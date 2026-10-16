"""Inspect MCP windows or apply a reviewed control profile to a new Access copy."""
import argparse
import copy
import json
from pathlib import Path
from control_patch import digest, patch_payload
from kind_registry import check_patchable
from mfc_archive import scan_unicode_strings, ArchiveError
from wnduser_records import parse_window, pack_record


def snapshot(path):
    from access_parser import AccessParser
    db = AccessParser(str(path))
    return {name:db.parse_table(name) for name in db.catalog if not name.startswith('MSys')}


def inspect(path):
    tables = snapshot(path)
    windows = tables['WndUser']
    result = []
    for row, ident in enumerate(windows['iID']):
        blob = windows['lbObjects'][row]
        try:
            parsed = parse_window(blob)
            records = [dict(index=r['index'],kind=hex(r['kind']),size=len(r['payload']),
                            sha256=digest(r['payload']),strings=list(scan_unicode_strings(r['payload'])))
                       for r in parsed['records']]
            result.append(dict(id=ident,records=records,trailer_preserved=True))
        except (ArchiveError,TypeError) as exc:
            result.append(dict(id=ident,error=str(exc)))
    return dict(source=str(path.resolve()),sha256=digest(path.read_bytes()),windows=result,
                scope='Top-level record framing; string scans are discovery, not nested serializers')


def plan_window(table, spec):
    """Validate a new-window request against the WndUser table.

    Returns (new_id, blob). The blob is the template window's blob copied
    verbatim; control names inside are therefore duplicated and the host
    must verify the new window. Window names stay unique.
    """
    template = spec.get('template_window_id')
    name = spec.get('new_name', '')
    if template not in table['iID']:
        raise ValueError('Template window %r does not exist' % (template,))
    if not name or name in table['strName']:
        raise ValueError('New window name is empty or already present')
    new_id = max(table['iID']) + 1
    blob = table['lbObjects'][table['iID'].index(template)]
    parse_window(blob)
    return new_id, blob


def patch(source, output, profile, driver):
    if output.exists():
        raise ValueError('Output exists; refusing overwrite')
    # This Access driver treats DBQ={path} as a literal invalid filename.
    # Its proven unbraced form cannot represent semicolon-delimited paths.
    dbq = str(output.resolve())
    if any(char in dbq for char in ';\r\n'):
        raise ValueError('Access DBQ paths containing semicolons/newlines are unsupported')
    raw = source.read_bytes()
    if digest(raw) != profile['source_sha256'].lower():
        raise ValueError('Source MCP changed since profile inspection')
    before = snapshot(source)
    if source.read_bytes() != raw:
        raise ValueError('Source changed while reading')
    expected = copy.deepcopy(before)
    windows = expected['WndUser']
    controls = profile.get('controls', [])
    new_specs = profile.get('new_windows', [])
    if not controls and not new_specs:
        raise ValueError('Profile has neither controls nor new_windows')
    if controls:
        row = windows['iID'].index(profile['window_id'])
        blob = windows['lbObjects'][row]; parsed = parse_window(blob)
        originals = parsed['records']
    else:
        row = None; parsed = None; originals = []
    records = [(r['kind'],r['payload']) for r in originals]
    replaced = set()
    for action in controls:
        index = action['record_index']
        if type(index) is not int or not 0<=index<len(originals):
            raise ValueError('Record index out of bounds')
        record = originals[index]
        if record['kind'] != int(str(action['kind']), 0):
            raise ValueError('Profile kind does not match record')
        check_patchable(record['kind'], action.get('edits', []))
        updated = patch_payload(record['payload'],action)
        if action['action'] == 'replace':
            if index in replaced:
                raise ValueError('A control may only be replaced once')
            replaced.add(index); records[index] = (record['kind'],updated)
        elif action['action'] == 'clone':
            # Explicit name guards avoid emitting a same-name object from this CLI.
            name_at = action['name_offset']
            from mfc_archive import read_string
            old_name = read_string(record['payload'],name_at)['text']
            name_edits = [e for e in action['edits'] if e['type']=='string' and e['offset']==name_at and e['expected']==old_name]
            if len(name_edits)!=1 or name_edits[0]['value']==old_name:
                raise ValueError('Clone requires a unique new control name')
            new_name = name_edits[0]['value']
            if not new_name or any(new_name==s['text'] for _,p in records for s in scan_unicode_strings(p)):
                raise ValueError('Cloned control name is empty or already present')
            records.append((record['kind'],updated))
        else:
            raise ValueError('Only replace and same-window clone are supported')
    import struct
    if controls:
        rebuilt = blob[:parsed['count_offset']]+struct.pack('<I',len(records))+b''.join(pack_record(kind,p) for kind,p in records)+parsed['trailer']
        check = parse_window(rebuilt)
        if check['trailer'] != parsed['trailer']:
            raise ValueError('Window trailer changed')
        windows['lbObjects'][row] = rebuilt
    new_rows = []
    for spec in new_specs:
        new_id, new_blob = plan_window(windows, spec)
        tpl = windows['iID'].index(spec['template_window_id'])
        new_rows.append((new_id, windows['iDeleteFlag'][tpl], windows['iCompileFlag'][tpl],
                         spec['new_name'], spec.get('note', ''), new_blob))
        windows['iID'].append(new_id)
        windows['iDeleteFlag'].append(windows['iDeleteFlag'][tpl])
        windows['iCompileFlag'].append(windows['iCompileFlag'][tpl])
        windows['strName'].append(spec['new_name'])
        windows['strNote'].append(spec.get('note', ''))
        windows['lbObjects'].append(new_blob)
    with output.open('xb') as stream:
        stream.write(raw)
    import pyodbc
    connection = pyodbc.connect(f'DRIVER={{{driver}}};DBQ={dbq};',autocommit=False)
    try:
        if controls:
            connection.cursor().execute('UPDATE WndUser SET lbObjects=? WHERE iID=?',pyodbc.Binary(rebuilt),profile['window_id'])
        for new_id, delflag, compflag, name, note, new_blob in new_rows:
            connection.cursor().execute('INSERT INTO WndUser (iID,iDeleteFlag,iCompileFlag,strName,strNote,lbObjects) VALUES (?,?,?,?,?,?)',
                                        new_id, delflag, compflag, name, note, pyodbc.Binary(new_blob))
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    if snapshot(output) != expected:
        raise ValueError('Unexpected database changes; output is not accepted')
    if source.read_bytes() != raw:
        raise ValueError('Source changed during patch; output requires reinspection')
    return dict(status='DATABASE_ROUNDTRIP_ONLY_HOST_ACCEPTANCE_REQUIRED',output=str(output.resolve()),
                sha256=digest(output.read_bytes()),source_unchanged=True,other_table_values_unchanged=True,
                compile_flags_preserved=True,window_trailer_preserved=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command',required=True)
    read = sub.add_parser('inspect'); read.add_argument('mcp',type=Path)
    write = sub.add_parser('patch'); write.add_argument('mcp',type=Path)
    write.add_argument('--profile',type=Path,required=True)
    write.add_argument('--output',type=Path,required=True)
    write.add_argument('--driver',default='Microsoft Access Driver (*.mdb, *.accdb)')
    args = parser.parse_args()
    if args.command == 'inspect':
        result = inspect(args.mcp)
    else:
        profile = json.loads(args.profile.read_text(encoding='utf-8-sig'))
        for control in profile.get('controls', []):
            for edit in control['edits']:
                if edit['type'] == 'event':
                    edit['program'] = json.loads((args.profile.parent/edit['program_file']).read_text(encoding='utf-8-sig'))
        result = patch(args.mcp,args.output,profile,args.driver)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
