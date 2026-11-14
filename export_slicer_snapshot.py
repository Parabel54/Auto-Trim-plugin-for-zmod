#!/usr/bin/env python3
"""Optional offline Orca project snapshot; adds no printer G-code. GPL-3.0-only.

Usage: python export_slicer_snapshot.py print.gcode --project project.3mf
Upload both print.gcode and print.gcode.dc.json to the same printer directory.
This archives scoped settings as exported; it does not resolve inheritance or
silently turn object/modifier settings into global defaults.
"""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile
from deep_calibration_gcode import digest, project_physics


def export(gcode_path, project_path, output=None):
    gcode_path, project_path = Path(gcode_path), Path(project_path)
    sha = hashlib.sha256()
    with gcode_path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''): sha.update(chunk)
    parts, size = {}, 0
    with zipfile.ZipFile(project_path) as archive:
        for info in archive.infolist():
            # Read in memory, never extract archive paths to disk.
            if not info.filename.lower().startswith('metadata/') or not info.filename.lower().endswith(('.config', '.json')):
                continue
            size += info.file_size
            if size > 3 * 1024 * 1024: raise ValueError('project settings exceed 3 MiB bound')
            text = archive.read(info).decode('utf-8')
            if info.filename in parts: raise ValueError('duplicate project settings part')
            parts[info.filename] = text
    if not parts: raise ValueError('no Orca metadata settings found in project')
    data = dict(schema=1, gcode_sha256=sha.hexdigest(), settings_parts=parts,
                settings_sha256=digest(parts), physics_sha256=project_physics(parts),
                scope='archived project settings; inheritance and modifier effectiveness not inferred')
    path = Path(output) if output else Path(str(gcode_path) + '.dc.json')
    # Exclusive creation protects an existing snapshot from accidental overwrite.
    with path.open('x') as stream: json.dump(data, stream, indent=2, allow_nan=False)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('gcode'); parser.add_argument('--project', required=True)
    args = parser.parse_args()
    print(export(args.gcode, args.project))


if __name__ == '__main__': main()
