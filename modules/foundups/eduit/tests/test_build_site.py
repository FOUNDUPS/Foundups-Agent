"""Build contracts using the existing renderer boundary, without rendering a movie."""
import importlib.util
import json
from pathlib import Path
import struct
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
MODULE = ROOT / 'modules/foundups/eduit/build_site.py'


def fake_render(output):
    output.mkdir()
    (output / 'little-shrew.mp4').write_bytes(b'video-fixture')
    (output / 'little-shrew.srt').write_text('1\n00:00:00,000 --> 00:00:01,000\nA shrew.\n')
    (output / 'provenance.json').write_text('{"status":"rendered_unreviewed"}')


class BuildSiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        renderer = types.SimpleNamespace(ROOT=ROOT, render=fake_render)
        spec = importlib.util.spec_from_file_location('eduit_build_under_test', MODULE)
        cls.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'render_story_preview': renderer}):
            spec.loader.exec_module(cls.module)

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix='eduit-test-')
        self.addCleanup(self.scratch.cleanup)
        self.output = Path(self.scratch.name) / 'site'

    def test_episode_and_review_bind_to_one_immutable_revision(self):
        receipt = self.module.build(self.output, ['https://storytime-example.web.app'])
        revision = receipt['revision']
        self.assertRegex(revision, r'^[0-9a-f]{16}$')
        episode = (self.output / 'storytime/index.html').read_text(encoding='utf-8')
        self.assertIn(revision, episode)
        self.assertNotIn('__STORYTIME_REVISION__', episode)
        self.assertIn(f'/revisions/{revision}/storytime/game.js', episode)
        self.assertIn(f'/revisions/{revision}/storytime/assets/little-shrew.mp4', episode)
        game = (self.output / f'revisions/{revision}/storytime/game.js').read_text(encoding='utf-8')
        self.assertIn(f'/revisions/{revision}/storytime/activity.mjs', game)
        activity = (self.output / f'revisions/{revision}/storytime/activity.mjs').read_text(encoding='utf-8')
        self.assertIn(f'/revisions/{revision}/storytime/engine.mjs', activity)
        scene = (self.output / f'revisions/{revision}/storytime/scene.mjs').read_text(encoding='utf-8')
        self.assertIn(f'/revisions/{revision}/storytime/rig.mjs', scene)
        review = (self.output / 'review/index.html').read_text(encoding='utf-8')
        self.assertIn(f'/revisions/{revision}/review/review.js', review)
        self.assertIn(f'/revisions/{revision}/storytime/assets/little-shrew.mp4', review)
        manifest = json.loads((self.output / 'manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['scope'], './')
        self.assertEqual(manifest['start_url'], './storytime/')
        self.assertIn(f'/revisions/{revision}/icons/', manifest['icons'][0]['src'])
        worker = (self.output / 'storytime-sw.js').read_text(encoding='utf-8')
        self.assertNotIn('__STORYTIME_', worker)
        self.assertIn('https://storytime-example.web.app', worker)
        shell_line = next(line for line in worker.splitlines() if line.startswith('const SHELL_ASSETS'))
        shell = json.loads(shell_line.partition(' = ')[2].rstrip(';'))
        self.assertIn('/storytime/', shell)
        self.assertFalse(any(path.endswith(('.mp4', '.wav')) or '/review/' in path for path in shell))
        self.assertLess(len(shell), 40)
        self.assertIn('0;url=/storytime/', (self.output / 'index.html').read_text())
        self.assertTrue((self.output / 'about/index.html').is_file())

    def test_revision_changes_with_media_and_existing_output_is_protected(self):
        first = self.module.build(self.output)
        with self.assertRaises(FileExistsError):
            self.module.build(self.output)
        other = Path(self.scratch.name) / 'other'
        def changed_render(output):
            fake_render(output)
            (output / 'little-shrew.mp4').write_bytes(b'changed-video')
        with patch.object(self.module, 'render', changed_render):
            second = self.module.build(other)
        self.assertNotEqual(first['revision'], second['revision'])
        self.assertEqual(first['collection_id'], 'storytime')
        self.assertEqual(second['canonical_origin'], 'https://storytime.eduit.org')

    def test_only_one_prior_immutable_revision_is_carried_forward(self):
        first = self.module.build(self.output)
        second_output = Path(self.scratch.name) / 'second'
        second = self.module.build(second_output, ['https://second.web.app'], self.output)
        self.assertEqual(second['previous_revision'], first['revision'])
        self.assertEqual(len(list((second_output / 'revisions').iterdir())), 2)
        third_output = Path(self.scratch.name) / 'third'
        third = self.module.build(third_output, ['https://third.web.app'], second_output)
        self.assertEqual(third['previous_revision'], second['revision'])
        self.assertFalse((third_output / 'revisions' / first['revision']).exists())
        self.assertTrue((third_output / 'revisions' / second['revision'] /
                         'storytime/assets/little-shrew.mp4').is_file())

    def test_wrong_previous_collection_fails_closed(self):
        self.module.build(self.output)
        receipt_path = self.output / 'revision.json'
        receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
        receipt['collection_id'] = 'another_collection'
        receipt_path.write_text(json.dumps(receipt), encoding='utf-8')
        with self.assertRaises(ValueError):
            self.module.build(Path(self.scratch.name) / 'other', previous_build=self.output)

    def test_origin_allowlist_rejects_wildcards_paths_and_credentials(self):
        for value in ('http://example.org', 'https://*.web.app', 'https://example.org/storytime/',
                      'https://name:secret@example.org', 'https://example.org?redirect=1'):
            with self.subTest(origin=value), self.assertRaises(ValueError):
                self.module.build(self.output, [value])
        self.assertFalse(self.output.exists())

    def test_icons_have_actual_declared_png_dimensions(self):
        for size in (192, 512):
            data = (ROOT / f'public/eduit/icons/storytime-{size}.png').read_bytes()
            self.assertEqual(data[:8], b'\x89PNG\r\n\x1a\n')
            self.assertEqual(struct.unpack('>II', data[16:24]), (size, size))


if __name__ == '__main__':
    unittest.main()
