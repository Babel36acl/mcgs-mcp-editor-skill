"""Bounded string reader recovered from MfcToQt.dll RVA 0x4b40.

This reads fields at a supplied offset; marker scanning remains a discovery
operation and does not establish an enclosing object boundary.
"""
import re


class ArchiveError(ValueError):
    pass


def read_string(data, offset=0, ansi_encoding='gbk'):
    start = offset

    def take(size):
        nonlocal offset
        if size < 0 or offset < 0 or offset + size > len(data):
            raise ArchiveError(f'Truncated field at {offset}, requested {size}')
        result = data[offset:offset+size]
        offset += size
        return result

    def number(size):
        return int.from_bytes(take(size), 'little')

    width = 1
    length = number(1)
    kind = 'u8'
    if length == 255:
        length = number(2)
        kind = 'u16'
        if length == 65534:
            width = 2
            length = number(1)
            kind = 'u8'
            if length == 255:
                length = number(2)
                kind = 'u16'
        if length == 65535:
            length = number(4)
            kind = 'u32'
    text_offset = offset
    raw = take(length * width)
    try:
        text = raw.decode('utf-16le' if width == 2 else ansi_encoding)
    except UnicodeDecodeError as exc:
        raise ArchiveError(f'Invalid text at {text_offset}') from exc
    return dict(offset=start, text_offset=text_offset, end=offset, code_units=length,
                width=width, length_kind=kind, text=text)


def scan_unicode_strings(data):
    for match in re.finditer(b'\xff\xfe\xff', data):
        try:
            result = read_string(data, match.start())
        except ArchiveError:
            continue
        if all(c.isprintable() or c in '\r\n\t' for c in result['text']):
            yield result
