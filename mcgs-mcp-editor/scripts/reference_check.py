"""Read-only window identity checks and explicitly located navigation fields.

No global string scan is used to infer a link. Unknown trailers and unprofiled
references remain uncovered. Results are consistency evidence, not host verdicts.
"""
from collections import Counter
import hashlib
import struct
from mfc_archive import ArchiveError, read_string


def _sha(blob):
    return hashlib.sha256(blob).hexdigest()


def trailer_identity(trailer):
    # Two observed tokenized prefixes: tag 3 + u32 ID, tag 8 + u32 byte
    # length + UTF-16 name. Select by tags, never by whether an ID matches.
    if len(trailer) < 8 or trailer[4:8] != b'\x02\x00\x00\x00':
        return None
    candidates = []
    for at in (12, 14):
        if len(trailer) < at+10:
            continue
        if trailer[at-2:at] != b'\x03\x00' or trailer[at+4:at+6] != b'\x08\x00':
            continue
        size = struct.unpack_from('<I', trailer, at+6)[0]
        end = at+10+size
        if size % 2 or end > len(trailer):
            continue
        try:
            name = trailer[at+10:end].decode('utf-16le')
        except UnicodeDecodeError:
            continue
        if not name or not all(c.isprintable() for c in name):
            continue
        candidates.append(dict(id=struct.unpack_from('<I', trailer, at)[0],
                               name=name, id_offset=at, name_offset=at+10))
    return candidates[0] if len(candidates) == 1 else None


def check_references(windows, parsed_windows, source_sha256, profile=None):
    """parsed_windows maps row indexes to strictly framed parse_window results."""
    findings = []
    names = windows.get('strName')
    ids = windows['iID']
    id_counts = Counter(ids)
    name_counts = Counter(names or [])
    for ident, count in id_counts.items():
        if count > 1:
            findings.append(dict(check='window_id_unique', status='mismatch', id=ident, count=count))
    for name, count in name_counts.items():
        if count > 1:
            findings.append(dict(check='window_name_unique', status='mismatch', name=name, count=count))
    for row, ident in enumerate(ids):
        item = dict(check='window_identity', row=row, window_id=ident)
        parsed = parsed_windows.get(row)
        if parsed is None:
            item.update(status='not_covered', reason='Window record framing was rejected')
        elif names is None or row >= len(names):
            item.update(status='not_covered', reason='Window row name is unavailable')
        else:
            identity = trailer_identity(parsed['trailer'])
            if identity is None:
                item.update(status='not_covered', reason='Unknown or ambiguous trailer identity layout')
            else:
                item.update(observed=identity, row_name=names[row],
                            status='consistent' if identity['id']==ident and identity['name']==names[row] else 'mismatch')
        findings.append(item)
    if profile is not None:
        if not isinstance(profile, dict) or profile.get('source_sha256') != source_sha256:
            raise ArchiveError('Reference profile source hash does not match this MCP')
        links = profile.get('links')
        if not isinstance(links, list) or not links:
            raise ArchiveError('Reference profile must contain a nonempty links list')
        for number, link in enumerate(links):
            if not isinstance(link, dict) or link.get('type') != 'window_navigation':
                raise ArchiveError('Only explicitly profiled window_navigation is supported')
            source_id = link.get('window_id')
            if type(source_id) is not int or id_counts[source_id] != 1:
                raise ArchiveError('Profile source window is missing or ambiguous')
            row = ids.index(source_id)
            parsed = parsed_windows.get(row)
            if parsed is None:
                raise ArchiveError('Profile source window did not pass record framing')
            index = link.get('record_index')
            if type(index) is not int or not 0 <= index < len(parsed['records']):
                raise ArchiveError('Invalid reference record index')
            record = parsed['records'][index]
            try:
                kind = int(str(link['kind']), 0)
            except (KeyError, TypeError, ValueError) as exc:
                raise ArchiveError('Invalid reference kind') from exc
            payload = record['payload']
            if kind != record['kind'] or link.get('sha256') != _sha(payload):
                raise ArchiveError('Reference record kind/hash differs from the profile')
            name_at, id_at = link.get('name_offset'), link.get('id_offset')
            if type(name_at) is not int or not 0 <= name_at < len(payload):
                raise ArchiveError('Invalid reference name offset')
            if type(id_at) is not int or not 0 <= id_at <= len(payload)-4:
                raise ArchiveError('Invalid reference ID offset')
            name_field = read_string(payload, name_at)
            if id_at < name_field['end'] and id_at+4 > name_at:
                raise ArchiveError('Reference name and ID fields overlap')
            target_name = name_field['text']
            target_id = struct.unpack_from('<I', payload, id_at)[0]
            reason = None
            if names is None or len(names) != len(ids):
                status, reason = 'not_covered', 'Window name table is unavailable'
            elif id_counts[target_id] != 1:
                status, reason = 'mismatch', 'Target ID is missing or ambiguous'
            elif name_counts[target_name] != 1:
                status, reason = 'mismatch', 'Target name is missing or ambiguous'
            elif names[ids.index(target_id)] != target_name:
                status, reason = 'mismatch', 'Target name and ID select different windows'
            else:
                status = 'consistent'
            findings.append(dict(check='window_navigation', profile_link=number, status=status,
                                 source_window_id=source_id, record_index=index,
                                 name_offset=name_at, id_offset=id_at,
                                 target_name=target_name, target_id=target_id, reason=reason))
    counts = Counter(item['status'] for item in findings)
    return dict(scope='Window row/trailer identity and explicitly profiled navigation only',
                summary={key:counts[key] for key in ('consistent', 'mismatch', 'not_covered')},
                findings=findings,
                not_covered=['unprofiled navigation', 'variable bindings', 'resource references',
                             'deleted-row semantics', 'host behavior'])
