"""Bounded BASIC subset; execute original Select/Block/Compare/Add code generation."""
import re
import struct
from vendor_codegen import VendorCodegen

IDENT = r'[^\W\d]\w*'
ATOM = rf'(?:-?[0-9]+|{IDENT})'
VT = {'assign':0x1121360, 'data':0x112125c, 'integer':0x11210f0,
      'block':0x1120c78, 'if':0x1121430, '+':0x1120d14,
      '=':0x1120f1c, '<>':0x1120fb8, '<':0x1120eb4,
      '>':0x1120ee8, '<=':0x1120f50, '>=':0x1120f84}


def parse_source(source, symbols):
    if not isinstance(source, str) or len(source) > 16000:
        raise ValueError('Source exceeds bounded subset')
    if not isinstance(symbols, dict) or not symbols:
        raise ValueError('An explicit numeric symbol mapping is required')
    for name, number in symbols.items():
        if not re.fullmatch(IDENT, name) or type(number) is not int or not 0 < number < 2**31:
            raise ValueError('Invalid numeric symbol mapping')
    lines = [line.strip() for line in source.splitlines() if line.strip()]
    if not 0 < len(lines) <= 128:
        raise ValueError('Expected 1 to 128 nonempty lines')
    pos = 0

    def atom(text):
        if re.fullmatch('-?[0-9]+', text):
            number = int(text)
            if not -(2**31) <= number < 2**31:
                raise ValueError('Integer exceeds signed 32-bit range')
            return ('integer', number)
        if text not in symbols:
            raise ValueError('Unknown numeric variable: ' + text)
        return ('data', symbols[text])

    def expression(text):
        if not re.fullmatch(rf'{ATOM}(?:\s*\+\s*{ATOM})*', text):
            raise ValueError('Only numeric atoms and addition are supported')
        parts = re.split(r'\s*\+\s*', text)
        tree = atom(parts[0])
        for part in parts[1:]:
            tree = ('+', tree, atom(part))
        return tree

    def block(depth=0):
        nonlocal pos
        if depth > 8:
            raise ValueError('Conditional nesting exceeds 8')
        nodes = []
        while pos < len(lines):
            line = lines[pos]
            if line.lower() in ('else', 'endif'):
                break
            condition = re.fullmatch(rf'If\s+({ATOM})\s*(<=|>=|<>|=|<|>)\s*({ATOM})\s+Then', line, re.I)
            if condition:
                pos += 1
                yes = block(depth+1)
                no = None
                if pos < len(lines) and lines[pos].lower() == 'else':
                    pos += 1
                    no = block(depth+1)
                if pos >= len(lines) or lines[pos].lower() != 'endif':
                    raise ValueError('Missing EndIf')
                pos += 1
                nodes.append(('if', (condition[2], atom(condition[1]), atom(condition[3])), yes, no))
            else:
                assignment = re.fullmatch(rf'({IDENT})\s*=\s*(.+)', line)
                if not assignment or assignment[1] not in symbols:
                    raise ValueError('Unsupported statement: ' + line)
                nodes.append(('assign', atom(assignment[1]), expression(assignment[2])))
                pos += 1
        if not nodes:
            raise ValueError('Empty blocks are not supported')
        return ('block', nodes)

    tree = block()
    if pos != len(lines):
        raise ValueError('Unexpected Else or EndIf')
    return tree


class ConditionalCodegen(VendorCodegen):
    def compile(self, source, symbols):
        tree = parse_source(source, symbols)
        self.uc.mem_write(0x10010000, bytes(0x70000))
        self.next_node = 0x10030000

        def allocate(size=0x80):
            address = self.next_node
            self.next_node += (size + 15) & ~15
            if self.next_node > 0x10070000:
                raise ValueError('Syntax arena exhausted')
            return address

        def node(tree):
            tag = tree[0]
            address = allocate()
            self.w32(address, VT[tag])
            if tag == 'integer':
                self.w32(address+0x14, tree[1])
            elif tag == 'data':
                self.w32(address+0x2c, 3)
                self.w32(address+0x30, tree[1])
            elif tag == 'block':
                children = [node(child) for child in tree[1]]
                vector = allocate(len(children)*4)
                for i, child in enumerate(children):
                    self.w32(vector+i*4, child)
                self.uc.mem_write(address+0x14, struct.pack('<3I', vector, vector+len(children)*4, vector+len(children)*4))
            elif tag == 'if':
                self.w32(address+0x14, node(tree[1]))
                self.w32(address+0xc, node(tree[2]))
                self.w32(address+0x10, node(tree[3]) if tree[3] else 0)
            else:
                self.w32(address+0xc, node(tree[1]))
                self.w32(address+0x10, node(tree[2]))
            return address

        root = node(tree)
        buffer, vector, data = 0x10010300, 0x10010400, 0x10011000
        self.w32(buffer+0x14, vector)
        self.uc.mem_write(vector, struct.pack('<3I', data, data, data+4096))
        for _ in range(3):
            self.call(0xca9320, buffer, [0])
        self.call(0xcbb770, root, [buffer])
        self.call(0xca9190, buffer, [1])
        start, end = self.r32(vector), self.r32(vector+4)
        if start != data or not start <= end <= data+4096:
            raise RuntimeError('Unexpected bytecode extent')
        code = bytes(self.uc.mem_read(start, end-start))
        return code, dict(source=source, symbols=symbols, code_hex=code.hex(),
                         editor_sha256=self.editor_sha256, instructions=self.instructions,
                         imports=sorted(self.external_calls), frontend='bounded assignment/add/If-Else subset')
