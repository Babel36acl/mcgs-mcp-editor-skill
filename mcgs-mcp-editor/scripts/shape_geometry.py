"""Horizontal-only moves for two host-tested shape specimens.

The fingerprint normalizes horizontal origin, retaining dimensions, vertical
position, style, name and every opaque byte. Matching kind/length is insufficient.
No vendor payload is distributed; tests build synthetic records independently.
"""
import hashlib
import struct
from mfc_archive import ArchiveError


HORIZONTAL_SAMPLES = {
    0x5004: 'c271e8df97abd438b459a4e3d327f8699f63b30148a86c7c9044a765b75a07ea',
    0x5006: 'e6b31e00887e2456fbc4b3627a2ab4dab5a516fa990195a170f104f2df8c97cc',
}


def horizontal_fingerprint(payload):
    if len(payload) != 92:
        raise ArchiveError('Horizontal move requires the verified 92-byte specimen')
    left, top, right, bottom = struct.unpack_from('<4i', payload, 12)
    if not (0 < right-left < 2**31 and 0 < bottom-top < 2**31):
        raise ArchiveError('Invalid shape extent')
    normalized = bytearray(payload)
    struct.pack_into('<4i', normalized, 12, 0, top, right-left, bottom)
    return hashlib.sha256(normalized).hexdigest()


def horizontal_coordinates(kind, payload, edit):
    if kind not in HORIZONTAL_SAMPLES:
        raise ArchiveError('Horizontal move is only verified for 0x5004/0x5006 specimens')
    if horizontal_fingerprint(payload) != HORIZONTAL_SAMPLES[kind]:
        raise ArchiveError('Shape differs from the verified horizontal-move specimen')
    if set(edit) != {'type', 'offset', 'expected', 'dx'} or edit['offset'] != 12:
        raise ArchiveError('Horizontal move requires offset 12, expected rectangle and dx only')
    expected = edit['expected']
    if not isinstance(expected, list) or len(expected) != 4 or any(type(n) is not int for n in expected):
        raise ArchiveError('Expected rectangle must be four int32 values')
    current = list(struct.unpack_from('<4i', payload, 12))
    if current != expected:
        raise ArchiveError('Unexpected horizontal-move preimage')
    dx = edit['dx']
    if type(dx) is not int or not -2**31 <= dx < 2**31:
        raise ArchiveError('Horizontal displacement must be int32')
    result = [current[0]+dx, current[1], current[2]+dx, current[3]]
    if any(not -2**31 <= n < 2**31 for n in result):
        raise ArchiveError('Horizontal move overflows int32 coordinates')
    return struct.pack('<4i', *result)
