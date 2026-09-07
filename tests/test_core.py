import hashlib
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'mcgs-mcp-editor/scripts'))
from control_patch import digest, patch_payload, unicode_string
from mfc_archive import ArchiveError, read_string
from wnduser_records import parse_window, pack_record, append_records


def window(payloads):
    header = bytes(12)+unicode_string('MCGS-SET DOCUMENT;VERSION 01.00')
    return header+struct.pack('<I',len(payloads))+b''.join(pack_record(0x5008,p) for p in payloads)+bytes(10)


class CoreTests(unittest.TestCase):
    def test_unicode_code_units_and_extended_count(self):
        for text in ['', '温度', 'A😀B', '字'*255]:
            with self.subTest(length=len(text)):
                raw = unicode_string(text)
                actual = read_string(raw)
                self.assertEqual(actual['text'],text)
                self.assertEqual(actual['end'],len(raw))
                self.assertEqual(actual['code_units'],len(text.encode('utf-16le'))//2)
        with self.assertRaises(ArchiveError):
            read_string(unicode_string('范围')[:-1])

    def test_window_roundtrip_and_bad_count(self):
        original = window([b'one',b'two'])
        grown = append_records(original,[(0x5027,b'three')])
        parsed = parse_window(grown)
        self.assertEqual([r['payload'] for r in parsed['records']],[b'one',b'two',b'three'])
        self.assertEqual(parsed['trailer'],bytes(10))
        with self.assertRaises(ArchiveError):
            parse_window(grown[:-1])
        with self.assertRaises(ArchiveError):
            pack_record(0x5008,bytes(65535))

    def test_three_nested_lengths_shrink_and_grow(self):
        # Entirely synthetic arrays; tests the demonstrated missed-ancestor bug.
        old = unicode_string('abcdef')
        inner = struct.pack('<H',len(old))+old
        middle = struct.pack('<H',len(inner)+2)+inner+b'ZZ'
        payload = struct.pack('<H',len(middle))+middle+b'TAIL'
        for new_text in ['ab','abcdefghij']:
            profile = dict(sha256=digest(payload),edits=[dict(type='string',offset=6,expected='abcdef',value=new_text)],
                           nested_counts=[dict(offset=0,expected=len(middle)),dict(offset=2,expected=len(inner)+2),dict(offset=4,expected=len(old))])
            result = patch_payload(payload,profile)
            delta = len(unicode_string(new_text))-len(old)
            self.assertEqual(struct.unpack_from('<H',result,0)[0],len(middle)+delta)
            self.assertEqual(struct.unpack_from('<H',result,2)[0],len(inner)+2+delta)
            self.assertEqual(struct.unpack_from('<H',result,4)[0],len(old)+delta)
            self.assertEqual(read_string(result,6)['text'],new_text)
            self.assertTrue(result.endswith(b'ZZTAIL'))

    def test_binding_length_range_and_geometry(self):
        original = struct.pack('<4i',0,0,100,30)+unicode_string('Old')+struct.pack('<2f',100.,0.)+b'TAIL'
        profile = dict(sha256=digest(original),edits=[
            dict(type='rectangle',offset=0,expected=[0,0,100,30],value=[5,6,105,36]),
            dict(type='string',offset=16,expected='Old',value='Longer'),
            dict(type='input_range',offset=26,expected=[100,0],value=[200,10])])
        result = patch_payload(original,profile)
        binding = read_string(result,16)
        self.assertEqual(binding['text'],'Longer')
        self.assertEqual(struct.unpack_from('<2f',result,binding['end']),(200.,10.))
        self.assertTrue(result.endswith(b'TAIL'))

    def test_preimages_and_overlap_fail(self):
        payload = unicode_string('x')
        with self.assertRaises(ArchiveError):
            patch_payload(payload,dict(sha256='0'*64,edits=[]))
        with self.assertRaises(ArchiveError):
            patch_payload(payload,dict(sha256=digest(payload),edits=[dict(type='string',offset=0,expected='y',value='z')]))
        edit = dict(type='string',offset=0,expected='x',value='z')
        with self.assertRaises(ArchiveError):
            patch_payload(payload,dict(sha256=digest(payload),edits=[edit,edit]))

    def test_binding_name_and_runtime_id_change_together(self):
        payload = struct.pack('<2I',3,2)+unicode_string('Old')+b'TAIL'
        edit = dict(type='input_binding',offset=8,expected='Old',value='NewName',
                    id_offset=0,expected_id=3,value_id=7)
        result = patch_payload(payload,dict(sha256=digest(payload),edits=[edit]))
        self.assertEqual(struct.unpack_from('<2I',result,0),(7,2))
        self.assertEqual(read_string(result,8)['text'],'NewName')
        self.assertTrue(result.endswith(b'TAIL'))
        edit['expected_id'] = 9
        with self.assertRaises(ArchiveError):
            patch_payload(payload,dict(sha256=digest(payload),edits=[edit]))


if __name__ == '__main__':
    unittest.main()
