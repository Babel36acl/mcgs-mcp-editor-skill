"""Evidence-profile edits with exact preimages and explicit nested count repair."""
import hashlib
import math
import struct
from mfc_archive import read_string, ArchiveError


def digest(data):
    return hashlib.sha256(data).hexdigest()


def unicode_string(text):
    encoded = text.encode('utf-16le')
    units = len(encoded)//2
    if units >= 65535:
        raise ArchiveError('String exceeds supported length')
    count = bytes([units]) if units < 255 else b'\xff'+struct.pack('<H',units)
    return b'\xff\xfe\xff'+count+encoded


def patch_payload(payload, profile):
    if digest(payload) != profile['sha256'].lower():
        raise ArchiveError('Control payload differs from the inspected profile')
    replacements = []
    for edit in profile['edits']:
        offset = edit['offset']
        if type(offset) is not int or not 0 <= offset < len(payload):
            raise ArchiveError('Invalid edit offset')
        kind = edit['type']
        if kind in ('string','input_binding'):
            old = read_string(payload, offset)
            if old['text'] != edit['expected']:
                raise ArchiveError('Unexpected string preimage')
            end, new = old['end'], unicode_string(edit['value'])
            if kind == 'input_binding':
                at = edit['id_offset']
                old_id, new_id = edit['expected_id'], edit['value_id']
                if type(at) is not int or not 0 <= at <= len(payload)-4:
                    raise ArchiveError('Invalid binding ID offset')
                if any(type(n) is not int or not 0 < n < 2**31 for n in (old_id,new_id)):
                    raise ArchiveError('Binding IDs must be positive int32 values')
                if struct.unpack_from('<I',payload,at)[0] != old_id:
                    raise ArchiveError('Unexpected old binding ID')
                replacements.append((at,at+4,struct.pack('<I',new_id)))
        elif kind in ('rectangle', 'input_range'):
            fmt = '<4i' if kind == 'rectangle' else '<2f'
            end = offset+struct.calcsize(fmt)
            new = struct.pack(fmt, *edit['value'])
            if payload[offset:end] != struct.pack(fmt, *edit['expected']):
                raise ArchiveError('Unexpected numeric preimage')
            values = struct.unpack(fmt, new)
            if kind == 'rectangle' and not (values[0]<values[2] and values[1]<values[3]):
                raise ArchiveError('Rectangle must have positive width and height')
            if kind == 'input_range' and not (all(math.isfinite(x) for x in values) and values[1]<=values[0]):
                raise ArchiveError('Input range order is [maximum, minimum]')
        elif kind == 'event':
            old = read_string(payload, offset)
            if old['text'] != edit['expected']:
                raise ArchiveError('Unexpected event source')
            if old['end']+2 > len(payload):
                raise ArchiveError('Missing compiled array')
            size = struct.unpack_from('<H',payload,old['end'])[0]
            end = old['end']+2+size
            if size == 65535 or end>len(payload):
                raise ArchiveError('Unsupported compiled array extent')
            if digest(payload[old['end']+2:end]) != edit['expected_code_sha256'].lower():
                raise ArchiveError('Unexpected old compiled array')
            # CLI resolves this from script_tool output, keeping source and code together.
            program = edit['program']
            code = bytes.fromhex(program['code_hex'])
            if not 13 <= len(code) <= 4096 or code[:12] != bytes(12) or code[-1] != 1:
                raise ArchiveError('Unsupported generated program format')
            new = unicode_string(program['source'])+struct.pack('<H',len(code))+code
        else:
            raise ArchiveError('Unsupported edit type: '+kind)
        replacements.append((offset,end,new))
    replacements.sort()
    for i,(start,end,_) in enumerate(replacements):
        if end>len(payload) or (i and start<replacements[i-1][1]):
            raise ArchiveError('Overlapping or out-of-bounds edits')
    seen = set()
    counts = []
    for field in profile.get('nested_counts',[]):
        at, count = field['offset'], field['expected']
        if type(at) is not int or at in seen or not 0 <= at <= len(payload)-2:
            raise ArchiveError('Invalid nested count position')
        seen.add(at)
        if type(count) is not int or not 0 <= count < 65535 or struct.unpack_from('<H',payload,at)[0] != count:
            raise ArchiveError('Nested u16 count differs from the inspected profile')
        end = at+2+count
        if end>len(payload):
            raise ArchiveError('Nested array extends beyond control')
        delta = 0
        for start,stop,new in replacements:
            if start<at+2 and stop>at:
                raise ArchiveError('Edit overlaps nested length field')
            if start<end and stop>at+2:
                if start<at+2 or stop>end:
                    raise ArchiveError('Edit crosses a nested boundary')
                delta += len(new)-(stop-start)
        if not 0 <= count+delta < 65535:
            raise ArchiveError('Nested array exceeds supported size')
        counts.append((at,at+2,struct.pack('<H',count+delta)))
    result = payload
    for start,end,new in sorted(replacements+counts, reverse=True):
        result = result[:start]+new+result[end:]
    return result
