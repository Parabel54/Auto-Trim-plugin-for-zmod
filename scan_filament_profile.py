#!/usr/bin/env python3
"""Read-only scan: print.gcode or an exported filament preset JSON. GPL-3.0-only."""
import argparse
import json
from pathlib import Path
from deep_calibration_gcode import parse_file, filament_profile_scan


def scan(path, parents=()):
    path=Path(path)
    if path.suffix.lower()!='.json':
        snapshot=parse_file(str(path))
        report=snapshot.get('filament_profile')
        if report is None:raise ValueError('filament inventory unavailable')
        report.update(gcode_sha256=snapshot['file_sha256'],source_issues=snapshot['issues'])
        return report
    documents={}
    for name in [path]+[Path(p) for p in parents]:
        if name.stat().st_size>4*1024*1024:raise ValueError('preset JSON exceeds 4 MiB')
        with name.open() as stream:data=json.load(stream)
        if not isinstance(data,dict):raise ValueError('preset must be an object')
        for identity in (str(name),name.stem,data.get('name')):
            if isinstance(identity,str):
                if identity in documents and documents[identity] is not data:raise ValueError('ambiguous preset name: '+identity)
                documents[identity]=data
    missing=[]
    def resolve(data,stack):
        token=id(data)
        if token in stack:raise ValueError('cyclic preset inheritance')
        merged,origins={},{}
        inherited=data.get('inherits') or []
        if isinstance(inherited,str):inherited=[inherited]
        if not isinstance(inherited,list):raise ValueError('unsupported inherits value')
        for identity in inherited:
            if identity not in documents:missing.append(identity);continue
            values,sources=resolve(documents[identity],stack|{token});merged.update(values);origins.update(sources)
        merged.update(data)
        origins.update({key:data.get('name','supplied preset') for key in data})
        return merged,origins
    values,origins=resolve(documents[str(path)],set())
    registry_path=Path(__file__).resolve().parent/'reference/orca_606b50f1/filament_registry_606b50f1.json'
    registry=json.loads(registry_path.read_text())
    return filament_profile_scan(values,registry,scope='preset',origins=origins,unresolved=sorted(set(missing)))


def markdown(report):
    lines=['# Filament profile scan','', 'Profile: '+str(report['profile']),
           'Scope: '+report['scope'],'Unresolved parents: '+', '.join(report['unresolved_parents']),
           '',report['note'],'','| Key | Status | Selected value | Hidden/conditional category | Origin |',
           '|---|---|---|---|---|']
    for row in report['settings']:
        value=json.dumps(row['selected_value'],ensure_ascii=False).replace('|','\\|').replace('\n','\\n')
        lines.append('| `'+row['key']+'` | '+row['status']+' | '+value+' | '+', '.join(row['hidden_categories'])+' | '+str(row['origin']).replace('|','\\|')+' |')
    return '\n'.join(lines)+'\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file');parser.add_argument('--parent',action='append',default=[])
    parser.add_argument('--output',required=True)
    args=parser.parse_args();report=scan(args.file,args.parent)
    out=Path(args.output)
    if out.suffix.lower()!='.json':parser.error('--output must end in .json')
    if out.exists() or out.with_suffix('.md').exists():raise FileExistsError('scan output already exists')
    with out.open('x') as stream:json.dump(report,stream,indent=2,allow_nan=False)
    with out.with_suffix('.md').open('x') as stream:stream.write(markdown(report))
    print(json.dumps(report['counts']))


if __name__=='__main__':main()
