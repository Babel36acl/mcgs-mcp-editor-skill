import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcgs-mcp-editor/scripts'))

from kind_registry import KIND_CLASSES, check_patchable


def edit(etype, **kw):
    base = {'type': etype, 'offset': 66, 'expected': 'AB', 'value': 'CD'}
    base.update(kw)
    return base


class KindRegistryTests(unittest.TestCase):
    def test_all_21_kinds_pinned(self):
        self.assertEqual(len(KIND_CLASSES), 21)
        for kind, cls in [(0x5002, 'CDrawLine'), (0x5008, 'CDrawLabel'),
                          (0x5025, 'CDrawEdit'), (0x5027, 'CDrawButton'),
                          (0x5028, 'CDrawMulBtn'), (0x502A, 'CDrawMulDis'),
                          (0x5031, 'CDrawSliderFill'), (0x503D, 'CDrawDll'),
                          (0x503C, 'CDrawComboBox')]:
            self.assertEqual(KIND_CLASSES[kind], cls)

    def test_proven_kinds_keep_full_power(self):
        check_patchable(0x5008, [edit('string', expected='A', value='ABC')])
        check_patchable(0x5025, [edit('input_binding', expected='P1', value='P2',
                                       id_offset=0, expected_id=1, value_id=2)])
        check_patchable(0x5025, [edit('input_range', expected=[1.0, 0.0], value=[2.0, 0.0])])
        check_patchable(0x5027, [edit('event', expected='s', expected_code_sha256='x' * 64,
                                       program_file='p')])
        check_patchable(0x5028, [edit('rectangle', expected=[0, 0, 1, 1], value=[0, 0, 2, 2])])

    def test_new_kinds_same_length_text_only(self):
        check_patchable(0x5028, [edit('string')])
        check_patchable(0x503C, [edit('string')])
        with self.assertRaises(ValueError):
            check_patchable(0x5028, [edit('string', expected='A', value='ABC')])
        with self.assertRaises(ValueError):
            check_patchable(0x5002, [edit('rectangle', expected=[0, 0, 1, 1],
                                          value=[0, 0, 2, 2])])
        with self.assertRaises(ValueError):
            check_patchable(0x5025, [edit('event', expected='s',
                                          expected_code_sha256='x' * 64,
                                          program_file='p')])
        with self.assertRaises(ValueError):
            check_patchable(0x5027, [edit('input_binding', expected='P1', value='P2',
                                          id_offset=0, expected_id=1, value_id=2)])

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            check_patchable(0x9999, [edit('string')])
        with self.assertRaises(ValueError):
            check_patchable(0x5008, [{'type': 'mystery'}])


if __name__ == '__main__':
    unittest.main()
