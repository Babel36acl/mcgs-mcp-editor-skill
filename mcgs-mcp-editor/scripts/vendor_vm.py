"""Execute pinned vendor x86 VM code in Unicorn with an in-memory data host.

No DLL is loaded into Windows. All imports are denied except memory copy.
This checks bytecode semantics, not McgsPro GUI compilation or event dispatch.
"""
import hashlib
import struct
from pathlib import Path

import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_ESP, UC_X86_REG_EIP

RUNTIME_SHA256 = 'a84156810e71e10fdf09db4217e17e494ffb3ba3ec81bf9f35a0377febb5a6a2'


class VendorVM:
    def __init__(self, values, runtime):
        raw = Path(runtime).read_bytes()
        expected = RUNTIME_SHA256
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('Vendor DLL differs from the inspected binary')
        self.sha256 = expected
        pe = pefile.PE(data=raw)
        self.uc = Uc(UC_ARCH_X86, UC_MODE_32)
        self.uc.mem_map(pe.OPTIONAL_HEADER.ImageBase, (pe.OPTIONAL_HEADER.SizeOfImage + 4095) & ~4095)
        self.uc.mem_write(pe.OPTIONAL_HEADER.ImageBase, pe.get_memory_mapped_image())
        self.uc.mem_map(0x10000000, 0x100000)
        self.uc.mem_map(0x20000000, 0x10000)
        self.uc.mem_map(0x30000000, 0x100000)
        self.imports = {}
        for entry in pe.DIRECTORY_ENTRY_IMPORT:
            for item in entry.imports:
                address = 0x20000000 + len(self.imports) * 16
                self.imports[address] = entry.dll.decode() + '!' + (item.name.decode() if item.name else str(item.ordinal))
                self.w32(item.address, address)
        self.values = dict(values)
        self.writes = []
        self.reads = []
        self.opcodes = []
        self.instructions = 0
        self.external_calls = set()
        self.uc.hook_add(UC_HOOK_CODE, self.hook)

    def w32(self, address, value):
        self.uc.mem_write(address, struct.pack('<I', value & 0xffffffff))

    def r32(self, address):
        return struct.unpack('<I', self.uc.mem_read(address, 4))[0]

    def ret(self, result, pop=0):
        sp = self.uc.reg_read(UC_X86_REG_ESP)
        self.uc.reg_write(UC_X86_REG_EAX, result)
        self.uc.reg_write(UC_X86_REG_EIP, self.r32(sp))
        self.uc.reg_write(UC_X86_REG_ESP, sp + 4 + pop)

    def hook(self, uc, address, size, _):
        self.instructions += 1
        if address == 0x2000fff0:
            uc.emu_stop()
            return
        if address == 0x6ab4886f:
            self.opcodes.append(uc.reg_read(UC_X86_REG_EAX) & 0xff)
        sp = uc.reg_read(UC_X86_REG_ESP)
        if address in self.imports:
            name = self.imports[address]
            self.external_calls.add(name)
            if name != 'utils.dll!_ZN2FF5utils6String10MemoryCopyEPvPKvj':
                raise RuntimeError('Denied external call: ' + name)
            dest, source, count = [self.r32(sp + n) for n in (4, 8, 12)]
            if count > 65536:
                raise RuntimeError('Unexpected memory-copy size')
            uc.mem_write(dest, bytes(uc.mem_read(source, count)))
            self.ret(dest)
        elif address == 0x20008000:
            object_id = self.r32(sp + 4)
            if object_id not in self.values:
                raise RuntimeError(f'Unknown mock object: {object_id}')
            value = struct.unpack('<d', uc.mem_read(sp + 8, 8))[0]
            self.values[object_id] = value
            self.writes.append({'object_id': object_id, 'value': value})
            self.ret(1, 12)
        elif address == 0x20008010:
            object_id, result = self.r32(sp + 4), self.r32(sp + 8)
            if object_id not in self.values:
                raise RuntimeError(f'Unknown mock object: {object_id}')
            uc.mem_write(result, struct.pack('<d', self.values[object_id]))
            self.reads.append(object_id)
            self.ret(1, 8)

    def call(self, address, this, args):
        sp = 0x300ff000
        self.uc.mem_write(sp, struct.pack('<' + 'I' * (len(args) + 1), 0x2000fff0, *args))
        self.uc.reg_write(UC_X86_REG_ESP, sp)
        self.uc.reg_write(UC_X86_REG_ECX, this)
        self.uc.emu_start(address, 0x2000fff0, timeout=5_000_000, count=100000)
        if self.uc.reg_read(UC_X86_REG_EIP) != 0x2000fff0:
            raise RuntimeError('VM instruction/time limit reached')
        return self.uc.reg_read(UC_X86_REG_EAX)

    def run(self, code):
        if not 13 <= len(code) <= 4096:
            raise ValueError('Expected 13 to 4096 bytes of bytecode')
        code_ptr, reader, vector = 0x10001000, 0x10002000, 0x10003000
        slots, context, host, vtable = 0x10004000, 0x10006000, 0x10006100, 0x10006200
        call_stack, runtime = 0x10007000, 0x10008000
        self.uc.mem_write(code_ptr, code)
        self.uc.mem_write(vector, struct.pack('<3I', slots, slots, slots + 4096))
        self.w32(context + 8, host)
        self.w32(host, vtable)
        self.w32(vtable + 0x14, 0x20008000)
        self.w32(vtable + 0x24, 0x20008010)
        accepted = self.call(0x6ab46c90, reader, [code_ptr, len(code), vector, 0]) & 0xff
        if accepted != 1:
            raise RuntimeError('Vendor VM rejected the program header')
        self.call(0x6ab48850, runtime, [reader, context, vector, call_stack])
        if self.r32(vector + 4) != self.r32(vector):
            raise RuntimeError('Unexpected remaining stack values')
        return dict(values=self.values, writes=self.writes, reads=self.reads,
                    opcodes=[f'{x:02x}' for x in self.opcodes], instructions=self.instructions,
                    imports=sorted(self.external_calls), script_dll_sha256=self.sha256)
