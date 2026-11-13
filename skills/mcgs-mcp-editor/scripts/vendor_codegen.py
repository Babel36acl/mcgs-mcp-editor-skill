"""Map the pinned editor into Unicorn and allow only bounded memory-copy imports."""
import hashlib
from pathlib import Path
import pefile
from vendor_vm import VendorVM, UC_X86_REG_ESP




class VendorCodegen(VendorVM):
    def __init__(self, editor, runtime):
        super().__init__({}, runtime)
        # The compiler's MSVC exception frames link through fs:[0]. This page is
        # emulator memory only; no Windows process/thread state is accessed.
        self.uc.mem_map(0, 4096)
        raw = Path(editor).read_bytes()
        expected = 'a8e1ce78535ea3db0ca5fdb54306df7f9b56f298ca1025f2e20e337347fd6f54'
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('Editor differs from the inspected binary')
        pe = pefile.PE(data=raw)
        self.uc.mem_map(pe.OPTIONAL_HEADER.ImageBase, (pe.OPTIONAL_HEADER.SizeOfImage + 4095) & ~4095)
        self.uc.mem_write(pe.OPTIONAL_HEADER.ImageBase, pe.get_memory_mapped_image())
        self.uc.mem_map(0x21000000, 0x10000)
        index = 0
        for entry in pe.DIRECTORY_ENTRY_IMPORT:
            for item in entry.imports:
                address = 0x21000000 + index * 16
                index += 1
                self.imports[address] = entry.dll.decode() + '!' + (item.name.decode() if item.name else str(item.ordinal))
                self.w32(item.address, address)
        self.editor_sha256 = expected

    def hook(self, uc, address, size, data):
        name = self.imports.get(address, '')
        if name.lower() in ('msvcr110.dll!memcpy', 'msvcr110.dll!memmove', 'msvcr110.dll!memcpy_s'):
            sp = uc.reg_read(UC_X86_REG_ESP)
            if name.endswith('_s'):
                dest, capacity, source, count = [self.r32(sp + n) for n in (4, 8, 12, 16)]
                if count > capacity:
                    raise RuntimeError('Copy exceeds output capacity')
            else:
                dest, source, count = [self.r32(sp + n) for n in (4, 8, 12)]
            if count > 65536:
                raise RuntimeError('Unexpected copy length')
            uc.mem_write(dest, bytes(uc.mem_read(source, count)))
            self.external_calls.add(name)
            self.ret(0 if name.endswith('_s') else dest)
            return
        super().hook(uc, address, size, data)
