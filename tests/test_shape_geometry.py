"""Fail-closed checks for the two specimen-limited horizontal moves."""
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/mcgs-mcp-editor/scripts'))

import shape_geometry
from control_patch import digest, patch_payload
from mfc_archive import ArchiveError
from shape_geometry import horizontal_coordinates, horizontal_fingerprint


def specimen():
    payload = bytearray(92)
    struct.pack_into('<4i', payload, 12, 10, 20, 60, 50)
    payload[40:44] = b'STYL'
    payload[80:84] = b'NAME'
    return bytes(payload)


def good_edit(**kw):
    edit = dict(type='horizontal_move', offset=12, expected=[10, 20, 60, 50], dx=5)
    edit.update(kw)
    return edit


class HorizontalMoveTests(unittest.TestCase):
    def setUp(self):
        # Tests must never depend on the vendor payloads; pin a synthetic
        # fingerprint in place of the two recorded specimens.
        self._saved = dict(shape_geometry.HORIZONTAL_SAMPLES)
        shape_geometry.HORIZONTAL_SAMPLES[0x5004] = horizontal_fingerprint(specimen())

    def tearDown(self):
        shape_geometry.HORIZONTAL_SAMPLES.clear()
        shape_geometry.HORIZONTAL_SAMPLES.update(self._saved)

    def test_moves_both_horizontal_edges_only(self):
        out = horizontal_coordinates(0x5004, specimen(), good_edit())
        self.assertEqual(struct.unpack('<4i', out), (15, 20, 65, 50))

    def test_fingerprint_normalizes_only_horizontal_origin(self):
        payload = specimen()
        moved = bytearray(payload)
        struct.pack_into('<4i', moved, 12, 12, 20, 62, 50)
        self.assertEqual(horizontal_fingerprint(bytes(moved)), horizontal_fingerprint(payload))
        for name, patch in (('left', lambda b: b.__setitem__(slice(12, 16), struct.pack('<i', 9))),
                            ('top', lambda b: b.__setitem__(slice(16, 20), struct.pack('<i', 21))),
                            ('right', lambda b: b.__setitem__(slice(20, 24), struct.pack('<i', 61))),
                            ('style', lambda b: b.__setitem__(40, 0x58)),
                            ('name', lambda b: b.__setitem__(80, 0x59))):
            changed = bytearray(payload)
            patch(changed)
            with self.subTest(field=name), self.assertRaises(ArchiveError):
                horizontal_coordinates(0x5004, bytes(changed), good_edit())

    def test_rejects_other_kinds_lengths_and_shapes(self):
        with self.assertRaises(ArchiveError):
            horizontal_coordinates(0x5006, specimen(), good_edit())
        with self.assertRaises(ArchiveError):
            horizontal_fingerprint(specimen()[:-1])
        with self.assertRaises(ArchiveError):
            horizontal_fingerprint(b'\x00' * 92)

    def test_rejects_bad_displacement_and_fields(self):
        payload = specimen()
        for bad in ({'dx': 1.5}, {'dx': 2 ** 31}, {'dx': -2 ** 31 - 1}):
            with self.subTest(**bad), self.assertRaises(ArchiveError):
                horizontal_coordinates(0x5004, payload, good_edit(**bad))
        for bad in ({'offset': 16}, {'expected': [10, 20, 60]},
                    {'expected': [0, 20, 60, 50]}, {'value': [0, 0, 1, 1]}):
            with self.subTest(**bad), self.assertRaises(ArchiveError):
                horizontal_coordinates(0x5004, payload, good_edit(**bad))

    def test_patch_payload_accepts_only_single_horizontal_edit(self):
        payload = specimen()
        profile = dict(sha256=digest(payload), kind='0x5004', edits=[good_edit()])
        out = patch_payload(payload, profile)
        self.assertEqual(struct.unpack_from('<4i', out, 12), (15, 20, 65, 50))
        self.assertEqual(out[40:44], b'STYL')
        self.assertEqual(out[80:84], b'NAME')
        self.assertEqual(len(out), len(payload))
        combined = dict(profile, edits=[good_edit(),
                                        dict(type='string', offset=80, expected='NAME', value='NAME')])
        with self.assertRaises(ArchiveError):
            patch_payload(payload, combined)
        with self.assertRaises(ArchiveError):
            patch_payload(payload, dict(profile, nested_counts=[dict(offset=0, expected=0)]))


if __name__ == '__main__':
    unittest.main()