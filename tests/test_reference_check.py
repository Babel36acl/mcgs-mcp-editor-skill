"""Synthetic coverage of the read-only identity/reference checker."""
import hashlib
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/mcgs-mcp-editor/scripts'))

from mfc_archive import ArchiveError
from reference_check import check_references, trailer_identity


def trailer(window_id, name):
    encoded = name.encode('utf-16le')
    return (b'\x00' * 4 + b'\x02\x00\x00\x00' + b'\x00' * 2
            + b'\x03\x00' + struct.pack('<I', window_id)
            + b'\x08\x00' + struct.pack('<I', len(encoded)) + encoded)


def fixture(rows, trailer_name=''):
    windows = {'iID': [ident for ident, _ in rows],
               'strName': [name for _, name in rows]}
    parsed = {}
    for row, (ident, name) in enumerate(rows):
        parsed[row] = dict(trailer=trailer(ident, trailer_name or name), records=[])
    return windows, parsed


class ReferenceTests(unittest.TestCase):
    def test_trailer_identity_picks_tagged_layout(self):
        found = trailer_identity(trailer(7, 'home'))
        self.assertEqual(found['id'], 7)
        self.assertEqual(found['name'], 'home')
        self.assertIsNone(trailer_identity(b'\x00' * 24))
        self.assertIsNone(trailer_identity(trailer(7, 'home')[:-1]))

    def test_consistent_rows_and_unique_names(self):
        windows, parsed = fixture([(1, 'a'), (2, 'b')])
        report = check_references(windows, parsed, 'f' * 64)
        self.assertEqual(report['summary'], {'consistent': 2, 'mismatch': 0, 'not_covered': 0})
        self.assertIn('variable bindings', report['not_covered'])

    def test_duplicate_and_identity_mismatch_are_reported(self):
        windows, parsed = fixture([(1, 'a'), (2, 'a')])
        report = check_references(windows, parsed, 'f' * 64)
        checks = {item['check'] for item in report['findings'] if item['status'] == 'mismatch'}
        self.assertIn('window_name_unique', checks)
        windows, parsed = fixture([(1, 'a')], trailer_name='other')
        report = check_references(windows, parsed, 'f' * 64)
        self.assertEqual(report['summary']['mismatch'], 1)

    def test_rejected_window_and_unknown_trailer_stay_uncovered(self):
        windows = {'iID': [1, 2], 'strName': ['a', 'b']}
        report = check_references(windows, {0: dict(trailer=b'\x00' * 24, records=[])}, 'f' * 64)
        statuses = [item['status'] for item in report['findings']]
        self.assertEqual(statuses.count('not_covered'), 2)
        self.assertEqual(report['summary']['consistent'], 0)

    def test_navigation_link_requires_exact_bytes(self):
        windows, parsed = fixture([(1, 'a'), (5, 'home')])
        payload = (struct.pack('<4i', 0, 0, 10, 10) + b'\xff\xfe\xff\x04'
                   + 'home'.encode('utf-16le') + struct.pack('<I', 5))
        parsed[0]['records'] = [dict(index=0, kind=0x5027, payload=payload)]
        link = dict(type='window_navigation', window_id=1, record_index=0, kind='0x5027',
                    sha256=hashlib.sha256(payload).hexdigest(),
                    name_offset=16, id_offset=len(payload) - 4)
        profile = dict(source_sha256='f' * 64, links=[link])
        report = check_references(windows, parsed, 'f' * 64, profile)
        navigation = [item for item in report['findings'] if item['check'] == 'window_navigation']
        self.assertEqual(navigation[0]['status'], 'consistent')
        with self.assertRaises(ArchiveError):
            check_references(windows, parsed, 'f' * 64, dict(profile, source_sha256='0' * 64))
        with self.assertRaises(ArchiveError):
            check_references(windows, parsed, 'f' * 64, dict(profile, links=[dict(link, sha256='0' * 64)]))


if __name__ == '__main__':
    unittest.main()