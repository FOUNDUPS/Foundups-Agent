"""Restore only checksum-pinned, already-public website images; never publish."""
import hashlib
import json
from pathlib import Path
from urllib.request import HTTPRedirectHandler, build_opener

ROOT = Path(__file__).resolve().parent


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def restore():
    manifest = json.loads((ROOT / 'public-assets.json').read_text())
    output = ROOT / 'dist' / 'assets'
    output.mkdir(parents=True, exist_ok=True)
    opener = build_opener(NoRedirect())
    for asset in manifest['assets']:
        name = asset['name']
        if Path(name).name != name or Path(name).suffix not in {'.jpg', '.png', '.webp'}:
            raise ValueError('Invalid asset name')
        if asset['url'] != 'https://hornethunter.com/assets/' + name:
            raise ValueError('Asset is outside the published allowlist origin')
        size = asset['bytes']
        if not isinstance(size, int) or not 0 < size <= 10_000_000:
            raise ValueError('Invalid asset size')
        destination = output / name
        if destination.exists() and hashlib.sha256(destination.read_bytes()).hexdigest() == asset['sha256']:
            continue
        with opener.open(asset['url'], timeout=30) as response:
            data = response.read(size + 1)
        if len(data) != size or hashlib.sha256(data).hexdigest() != asset['sha256']:
            raise ValueError('Published asset changed; review manifest before updating: ' + name)
        temporary = output / (name + '.tmp')
        temporary.write_bytes(data)
        temporary.replace(destination)
        print('Restored ' + name)


if __name__ == '__main__':
    restore()
