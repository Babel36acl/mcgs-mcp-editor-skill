"""Framing and typed-control-flow tests using synthetic programs only."""
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'mcgs-mcp-editor/scripts'))
from bytecode_inspect import inspect_program

HEADER = bytes(12)


def integer(number):
    return b'\x11' + struct.pack('<i', number)


def store(number):
    return b'\x47\x3e' + struct.pack('<I', number)


class BytecodeTests(unittest.TestCase):
    def test_assignment_and_reference_evidence(self):
        report = inspect_program(HEADER + integer(12345) + store(164) + b'\x01')
        self.assertEqual(report['write_object_ids'], [164])
        self.assertEqual(report['read_object_ids'], [])
        self.assertEqual(report['max_stack_slots'], 1)
        self.assertEqual([r['name'] for r in report['instructions']],
                         ['push_i32', 'i32_to_f64', 'write_number', 'return'])

    def test_jump_is_relative_to_end_of_operand(self):
        # False branch skips an entire assignment. Both paths end with no stack.
        assignment = integer(5) + store(2)
        code = HEADER + integer(0) + b'\x03' + struct.pack('<i', len(assignment)) + assignment + b'\x01'
        report = inspect_program(code)
        branch = report['instructions'][1]
        self.assertEqual(branch['target'], len(code)-1)
        self.assertEqual(branch['stack_after'], [])
        self.assertEqual(report['unreachable_offsets'], [])

    def test_bad_framing_and_jump_targets_are_rejected(self):
        cases = [HEADER + b'\xff\x01', HEADER + b'\x11\x01',
                 HEADER + integer(1), struct.pack('<3I', 1, 0, 0) + b'\x01',
                 HEADER + b'\x02' + struct.pack('<i', -16) + b'\x01',
                 HEADER + b'\x02' + struct.pack('<i', 1) + integer(1) + b'\x01',
                 HEADER + b'\x26' + bytes(4) + b'\x01']
        for code in cases:
            with self.subTest(code=code.hex()), self.assertRaises(ValueError):
                inspect_program(code)

    def test_types_underflow_and_inconsistent_merges_are_rejected(self):
        # Conditional jump leaves a value only on its fall-through path.
        merge = HEADER + integer(1) + b'\x03' + struct.pack('<i', 5) + integer(2) + b'\x01'
        cases = [HEADER + b'\x47\x01', HEADER + integer(1) + b'\x3e\x02\0\0\0\x01',
                 HEADER + integer(1) + b'\x01', merge]
        for code in cases:
            with self.subTest(code=code.hex()), self.assertRaises(ValueError):
                inspect_program(code)

    def test_backward_jump_requires_consistent_stack_and_reachable_return(self):
        code = HEADER + b'\x02' + struct.pack('<i', -5) + b'\x01'
        with self.assertRaisesRegex(ValueError, 'No reachable return'):
            inspect_program(code)


if __name__ == '__main__':
    unittest.main()
