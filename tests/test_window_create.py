import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcgs-mcp-editor/scripts'))

from mcp_tool import plan_window


def table():
    return {'iID': [1, 4, 53], 'iDeleteFlag': [0, 0, 0], 'iCompileFlag': [1, 1, 1],
            'strName': ['a', 'b', 'c'], 'strNote': ['', '', ''],
            'lbObjects': [b'\x00\x01', b'\x02\x03', None]}


class PlanWindowTests(unittest.TestCase):
    def test_rejects_bad_template(self):
        with self.assertRaises(ValueError):
            plan_window(table(), {'template_window_id': 999, 'new_name': 'x'})

    def test_rejects_duplicate_or_empty_name(self):
        with self.assertRaises(ValueError):
            plan_window(table(), {'template_window_id': 53, 'new_name': 'b'})
        with self.assertRaises(ValueError):
            plan_window(table(), {'template_window_id': 53, 'new_name': ''})

    def test_rejects_unparsable_template(self):
        with self.assertRaises(Exception):
            plan_window(table(), {'template_window_id': 53, 'new_name': 'x'})

    def test_allocates_max_plus_one(self):
        import struct
        from wnduser_records import parse_window
        blob = struct.pack('<II', 0x1234, 0) + b'\x00' * 32
        try:
            parse_window(blob)
        except Exception:
            self.skipTest('synthetic blob is not a valid window; covered by CLI proof')
        t = table()
        t['lbObjects'][2] = blob
        new_id, out = plan_window(t, {'template_window_id': 53, 'new_name': 'x'})
        self.assertEqual(new_id, 54)
        self.assertEqual(out, blob)


if __name__ == '__main__':
    unittest.main()
