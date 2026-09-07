"""Length-framed top-level WndUser records, validated on 36 native windows.

Nested payloads and the preserved window trailer are not fully decoded.
"""
import struct
from mfc_archive import ArchiveError, read_string


def parse_window(blob):
    header = read_string(blob, 12)
    if header['text'] != 'MCGS-SET DOCUMENT;VERSION 01.00':
        raise ArchiveError('Unsupported WndUser document header')
    count_offset = header['end']
    if count_offset + 4 > len(blob):
        raise ArchiveError('Missing record count')
    count = struct.unpack_from('<I', blob, count_offset)[0]
    pos = count_offset + 4
    records = []
    if count > (len(blob)-pos)//6:
        raise ArchiveError('Impossible record count')
    for index in range(count):
        if pos+6 > len(blob):
            raise ArchiveError('Truncated record header')
        kind, length = struct.unpack_from('<IH',blob,pos)
        if not 0x5000 <= kind < 0x6000 or length == 65535:
            raise ArchiveError(f'Unsupported record header at {pos}')
        end = pos+6+length
        if end > len(blob):
            raise ArchiveError('Truncated record payload')
        records.append(dict(index=index,start=pos,end=end,kind=kind,payload=blob[pos+6:end]))
        pos=end
    if len(blob)-pos < 10:
        raise ArchiveError('Missing window trailer')
    trailer_length = struct.unpack_from('<I',blob,pos)[0]
    if trailer_length + 10 != len(blob)-pos:
        raise ArchiveError('Window trailer extent does not match sample format')
    return dict(count_offset=count_offset, records=records, trailer_offset=pos, trailer=blob[pos:])


def pack_record(kind, payload):
    if len(payload) >= 65535:
        raise ArchiveError('Extended record length is not implemented')
    return struct.pack('<IH',kind,len(payload))+payload


def append_records(blob, additions):
    parsed=parse_window(blob)
    result=bytearray(blob[:parsed['trailer_offset']])
    struct.pack_into('<I',result,parsed['count_offset'],len(parsed['records'])+len(additions))
    for kind,payload in additions:
        result.extend(pack_record(kind,payload))
    result.extend(parsed['trailer'])
    check=parse_window(result)
    if check['trailer'] != parsed['trailer']:
        raise ArchiveError('Trailer changed')
    return bytes(result)
