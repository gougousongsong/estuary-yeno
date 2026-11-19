"""Fetch official verification fixtures by HTTPS and verify their recorded SHA256."""
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

if __name__ == '__main__':
    manifest = json.loads(Path('sources.json').read_text())
    for item in manifest['verificationFixtures']:
        with urlopen(item['url'], timeout=15) as response:
            raw = response.read(200001)
        if len(raw) > 200000 or hashlib.sha256(raw).hexdigest() != item['sha256']:
            raise SystemExit('Upstream fixture changed: '+item['file'])
        Path(item['file']).write_bytes(raw)
        print('verified '+item['file'])
