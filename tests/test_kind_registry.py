import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcgs-mcp-editor/scripts'))

from kind_registry import KIND_CLASSES, RECT_WIDGETS, NEVER_EDITABLE, check_patchable
from shape_geometry import HORIZONTAL_SAMPLES


def edit(etype, **kw):
    base = {'type': etype, 'offset': 66, 'expected': 'AB', 'value': 'CD'}
    base.update(kw)
    return base


def horizontal(**kw):
    base = {'type': 'horizontal_move', 'offset': 12, 'expected': [0, 0, 10, 10], 'dx': 4}
    base.update(kw)
    return base


class KindRegistryTests(unittest.TestCase):
    def test_all_22_kinds_pinned(self):
        self.assertEqual(len(KIND_CLASSES), 22)
        for kind, cls in [(0x5002, 'CDrawLine'), (0x5008, 'CDrawLabel'),
                          (0x5025, 'CDrawEdit'), (0x5026, 'CDrawFlow'),
                          (0x5027, 'CDrawButton'), (0x5028, 'CDrawMulBtn'),
                          (0x502A, 'CDrawMulDis'), (0x5031, 'CDrawSliderFill'),
                          (0x503D, 'CDrawDll'), (0x503C, 'CDrawComboBox')]:
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

    def test_new_shape_kinds_geometry_classified(self):
        # 503c has an int32 rectangle sample; the other kinds still lack evidence.
        check_patchable(0x503C, [edit('rectangle', expected=[0, 0, 1, 1],
                                          value=[0, 0, 2, 2])])
        for kind in (0x5006, 0x5009, 0x5023, 0x5029, 0x502D, 0x502E,
                     0x5032, 0x5033, 0x503A):
            with self.assertRaises(ValueError):
                check_patchable(kind, [edit('rectangle', expected=[0, 0, 1, 1],
                                            value=[0, 0, 2, 2])])

    def test_rectangle_gate_matches_registry_set(self):
        self.assertEqual(RECT_WIDGETS, {0x5008, 0x5025, 0x5027, 0x5028, 0x503C, 0x503D})
        for kind in sorted(RECT_WIDGETS):
            check_patchable(kind, [edit('rectangle', expected=[0, 0, 1, 1],
                                        value=[0, 0, 2, 2])])

    def test_flow_kind_rejects_every_edit(self):
        # 0x5026 CDrawFlow has a constructor identity but no verified writable layout.
        self.assertIn(0x5026, NEVER_EDITABLE)
        for action in (edit('string'), edit('string', expected='AB', value='ABCD'),
                       edit('rectangle', expected=[0, 0, 1, 1], value=[0, 0, 2, 2]),
                       horizontal()):
            with self.subTest(action=action['type']), self.assertRaises(ValueError):
                check_patchable(0x5026, [action])

    def test_horizontal_move_only_for_two_specimens(self):
        self.assertEqual(set(HORIZONTAL_SAMPLES), {0x5004, 0x5006})
        for kind in (0x5004, 0x5006):
            check_patchable(kind, [horizontal()])
        for kind in (0x5002, 0x5005, 0x5009, 0x5023, 0x5029, 0x502A, 0x502D,
                     0x502E, 0x5031, 0x5032, 0x5033, 0x5039, 0x503A, 0x503C):
            with self.subTest(kind=hex(kind)), self.assertRaises(ValueError):
                check_patchable(kind, [horizontal()])

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            check_patchable(0x9999, [edit('string')])
        with self.assertRaises(ValueError):
            check_patchable(0x5008, [{'type': 'mystery'}])


if __name__ == '__main__':
    unittest.main()
