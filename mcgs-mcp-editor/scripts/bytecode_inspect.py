"""Inspect the numeric bytecode subset recovered from the pinned script.dll.

This is a strict reader, not a compiler or a replacement VM. Offsets include the
12-byte header. Jump displacements are relative to the end of their operand.
"""
import struct
from collections import deque

RUNTIME_SHA256 = 'a84156810e71e10fdf09db4217e17e494ffb3ba3ec81bf9f35a0377febb5a6a2'

# Original handler VAs, recovered from the table at 0x6ab5e84c in script.dll.
# Names describe observed effects; they are not vendor source identifiers.
OPS = {
    0x01: ('return', None, 0x6ab4b1f4),
    0x02: ('jump', 'relative_i32', 0x6ab4b1ac),
    0x03: ('jump_if_zero', 'relative_i32', 0x6ab4ad20),
    0x11: ('push_i32', 'i32', 0x6ab4af01),
    0x26: ('read_number', 'object_id', 0x6ab4a052),
    0x3e: ('write_number', 'object_id', 0x6ab497b7),
    0x47: ('i32_to_f64', None, 0x6ab4963f),
    0x4c: ('add_i32', None, 0x6ab49658),
    0x4d: ('add_f64', None, 0x6ab491e0),
    0x5d: ('lt_i32', None, 0x6ab4942a),
    0x5e: ('lt_f64', None, 0x6ab490f5),
    0x61: ('gt_i32', None, 0x6ab48f04),
    0x62: ('gt_f64', None, 0x6ab48ecc),
    0x65: ('eq_i32', None, 0x6ab48da4),
    0x66: ('eq_f64', None, 0x6ab48d66),
    0x69: ('le_i32', None, 0x6ab48d3c),
    0x6a: ('le_f64', None, 0x6ab48d06),
    0x6d: ('ge_i32', None, 0x6ab48bde),
    0x6e: ('ge_f64', None, 0x6ab48ba6),
    0x71: ('ne_i32', None, 0x6ab48b7c),
    0x72: ('ne_f64', None, 0x6ab48a43),
}


def inspect_program(code):
    """Return JSON-compatible framing, object references and typed CFG evidence.

    Only zero return/parameter/local headers used by ConditionalCodegen are
    supported. Every byte and jump target is checked. Stack types are checked
    on all reachable CFG paths without executing instructions or host calls.
    """
    if not isinstance(code, bytes) or not 13 <= len(code) <= 4096:
        raise ValueError('Expected 13 to 4096 bytes of bytecode')
    header = struct.unpack_from('<3I', code)
    if header != (0, 0, 0):
        raise ValueError('Only zero return/parameter/local headers are supported')
    instructions = []
    offset = 12
    while offset < len(code):
        start = offset
        opcode = code[offset]
        if opcode not in OPS:
            raise ValueError(f'Unsupported opcode 0x{opcode:02x} at byte {offset}')
        name, operand_kind, handler = OPS[opcode]
        offset += 1
        row = dict(offset=start, opcode=f'{opcode:02x}', name=name,
                   native_handler=f'0x{handler:08x}')
        if operand_kind:
            if offset + 4 > len(code):
                raise ValueError(f'Truncated {name} operand at byte {start}')
            operand = struct.unpack_from('<I' if operand_kind == 'object_id' else '<i', code, offset)[0]
            offset += 4
            row['operand_kind'] = operand_kind
            row['operand'] = operand
            if operand_kind == 'object_id' and not 0 < operand < 2**31:
                raise ValueError(f'Invalid numeric object ID at byte {start}')
            if operand_kind == 'relative_i32':
                row['target'] = offset + operand
        row['size'] = offset - start
        instructions.append(row)
    if instructions[-1]['name'] != 'return':
        raise ValueError('Expected a final return instruction')
    by_offset = {row['offset']: row for row in instructions}
    for row in instructions:
        if 'target' in row and row['target'] not in by_offset:
            raise ValueError(f'Jump at byte {row["offset"]} does not target an instruction boundary')

    states = {12: ()}
    pending = deque([12])
    max_stack = 0
    exits = []
    while pending:
        offset = pending.popleft()
        row = by_offset[offset]
        stack = list(states[offset])
        name = row['name']

        def pop(expected):
            if not stack:
                raise ValueError(f'Stack underflow at byte {offset}')
            if stack.pop() != expected:
                raise ValueError(f'Stack type mismatch at byte {offset}; expected {expected}')

        if name == 'push_i32':
            stack.append('i32')
        elif name == 'read_number':
            stack.append('f64')
        elif name == 'write_number':
            pop('f64')
        elif name == 'i32_to_f64':
            pop('i32')
            stack.append('f64')
        elif name == 'jump_if_zero':
            pop('i32')
        elif name == 'return':
            if stack:
                raise ValueError(f'Unexpected remaining stack values at return byte {offset}')
            exits.append(offset)
        elif name != 'jump':
            value_type = name.rsplit('_', 1)[1]
            pop(value_type)
            pop(value_type)
            stack.append(value_type if name.startswith('add_') else 'i32')
        max_stack = max(max_stack, len(stack))
        row['stack_before'] = list(states[offset])
        row['stack_after'] = list(stack)
        successors = []
        if name != 'return':
            if name in ('jump', 'jump_if_zero'):
                successors.append(row['target'])
            if name != 'jump':
                successors.append(offset + row['size'])
        row['successors'] = list(dict.fromkeys(successors))
        for target in row['successors']:
            if target not in by_offset:
                raise ValueError(f'Execution falls outside the program at byte {offset}')
            next_state = tuple(stack)
            if target in states:
                if states[target] != next_state:
                    raise ValueError(f'Inconsistent stack at control-flow merge byte {target}')
            else:
                states[target] = next_state
                pending.append(target)
    if not exits:
        raise ValueError('No reachable return in the supported control-flow graph')
    return dict(
        schema='mcgs-numeric-bytecode-inspection-v1',
        status='BOUNDED_BYTECODE_STRUCTURE_VALIDATED',
        expected_runtime_sha256=RUNTIME_SHA256,
        header=dict(return_type=0, parameter_count=0, local_count=0),
        byte_length=len(code), instruction_count=len(instructions),
        instructions=instructions, max_stack_slots=max_stack,
        read_object_ids=sorted({r['operand'] for r in instructions if r['name'] == 'read_number'}),
        write_object_ids=sorted({r['operand'] for r in instructions if r['name'] == 'write_number'}),
        unreachable_offsets=sorted(set(by_offset) - set(states)),
        limitations='Static references are not an execution trace; no termination, host project, or device acceptance is claimed')
