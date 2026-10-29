import base64
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import urlsplit, parse_qs
import os

FRONTEND = Path(__file__).resolve().parents[1] / 'frontend'


class PublicBuildTests(unittest.TestCase):
    def test_sanitized_video_fields_and_public_assets(self):
        for video in json.loads((FRONTEND / 'videos.json').read_text()):
            self.assertLessEqual(set(video), {'id', 'draft_caption', 'watch_url', 'start_seconds'})
            url = urlsplit(video['watch_url'])
            self.assertEqual((url.scheme, url.netloc, url.path), ('https', 'www.youtube.com', '/watch'))
            self.assertEqual(parse_qs(url.query)['v'], [video['id']])
        for asset in json.loads((FRONTEND / 'public-assets.json').read_text())['assets']:
            self.assertEqual(Path(asset['name']).name, asset['name'])
            self.assertEqual(asset['url'], 'https://hornethunter.com/assets/' + asset['name'])
            self.assertRegex(asset['sha256'], r'^[a-f0-9]{64}$')
            self.assertGreater(asset['bytes'], 0)

    def test_build_metadata_and_private_preview(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ('build.py', 'seo.py', 'videos.json'):
                shutil.copyfile(FRONTEND / name, root / name)
            env = dict(os.environ, HORNET_SITE_URL='https://hornethunter.com', HORNET_PUBLIC='1')
            subprocess.run([sys.executable, '-B', str(root / 'build.py')], env=env, check=True, capture_output=True)
            pages = list((root / 'dist').rglob('index.html'))
            self.assertEqual(len(pages), 17)
            titles = set()
            for path in pages:
                text = path.read_text()
                title = re.search(r'<title>(.*?)</title>', text)[1]
                self.assertNotIn(title, titles)
                titles.add(title)
                self.assertEqual(len(re.findall(r'<h1[ >]', text)), 1)
                self.assertIn('https://www.linkedin.com/in/openstartup/', text)
                self.assertNotIn('mailto:', text)
                self.assertFalse(re.search(r'/forms/d/(?!e/)', text), 'Private form URL found')
                raw = re.search(r'<script type="application/ld\+json">(.*?)</script>', text)[1]
                self.assertIn('@graph', json.loads(raw))
                digest = base64.b64encode(hashlib.sha256(raw.encode()).digest()).decode()
                self.assertIn('sha256-' + digest, text)
            env['HORNET_PUBLIC'] = '0'
            subprocess.run([sys.executable, '-B', str(root / 'build.py')], env=env, check=True, capture_output=True)
            self.assertIn('noindex,nofollow', (root / 'dist/index.html').read_text())
            self.assertIn('Disallow: /', (root / 'dist/robots.txt').read_text())


if __name__ == '__main__':
    unittest.main()
