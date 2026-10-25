"""Package the existing EDUIT scene and Shorts renderer for isolated static hosting.

The immutable revision binds the page, game and rendered media. No provider API,
render endpoint, authentication or child interaction storage belongs in this build.
"""
import argparse
import hashlib
import json
import posixpath
import re
from pathlib import Path
import shutil
import tempfile
from urllib.parse import urlsplit

from render_story_preview import ROOT, render

CANONICAL_ORIGIN = 'https://storytime.eduit.org'
TEXT_ASSETS = {'.html', '.css', '.js', '.mjs', '.json', '.svg', '.srt'}
MEDIA_SUFFIXES = {'.mp4', '.wav', '.mp3', '.webm', '.ogg'}


def _origins(additional):
    result = {CANONICAL_ORIGIN}
    for origin in additional:
        parsed = urlsplit(origin)
        if (parsed.scheme != 'https' or not parsed.hostname or
                not re.fullmatch(r'[a-z0-9.-]+(?::[0-9]+)?', parsed.netloc) or parsed.path or
                parsed.query or parsed.fragment or parsed.username or parsed.password):
            raise ValueError('PWA origins must be exact HTTPS origins without a path')
        result.add(origin)
    return sorted(result)


def _revision(site, origins):
    digest = hashlib.sha256(Path(__file__).read_bytes())
    digest.update(json.dumps(origins).encode())
    for path in sorted(site.rglob('*')):
        if path.is_file():
            digest.update(path.relative_to(site).as_posix().encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


def _rewrite(text, source, assets):
    """Resolve only local, existing asset references; links remain navigation."""
    def reference(value):
        if value.startswith(('#', 'https:', 'http:', 'data:', 'mailto:')):
            return value
        path, separator, query = value.partition('?')
        path, fragment_separator, fragment = path.partition('#')
        resolved = posixpath.normpath(posixpath.join(posixpath.dirname(source), path))
        resolved = resolved.lstrip('/')
        target = assets.get(resolved)
        return (target + (separator + query if separator else '') +
                (fragment_separator + fragment if fragment_separator else '')) if target else value

    # Covers HTML attributes, module imports and existing review template URLs.
    return re.sub(r'([\"\'`])([^\"\'`\s<>]+)\1',
                  lambda match: match[1] + reference(match[2]) + match[1], text)


def _retain_previous(output, previous_build, revision):
    if previous_build is None:
        return None
    previous = Path(previous_build).resolve()
    receipt = json.loads((previous / 'revision.json').read_text(encoding='utf-8'))
    prior = receipt.get('revision', '')
    if (receipt.get('schema') != 'eduit.storytime_build.v1' or
            receipt.get('collection_id') != 'storytime' or
            not re.fullmatch(r'[0-9a-f]{16}', prior)):
        raise ValueError('Previous build must be a verified Story Time revision receipt')
    source = previous / 'revisions' / prior
    if not source.is_dir() or source.is_symlink() or any(path.is_symlink() for path in source.rglob('*')):
        raise ValueError('Previous immutable revision is missing or contains symbolic links')
    if prior != revision:
        shutil.copytree(source, output / 'revisions' / prior)
        return prior
    return None


def build(output, pwa_origins=(), previous_build=None):
    output = Path(output).resolve()
    origins = _origins(pwa_origins)
    if output.exists():
        raise FileExistsError(output)
    with tempfile.TemporaryDirectory(prefix='eduit-build-') as scratch:
        media = Path(scratch) / 'media'
        render(media)
        shutil.copytree(ROOT / 'public/eduit', output)
        # Review tooling remains owned by Shorts; only its mounted asset URLs change.
        shutil.copytree(ROOT / 'modules/communication/youtube_shorts/assets/kids_review',
                        output / 'review')
        shutil.copytree(media, output / 'storytime/assets', dirs_exist_ok=True)
        revision = _revision(output, origins)
        revision_root = output / 'revisions' / revision
        asset_sources = [path for path in output.rglob('*') if path.is_file() and (
            path.relative_to(output).as_posix() == 'style.css' or
            path.relative_to(output).parts[0] in {'storytime', 'icons', 'review'})
            and path.suffix != '.html']
        assets = {path.relative_to(output).as_posix():
                  '/revisions/' + revision + '/' + path.relative_to(output).as_posix()
                  for path in asset_sources}
        for path in asset_sources:
            relative = path.relative_to(output)
            destination = revision_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            data = path.read_bytes()
            if path.suffix in TEXT_ASSETS:
                text = _rewrite(data.decode('utf-8'), relative.as_posix(), assets)
                text = text.replace('__STORYTIME_REVISION__', revision)
                text = text.replace('__STORYTIME_PWA_ORIGINS__', ','.join(origins))
                data = text.encode('utf-8')
            destination.write_bytes(data)
        # Preserve the existing EDUIT introduction without placing it before the episode.
        (output / 'about').mkdir()
        (output / 'about/index.html').write_text(
            _rewrite((output / 'index.html').read_text(encoding='utf-8'), 'index.html', assets)
            .replace('href="storytime/"', 'href="/storytime/"')
            .replace('href="./"', 'href="/about/"'), encoding='utf-8')
        for page in (output / 'storytime/index.html', output / 'review/index.html',
                     output / 'manifest.json'):
            relative = page.relative_to(output).as_posix()
            page.write_text(_rewrite(page.read_text(encoding='utf-8'), relative, assets)
                            .replace('__STORYTIME_REVISION__', revision), encoding='utf-8')
        (output / 'index.html').write_text(
            '<!doctype html><html lang="en"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta http-equiv="refresh" content="0;url=/storytime/">'
            '<title>Story Time</title><a href="/storytime/">Open Story Time</a>'
            f'<small>Revision {revision}</small></html>\n', encoding='utf-8')
        # Only the exact episode shell and bounded non-media inventory are cached.
        shell = ['/storytime/', '/manifest.json'] + sorted(
            value for key, value in assets.items()
            if Path(key).suffix not in MEDIA_SUFFIXES and not key.startswith('review/')
            and not key.endswith('provenance.json'))
        worker = (output / 'storytime-sw.js').read_text(encoding='utf-8')
        worker = worker.replace('__STORYTIME_REVISION__', revision)
        worker = worker.replace('__STORYTIME_SHELL_ASSETS__', json.dumps(shell))
        worker = worker.replace('__STORYTIME_PWA_ORIGINS__', json.dumps(origins))
        (output / 'storytime-sw.js').write_text(worker, encoding='utf-8')
        prior = _retain_previous(output, previous_build, revision)
        receipt = {'schema': 'eduit.storytime_build.v1', 'revision': revision,
                   'foundup_id': 'eduit', 'production_foundup_id': 'kids_episodes',
                   'collection_id': 'storytime', 'story_id': 'little_shrew',
                   'episode_id': 'little_shrew_poc_001', 'publisher_id': 'us_story_time',
                   'previous_revision': prior,
                   'locale': 'en', 'canonical_origin': CANONICAL_ORIGIN,
                   'pwa_origins': origins, 'media_policy': 'immutable-network-only',
                   'assets': assets}
        (output / 'revision.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
        return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--pwa-origin', action='append', default=[],
                        help='Additional exact HTTPS provider staging origin')
    parser.add_argument('--previous-build', help='Prior deployed build; retain its one immutable revision')
    arguments = parser.parse_args()
    print(json.dumps(build(arguments.output_dir, arguments.pwa_origin, arguments.previous_build), indent=2))
