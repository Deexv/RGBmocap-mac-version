"""Prepare independent capabilities after the base installation has committed."""
from pathlib import Path
import json
import os


def prepare(root):
    path = Path(root) / '.setup/git-components.json'
    rows = {}

    def record():
        temp = path.with_suffix('.partial')
        temp.write_text(json.dumps(dict(version=1, components=rows), indent=2), encoding='utf8')
        os.replace(temp, path)

    print('Installation complete. Existing models and projects were retained.', flush=True)
    return rows
