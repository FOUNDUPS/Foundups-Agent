#!/usr/bin/env python3
"""
antifaFM Broadcaster - Headless Launch Script

Run: python modules/platform_integration/antifafm_broadcaster/scripts/launch.py

For Windows Task Scheduler or systemd service.

Debug Switches (environment variables for Occam's layering):
    ANTIFAFM_SKIP_BROWSER=1     - Skip browser automation, just start FFmpeg
    ANTIFAFM_SKIP_FFMPEG=1      - Skip FFmpeg, just test browser automation
    ANTIFAFM_WAIT_BEFORE_FFMPEG=30  - Wait N seconds before starting FFmpeg (default: 10)
    ANTIFAFM_AUTO_GO_LIVE=0     - Skip Go Live automation
    ANTIFAFM_DEBUG_VERBOSE=1    - Extra verbose logging

Integration with main.py:
    from modules.platform_integration.antifafm_broadcaster.scripts.launch import (
        run_antifafm_broadcaster,
        start_antifafm_background,
        stop_antifafm_background,
    )
"""

import asyncio
import logging
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

from modules.platform_integration.antifafm_broadcaster.src import AntifaFMBroadcaster
from modules.infrastructure.instance_lock.src.instance_manager import get_instance_lock

# Global broadcaster instance for background operation
_background_broadcaster: Optional[AntifaFMBroadcaster] = None
_background_task: Optional[asyncio.Task] = None
_background_loop: Optional[asyncio.AbstractEventLoop] = None
_instance_lock = None  # InstanceLock from instance_manager
_obs_threads = []  # OBS orchestration threads (grid + news)

# Lyrics cache - SQLite per WSP 78 (Layer B: Operational Relational Store)
LYRICS_DB_PATH = Path(__file__).parent.parent / "data" / "lyrics_cache.db"
_lyrics_db_conn = None  # SQLite connection, lazy initialized
_lyrics_db_lock = threading.Lock()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(PROJECT_ROOT / "logs" / "antifafm_broadcaster.log")
    ]
)
logger = logging.getLogger(__name__)


def _ensure_karaoke_sources(client):
    """
    Auto-create karaoke text sources in OBS if they don't exist.

    Creates:
    - Lyrics Line 1: Large centered text for current lyric
    - Lyrics Line 2: Smaller text below for next lyric
    """
    scene = client.get_current_program_scene().scene_name

    # Text source configurations
    sources = [
        {
            'name': 'Lyrics Line 1',
            'settings': {
                'text': '',
                'font': {'face': 'Arial Black', 'size': 72, 'style': 'Bold'},
                'color': 0xFFFFFFFF,  # White
                'outline': True,
                'outline_color': 0xFF000000,  # Black outline
                'outline_size': 4,
                'align': 'center',
            },
            'position': {'x': 960, 'y': 400},  # Center of 1920x1080
            'alignment': 4,  # Center alignment
        },
        {
            'name': 'Lyrics Line 2',
            'settings': {
                'text': '',
                'font': {'face': 'Arial', 'size': 48, 'style': 'Regular'},
                'color': 0xCCFFFFFF,  # Slightly transparent white
                'outline': True,
                'outline_color': 0xFF000000,
                'outline_size': 2,
                'align': 'center',
            },
            'position': {'x': 960, 'y': 500},
            'alignment': 4,
        },
    ]

    for src in sources:
        try:
            # Check if source already exists
            client.get_input_settings(src['name'])
            print(f"[OBS-SETUP] '{src['name']}' already exists")
        except Exception:
            # Source doesn't exist - create it
            try:
                # Create text input
                client.create_input(
                    scene_name=scene,
                    input_name=src['name'],
                    input_kind='text_gdiplus_v3',  # Windows text source
                    input_settings=src['settings'],
                    scene_item_enabled=True
                )
                print(f"[OBS-SETUP] Created '{src['name']}'")

                # Position the source
                try:
                    item_id = client.get_scene_item_id(scene, src['name']).scene_item_id
                    client.set_scene_item_transform(scene, item_id, {
                        'positionX': float(src['position']['x']),
                        'positionY': float(src['position']['y']),
                        'alignment': src['alignment'],
                    })
                except Exception as pos_err:
                    print(f"[OBS-SETUP] Could not position '{src['name']}': {pos_err}")

            except Exception as create_err:
                # Try alternative text source type (cross-platform)
                try:
                    client.create_input(
                        scene_name=scene,
                        input_name=src['name'],
                        input_kind='text_ft2_source_v2',  # FreeType2 (Linux/Mac)
                        input_settings=src['settings'],
                        scene_item_enabled=True
                    )
                    print(f"[OBS-SETUP] Created '{src['name']}' (FreeType2)")
                except Exception:
                    print(f"[OBS-SETUP] Could not create '{src['name']}': {create_err}")


def _start_obs_orchestration():
    """
    Start OBS video orchestration components:
    1. Grid Orchestrator - Video rotation synced to songs
    2. News Monitor - Breaking news from international sources

    These run as daemon threads alongside the FFmpeg broadcaster.
    """
    global _obs_threads

    # Check if OBS orchestration is enabled
    if os.getenv("ANTIFAFM_OBS_ORCHESTRATION", "1") == "0":
        print("[OBS] Video orchestration disabled (ANTIFAFM_OBS_ORCHESTRATION=0)")
        return

    try:
        import obsws_python as obs
        import urllib.request
        import json
        import xml.etree.ElementTree as ET

        # Test OBS connection first
        try:
            c = obs.ReqClient(host='localhost', port=4455, password='')
            version = c.get_version()
            print(f'[OBS] Connected - OBS {version.obs_version}')
        except Exception as e:
            print(f'[OBS] Not connected (will skip video orchestration): {e}')
            return

        # Auto-create karaoke text sources if they don't exist
        _ensure_karaoke_sources(c)

        # Grid orchestrator thread
        def run_grid_orchestrator():
            """Run the grid-based video orchestrator with schema + karaoke support."""
            try:
                c = obs.ReqClient(host='localhost', port=4455, password='')
                scene = c.get_current_program_scene().scene_name

                GRID = {
                    'LEFT':  {'x': 0,   'y': 0, 'w': 960,  'h': 910},
                    'RIGHT': {'x': 960, 'y': 0, 'w': 960,  'h': 910},
                    'FULL':  {'x': 0,   'y': 0, 'w': 1920, 'h': 910},
                }

                LAYOUTS = [
                    {'LEFT': 'Charlie Chaplin', 'RIGHT': 'BBC Straits'},
                    {'LEFT': 'antifaFM Background', 'RIGHT': 'Telaviv'},
                    {'FULL': 'Charlie Chaplin'},
                    {'FULL': 'BBC Straits'},
                ]

                videos = ['Charlie Chaplin', 'BBC Straits', 'antifaFM Background', 'Telaviv']
                video_ids = {}
                for name in videos:
                    try:
                        video_ids[name] = c.get_scene_item_id(scene, name).scene_item_id
                    except:
                        pass

                # Karaoke state
                current_lyrics = []  # List of (timestamp_ms, text)
                lyrics_index = 0
                song_start_time = 0

                def apply_layout(idx):
                    """Apply video layout (for VIDEO_GRID and VIDEO_FULL schemas)."""
                    layout = LAYOUTS[idx % len(LAYOUTS)]
                    for name, item_id in video_ids.items():
                        c.set_scene_item_enabled(scene, item_id, False)
                    for cell, video in layout.items():
                        if video in video_ids:
                            item_id = video_ids[video]
                            g = GRID[cell]
                            c.set_scene_item_transform(scene, item_id, {
                                'positionX': float(g['x']), 'positionY': float(g['y']),
                                'boundsType': 'OBS_BOUNDS_SCALE_INNER',
                                'boundsWidth': float(g['w']), 'boundsHeight': float(g['h']),
                            })
                            c.set_scene_item_enabled(scene, item_id, True)
                    return list(layout.values())

                def apply_karaoke_layout():
                    """Apply karaoke layout - hide videos, show lyrics background."""
                    for name, item_id in video_ids.items():
                        c.set_scene_item_enabled(scene, item_id, False)
                    # Hide entangled visualizer if visible
                    try:
                        c.set_input_settings('Entangled Visualizer', {'shutdown': True}, True)
                    except:
                        pass
                    # Show antifaFM Background for karaoke (dark background)
                    if 'antifaFM Background' in video_ids:
                        item_id = video_ids['antifaFM Background']
                        c.set_scene_item_transform(scene, item_id, {
                            'positionX': 0.0, 'positionY': 0.0,
                            'boundsType': 'OBS_BOUNDS_SCALE_INNER',
                            'boundsWidth': 1920.0, 'boundsHeight': 910.0,
                        })
                        c.set_scene_item_enabled(scene, item_id, True)

                def apply_entangled_layout():
                    """Apply entangled Bell state layout - hide videos, show visualizer."""
                    # Hide all videos
                    for name, item_id in video_ids.items():
                        c.set_scene_item_enabled(scene, item_id, False)
                    # Show Entangled Visualizer browser source (full screen)
                    # Source must be named "Entangled Visualizer" in OBS
                    try:
                        # Get scene item ID for browser source
                        items = c.get_scene_item_list(scene).scene_items
                        for item in items:
                            if item.get('sourceName') == 'Entangled Visualizer':
                                item_id = item['sceneItemId']
                                c.set_scene_item_transform(scene, item_id, {
                                    'positionX': 0.0, 'positionY': 0.0,
                                    'boundsType': 'OBS_BOUNDS_SCALE_INNER',
                                    'boundsWidth': 1920.0, 'boundsHeight': 910.0,
                                })
                                c.set_scene_item_enabled(scene, item_id, True)
                                print('[OBS-GRID] Entangled Visualizer enabled')
                                return
                        print('[OBS-GRID] WARNING: "Entangled Visualizer" source not found in OBS')
                        print('[OBS-GRID] Add Browser Source named "Entangled Visualizer" pointing to:')
                        print('[OBS-GRID] file:///O:/Foundups-Agent/modules/platform_integration/antifafm_broadcaster/assets/entangled_visualizer.html')
                    except Exception as e:
                        print(f'[OBS-GRID] Entangled layout error: {e}')

                def update_lyrics_display(line1: str, line2: str = ''):
                    """Update lyrics OBS text sources."""
                    # Uses 'Lyrics Line 1' and 'Lyrics Line 2' text sources in OBS
                    try:
                        c.set_input_settings('Lyrics Line 1', {'text': line1.upper()}, True)
                        c.set_input_settings('Lyrics Line 2', {'text': line2.upper()}, True)
                    except:
                        # Fall back to Now Playing if dedicated lyrics sources don't exist
                        combined = line1 + ('\n' + line2 if line2 else '')
                        c.set_input_settings('Now Playing', {'text': combined.upper()}, True)

                def get_song_with_elapsed():
                    """Get current song AND elapsed time from antifaFM API."""
                    try:
                        req = urllib.request.Request(
                            'https://a12.asurahosting.com/api/nowplaying',
                            headers={'User-Agent': 'Mozilla/5.0'}
                        )
                        with urllib.request.urlopen(req, timeout=10) as resp:
                            data = json.loads(resp.read().decode('utf-8'))
                        for s in data:
                            if 'antifa' in s.get('station', {}).get('name', '').lower():
                                song = s.get('now_playing', {}).get('song', {})
                                elapsed = s.get('now_playing', {}).get('elapsed', 0)
                                return song.get('artist', ''), song.get('title', ''), elapsed
                    except:
                        pass
                    return '', '', 0

                print('[OBS-GRID] Starting video orchestrator (schema-aware)')
                layout_idx = 0
                last_song = None
                last_schema = None
                apply_layout(0)

                while True:
                    try:
                        current_schema = get_schema()
                        artist, title, elapsed_sec = get_song_with_elapsed()
                        song_key = artist + title
                        elapsed_ms = elapsed_sec * 1000

                        # Schema changed?
                        if current_schema != last_schema:
                            last_schema = current_schema
                            print(f'[OBS-GRID] Schema changed to {current_schema}')
                            if current_schema == 'KARAOKE':
                                apply_karaoke_layout()
                            elif current_schema == 'ENTANGLED':
                                apply_entangled_layout()
                            elif current_schema == 'VIDEO_FULL':
                                # Show first video full screen
                                apply_layout(2)  # FULL layout
                            else:
                                apply_layout(layout_idx)

                        # Song changed?
                        if song_key != last_song and title:
                            last_song = song_key
                            layout_idx = (layout_idx + 1) % len(LAYOUTS)

                            # Update Now Playing
                            np = 'NOW PLAYING: ' + (artist.upper() + ' - ' if artist else '') + title.upper()
                            c.set_input_settings('Now Playing', {'text': np}, True)

                            safe = title.encode('ascii', 'replace').decode('ascii')[:25]
                            print(f'[OBS-GRID] {safe}')

                            # Fetch lyrics for karaoke
                            current_lyrics = fetch_lyrics(artist, title)
                            lyrics_index = 0
                            if current_lyrics:
                                print(f'[KARAOKE] Loaded {len(current_lyrics)} lines')
                            else:
                                print(f'[KARAOKE] No lyrics found')

                            # Apply layout if in video mode
                            if current_schema in ('VIDEO_GRID', 'VIDEO_FULL', 'NEWS'):
                                if current_schema == 'VIDEO_FULL':
                                    apply_layout(2)
                                else:
                                    apply_layout(layout_idx)

                        # Update lyrics display in KARAOKE mode
                        if current_schema == 'KARAOKE' and current_lyrics:
                            # Find current line based on elapsed time
                            while (lyrics_index < len(current_lyrics) - 1 and
                                   current_lyrics[lyrics_index + 1][0] <= elapsed_ms):
                                lyrics_index += 1

                            line1 = current_lyrics[lyrics_index][1] if lyrics_index < len(current_lyrics) else ''
                            line2 = current_lyrics[lyrics_index + 1][1] if lyrics_index + 1 < len(current_lyrics) else ''
                            update_lyrics_display(line1, line2)

                        time.sleep(1 if current_schema == 'KARAOKE' else 5)
                    except Exception as e:
                        print(f'[OBS-GRID] Error: {e}')
                        time.sleep(5)
            except Exception as e:
                print(f'[OBS-GRID] Fatal error: {e}')

        # News monitor thread
        def run_news_monitor():
            """Monitor international news for breaking alerts."""
            try:
                c = obs.ReqClient(host='localhost', port=4455, password='')

                RSS_FEEDS = {
                    'Al Jazeera': 'https://www.aljazeera.com/xml/rss/all.xml',
                    'BBC': 'https://feeds.bbci.co.uk/news/world/rss.xml',
                    'Guardian': 'https://www.theguardian.com/world/rss',
                    'France24': 'https://www.france24.com/en/rss',
                    'DW': 'https://rss.dw.com/xml/rss-en-world',
                }

                KEYWORDS = ['iran', 'tehran', 'attack', 'missile', 'strike', 'war',
                            'beirut', 'israel', 'hezbollah', 'idf', 'bombing']

                seen_titles = set()

                def scan_news():
                    alerts = []
                    for source, url in RSS_FEEDS.items():
                        try:
                            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                            with urllib.request.urlopen(req, timeout=10) as response:
                                content = response.read().decode('utf-8', errors='ignore')

                            root = ET.fromstring(content)
                            for item in root.findall('.//item')[:10]:
                                title_el = item.find('title')
                                if title_el is not None and title_el.text:
                                    title = title_el.text.strip()
                                    if any(kw in title.lower() for kw in KEYWORDS):
                                        if title not in seen_titles:
                                            seen_titles.add(title)
                                            safe = title.encode('ascii', 'replace').decode('ascii')[:70]
                                            alerts.append(safe.upper())
                        except:
                            pass
                    return alerts[:5]

                def update_ticker(alerts):
                    # Clean separator (no >>> <<< noise)
                    ticker_parts = alerts.copy()
                    ticker_parts.extend(['ANTIFAFM.COM', 'FOUNDUPS.COM'])
                    # Red dot separator (on brand) - cleaner than ***
                    ticker_text = '  ●  '.join(ticker_parts)
                    # Larger font for mobile viewing (48pt -> 64pt)
                    c.set_input_settings('Scrolling Ticker', {
                        'text': ticker_text,
                        'font': {'face': 'Arial Black', 'size': 64, 'style': 'Bold'}
                    }, True)

                print('[OBS-NEWS] Starting news monitor')

                # Initial scan
                alerts = scan_news()
                if alerts:
                    update_ticker(alerts)
                    print(f'[OBS-NEWS] Loaded {len(alerts)} alerts')

                while True:
                    time.sleep(300)  # 5 minutes
                    new_alerts = scan_news()
                    if new_alerts:
                        update_ticker(new_alerts)
                        print(f'[OBS-NEWS] Updated: {new_alerts[0][:40]}...')
            except Exception as e:
                print(f'[OBS-NEWS] Fatal error: {e}')

        # Start both threads
        grid_thread = threading.Thread(target=run_grid_orchestrator, daemon=True, name="obs-grid")
        news_thread = threading.Thread(target=run_news_monitor, daemon=True, name="obs-news")

        grid_thread.start()
        news_thread.start()

        _obs_threads.extend([grid_thread, news_thread])
        print('[OBS] Video orchestration started (grid + news)')

        # Boot Layer Rotator - GCC shipping, chess, etc. schema rotation
        if os.getenv("ANTIFAFM_BOOT_ROTATOR_ENABLED", "0") == "1":
            try:
                from modules.platform_integration.antifafm_broadcaster.skillz.boot_layer_rotator.executor import (
                    rotation_daemon as boot_rotator_daemon
                )

                def run_boot_rotator():
                    """Run boot layer schema rotation (GCC -> Video -> News -> ...)"""
                    try:
                        import asyncio
                        import logging as bg_logging

                        # Suppress INFO logs from background daemons to console
                        # (logs still go to file via FileHandler)
                        for mod_name in [
                            'modules.platform_integration.antifafm_broadcaster.skillz.gcc_shipping_tracker.executor',
                            'modules.platform_integration.antifafm_broadcaster.skillz.boot_layer_rotator.executor',
                            'obsws_python.baseclient.ObsClient',
                            'obsws_python.reqs.ReqClient',
                        ]:
                            bg_logging.getLogger(mod_name).setLevel(bg_logging.WARNING)

                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        print('[OBS-ROTATOR] Starting boot layer rotation (10-min schemas)')
                        loop.run_until_complete(boot_rotator_daemon())
                    except Exception as e:
                        print(f'[OBS-ROTATOR] Fatal error: {e}')

                rotator_thread = threading.Thread(target=run_boot_rotator, daemon=True, name="obs-rotator")
                rotator_thread.start()
                _obs_threads.append(rotator_thread)
                print('[OBS] Boot layer rotator started (ANTIFAFM_BOOT_ROTATOR_ENABLED=1)')

            except ImportError as e:
                print(f'[OBS] Boot layer rotator import failed: {e}')
        else:
            print('[OBS] Boot layer rotator disabled (set ANTIFAFM_BOOT_ROTATOR_ENABLED=1 to enable)')

    except ImportError:
        print('[OBS] obsws_python not installed - skipping video orchestration')
    except Exception as e:
        print(f'[OBS] Orchestration error: {e}')

    # NOTE: Chat agents now start AFTER stream verification (not at preflight)
    # See _start_chat_agents_delayed() called after stream is live


def _start_chat_agents():
    """
    Start AI chat agents for antifaFM stream engagement.
    Uses existing livechat module - NO NEW CODE (WSP 84).

    Layer 2.5B from ROADMAP.md - marked READY.

    PID Violation Fix: Sets ANTIFAFM_CHAT_ACTIVE=1 so main YT DAE
    excludes antifafm from rotation when broadcaster is running.
    """
    global _obs_threads

    try:
        # Set env vars to focus on antifaFM channel
        os.environ["YT_FORCE_CHANNEL"] = "antifafm"
        os.environ["YT_ACTIVE_PERSONA"] = "antifafm"
        # Signal to main YT DAE: exclude antifafm from rotation
        os.environ["ANTIFAFM_CHAT_ACTIVE"] = "1"

        def run_chat_agent():
            """Run AutoModeratorDAE for antifaFM chat engagement."""
            try:
                import asyncio
                from modules.communication.livechat.src.auto_moderator_dae import AutoModeratorDAE

                print('[CHAT] Starting antifaFM chat agent (AutoModeratorDAE)')

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                dae = AutoModeratorDAE(enable_ai_monitoring=False)
                loop.run_until_complete(dae.run())

            except Exception as e:
                print(f'[CHAT] Fatal error: {e}')

        chat_thread = threading.Thread(target=run_chat_agent, daemon=True, name="antifafm-chat")
        chat_thread.start()
        _obs_threads.append(chat_thread)
        print('[CHAT] AI chat agent started (antifaFM persona)')

    except ImportError as e:
        print(f'[CHAT] livechat module not available: {e}')
    except Exception as e:
        print(f'[CHAT] Chat agent error: {e}')


# ============================================================================
# SCHEMA SYSTEM + KARAOKE (Layer 2.5D)
# ============================================================================

# File-based schema signal (cross-process communication)
SCHEMA_FILE = Path(__file__).parent.parent / "data" / "current_schema.txt"
_schema_lock = threading.Lock()

SCHEMAS = {
    'VIDEO_GRID': 'Grid layout with song-synced rotation',
    'VIDEO_FULL': 'Single video full screen',
    'KARAOKE': 'Lyrics display mode',
    'NEWS': 'News-focused layout with large ticker',
    'ENTANGLED': 'Bell state 0102↔0201 audio-reactive visualization',
}


def set_schema(schema_name: str) -> bool:
    """
    Set the current display schema via file signal.
    Works across processes - any script can switch the live stream.

    Usage:
        set_schema('KARAOKE')  # Python
        echo KARAOKE > data/current_schema.txt  # CLI
    """
    schema = schema_name.upper()
    if schema not in SCHEMAS:
        return False
    with _schema_lock:
        SCHEMA_FILE.parent.mkdir(parents=True, exist_ok=True)
        SCHEMA_FILE.write_text(schema)
        print(f'[SCHEMA] Switched to {schema}')
    return True


def get_schema() -> str:
    """
    Get current schema from file signal.
    OBS orchestration calls this every loop to detect changes.
    """
    try:
        if SCHEMA_FILE.exists():
            schema = SCHEMA_FILE.read_text().strip().upper()
            if schema in SCHEMAS:
                return schema
    except Exception:
        pass
    return 'VIDEO_GRID'  # Default


def _normalize_cache_key(artist: str, title: str) -> str:
    """Normalize artist/title for cache lookup (lowercase, stripped)."""
    artist_norm = (artist or '').lower().strip()
    title_norm = (title or '').lower().strip()
    return f"{artist_norm}|{title_norm}"


def _get_lyrics_db():
    """
    Get SQLite connection for lyrics cache (WSP 78 Layer B).

    Creates table if not exists. Uses WAL mode for concurrent access.
    Table: modules_lyrics_cache (WSP 78 namespace contract)
    """
    global _lyrics_db_conn
    import sqlite3
    import json

    with _lyrics_db_lock:
        if _lyrics_db_conn is not None:
            return _lyrics_db_conn

        LYRICS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _lyrics_db_conn = sqlite3.connect(str(LYRICS_DB_PATH), check_same_thread=False)
        _lyrics_db_conn.row_factory = sqlite3.Row

        # WSP 78 SQLite policy
        _lyrics_db_conn.execute("PRAGMA journal_mode=WAL")
        _lyrics_db_conn.execute("PRAGMA synchronous=NORMAL")
        _lyrics_db_conn.execute("PRAGMA busy_timeout=5000")

        # Create table (WSP 78 namespace: modules_*)
        _lyrics_db_conn.execute("""
            CREATE TABLE IF NOT EXISTS modules_lyrics_cache (
                cache_key TEXT PRIMARY KEY,
                artist TEXT NOT NULL,
                title TEXT NOT NULL,
                lyrics_json TEXT NOT NULL,
                source TEXT NOT NULL,
                line_count INTEGER DEFAULT 0,
                cached_at TEXT NOT NULL
            )
        """)
        _lyrics_db_conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_lyrics_artist ON modules_lyrics_cache(artist)
        """)
        _lyrics_db_conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_lyrics_source ON modules_lyrics_cache(source)
        """)
        _lyrics_db_conn.commit()

        # Log cache size
        cursor = _lyrics_db_conn.execute("SELECT COUNT(*) FROM modules_lyrics_cache")
        count = cursor.fetchone()[0]
        print(f'[LYRICS-DB] Initialized with {count} cached songs')

        return _lyrics_db_conn


def _save_lyrics_to_cache(artist: str, title: str, lyrics: list, source: str = 'lrclib'):
    """
    Save lyrics to SQLite cache (WSP 78 Layer B).

    Args:
        artist: Song artist
        title: Song title
        lyrics: List of (timestamp_ms, line_text) tuples
        source: Where lyrics came from ('lrclib-synced', 'lrclib-plain', 'lrclib-miss', 'manual-lrc')
    """
    import json
    from datetime import datetime

    key = _normalize_cache_key(artist, title)
    lyrics_json = json.dumps(lyrics, ensure_ascii=False)

    try:
        conn = _get_lyrics_db()
        with _lyrics_db_lock:
            conn.execute("""
                INSERT INTO modules_lyrics_cache (cache_key, artist, title, lyrics_json, source, line_count, cached_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    lyrics_json = excluded.lyrics_json,
                    source = excluded.source,
                    line_count = excluded.line_count,
                    cached_at = excluded.cached_at
            """, (key, artist, title, lyrics_json, source, len(lyrics), datetime.now().isoformat()))
            conn.commit()
        print(f'[LYRICS-DB] Saved: {title} by {artist} ({len(lyrics)} lines, {source})')
    except Exception as e:
        print(f'[LYRICS-DB] Save error: {e}')


def get_cached_lyrics(artist: str, title: str) -> Optional[list]:
    """
    Check if lyrics exist in SQLite cache.

    Returns list of (timestamp_ms, text) tuples if cached, None otherwise.
    """
    import json

    key = _normalize_cache_key(artist, title)

    try:
        conn = _get_lyrics_db()
        cursor = conn.execute(
            "SELECT lyrics_json, source FROM modules_lyrics_cache WHERE cache_key = ?",
            (key,)
        )
        row = cursor.fetchone()
        if row:
            lyrics = json.loads(row['lyrics_json'])
            # Convert inner lists back to tuples
            lyrics = [(ts, text) for ts, text in lyrics]
            print(f'[LYRICS-DB] Hit: {title} ({row["source"]})')
            return lyrics
    except Exception as e:
        print(f'[LYRICS-DB] Lookup error: {e}')

    return None


def fetch_lyrics(artist: str, title: str) -> list:
    """
    Fetch synchronized lyrics - cache first, then LrcLib API.

    As songs play, lyrics are automatically cached for future karaoke use.
    Cache location: antifafm_broadcaster/data/lyrics_cache.json

    Returns list of (timestamp_ms, line_text) tuples.
    Empty list if no lyrics found.
    """
    import urllib.request
    import urllib.parse
    import json

    if not title:
        return []

    # 1. Check cache first (instant, no API call)
    cached = get_cached_lyrics(artist, title)
    if cached is not None:
        return cached

    # 2. Cache miss - fetch from LrcLib API
    print(f'[LYRICS-CACHE] Miss: {title} - fetching from LrcLib...')
    try:
        # LrcLib API - free, no key needed
        query = urllib.parse.urlencode({
            'artist_name': artist or '',
            'track_name': title,
        })
        url = f'https://lrclib.net/api/search?{query}'

        req = urllib.request.Request(url, headers={
            'User-Agent': 'antifaFM-Karaoke/1.0',
            'Accept': 'application/json'
        })

        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))

        if not data:
            # Cache the miss to avoid repeated API calls
            _save_lyrics_to_cache(artist, title, [], source='lrclib-miss')
            return []

        # Get first result with synced lyrics
        for result in data:
            synced = result.get('syncedLyrics', '')
            if synced:
                lyrics = _parse_lrc(synced)
                # 3. Cache successful fetch
                _save_lyrics_to_cache(artist, title, lyrics, source='lrclib-synced')
                return lyrics

        # Fall back to plain lyrics (no timing)
        for result in data:
            plain = result.get('plainLyrics', '')
            if plain:
                lyrics = [(0, line) for line in plain.split('\n') if line.strip()]
                _save_lyrics_to_cache(artist, title, lyrics, source='lrclib-plain')
                return lyrics

        # No lyrics found - cache the miss
        _save_lyrics_to_cache(artist, title, [], source='lrclib-miss')

    except Exception as e:
        print(f'[KARAOKE] Lyrics fetch error: {e}')

    return []


def _parse_lrc(lrc_content: str) -> list:
    """
    Parse .lrc format into (timestamp_ms, text) tuples.

    LRC format: [mm:ss.xx] lyrics text
    """
    import re
    lines = []
    pattern = re.compile(r'\[(\d{2}):(\d{2})\.(\d{2,3})\](.*)')

    for line in lrc_content.split('\n'):
        match = pattern.match(line)
        if match:
            minutes = int(match.group(1))
            seconds = int(match.group(2))
            centis = match.group(3)
            # Handle both .xx and .xxx formats
            if len(centis) == 2:
                millis = int(centis) * 10
            else:
                millis = int(centis)

            timestamp_ms = (minutes * 60 + seconds) * 1000 + millis
            text = match.group(4).strip()
            if text:
                lines.append((timestamp_ms, text))

    return sorted(lines, key=lambda x: x[0])


def import_lrc_file(artist: str, title: str, lrc_path: str) -> bool:
    """
    Import an .lrc file into the lyrics cache.

    Use this to add lyrics for songs not in LrcLib, or to correct bad timestamps.

    Usage:
        python -c "from launch import import_lrc_file; import_lrc_file('Artist', 'Title', 'song.lrc')"

    Returns True if successful.
    """
    try:
        with open(lrc_path, 'r', encoding='utf-8') as f:
            lrc_content = f.read()
        lyrics = _parse_lrc(lrc_content)
        if lyrics:
            _save_lyrics_to_cache(artist, title, lyrics, source='manual-lrc')
            print(f'[LYRICS-DB] Imported {len(lyrics)} lines for: {title} by {artist}')
            return True
        else:
            print(f'[LYRICS-DB] No valid lyrics found in {lrc_path}')
            return False
    except Exception as e:
        print(f'[LYRICS-DB] Import error: {e}')
        return False


def get_lyrics_cache_stats() -> dict:
    """
    Get lyrics cache statistics from SQLite.

    Returns dict with:
        - total: Total cached songs
        - synced: Songs with synced lyrics
        - plain: Songs with plain lyrics
        - misses: Songs with no lyrics (cached miss)
        - manual: Manually imported lyrics
    """
    stats = {'total': 0, 'synced': 0, 'plain': 0, 'misses': 0, 'manual': 0}
    try:
        conn = _get_lyrics_db()
        cursor = conn.execute("SELECT COUNT(*) FROM modules_lyrics_cache")
        stats['total'] = cursor.fetchone()[0]

        cursor = conn.execute("SELECT COUNT(*) FROM modules_lyrics_cache WHERE source LIKE '%synced%'")
        stats['synced'] = cursor.fetchone()[0]

        cursor = conn.execute("SELECT COUNT(*) FROM modules_lyrics_cache WHERE source LIKE '%plain%'")
        stats['plain'] = cursor.fetchone()[0]

        cursor = conn.execute("SELECT COUNT(*) FROM modules_lyrics_cache WHERE source LIKE '%miss%'")
        stats['misses'] = cursor.fetchone()[0]

        cursor = conn.execute("SELECT COUNT(*) FROM modules_lyrics_cache WHERE source LIKE '%manual%'")
        stats['manual'] = cursor.fetchone()[0]
    except Exception as e:
        print(f'[LYRICS-DB] Stats error: {e}')

    return stats


def process_schema_command(message: str) -> dict:
    """
    Process schema switching commands from chat.

    Commands:
        !karaoke  - Switch to karaoke mode (lyrics display)
        !video    - Switch to video grid mode
        !grid     - Same as !video
        !full     - Single video full screen
        !news     - News-focused layout

    Returns:
        dict with 'handled' (bool), 'schema' (str or None), 'response' (str)
    """
    msg = message.strip().lower()

    # Command mapping (with common typo variants)
    commands = {
        '!karaoke': 'KARAOKE',
        '!karaoki': 'KARAOKE',      # Common typo
        '!karaokie': 'KARAOKE',     # Common typo
        '!lyrics': 'KARAOKE',
        '!video': 'VIDEO_GRID',
        '!grid': 'VIDEO_GRID',
        '!videos': 'VIDEO_GRID',
        '!full': 'VIDEO_FULL',
        '!fullscreen': 'VIDEO_FULL',
        '!news': 'NEWS',
        '!entangled': 'ENTANGLED',
        '!bell': 'ENTANGLED',       # Bell state alias
        '!0102': 'ENTANGLED',       # Identity alias
        '!wave': 'ENTANGLED',       # Simple alias
    }

    if msg in commands:
        schema = commands[msg]
        success = set_schema(schema)
        return {
            'handled': True,
            'schema': schema,
            'response': f'Switched to {schema} mode' if success else f'Failed to switch to {schema}'
        }

    # Also support /commands (slash style)
    if msg.startswith('/'):
        slash_cmd = '!' + msg[1:]
        if slash_cmd in commands:
            schema = commands[slash_cmd]
            success = set_schema(schema)
            return {
                'handled': True,
                'schema': schema,
                'response': f'Switched to {schema} mode' if success else f'Failed to switch to {schema}'
            }

    return {'handled': False, 'schema': None, 'response': None}


def get_antifafm_schema_status() -> dict:
    """
    Get current antifaFM schema status for API/CLI.
    """
    return {
        'current_schema': get_schema(),
        'available_schemas': list(SCHEMAS.keys()),
        'commands': ['!karaoke', '!video', '!grid', '!full', '!news'],
    }


def _get_antifafm_youtube_token_set() -> Optional[int]:
    """Return the credential set reserved for antifaFM OAuth operations."""
    raw_value = os.getenv("ANTIFAFM_YOUTUBE_TOKEN_SET", "10").strip()
    if raw_value.isdigit():
        return int(raw_value)
    logger.warning(f"[RADIO] Invalid ANTIFAFM_YOUTUBE_TOKEN_SET={raw_value!r}; falling back to auto-selection")
    return None


def _get_antifafm_broadcast_channel_id() -> str:
    """Return the YouTube channel ID that currently hosts the antifaFM stream."""
    # For antifaFM broadcaster, use ANTIFAFM channel - NOT FOUNDUPS_CHANNEL_ID fallback
    return os.getenv(
        "ANTIFAFM_BROADCAST_CHANNEL_ID",
        os.getenv("ANTIFAFM_CHANNEL_ID", "UCVSmg5aOhP4tnQ9KFUg97qA"),
    )


def _preflight_antifafm_youtube_auth(auto_reauth: bool = False) -> dict:
    """
    Validate the antifaFM YouTube OAuth token and optionally trigger re-auth.

    antifaFM should use its dedicated YouTube credential set instead of the
    general multi-account auto-rotation path.
    """
    token_set = _get_antifafm_youtube_token_set()
    result = {
        "token_set": token_set,
        "healthy": [],
        "expired": [],
        "missing": [],
        "reauth_needed": False,
        "checked": False,
        "channel_id": None,
        "channel_title": None,
        "channel_match": None,
    }

    try:
        from modules.platform_integration.youtube_auth.src.youtube_auth import preflight_oauth_check

        credential_sets = [token_set] if token_set is not None else None
        result = {
            "token_set": token_set,
            **preflight_oauth_check(
                auto_reauth=auto_reauth,
                credential_sets=credential_sets,
            ),
            "checked": True,
        }
    except Exception as e:
        logger.warning(f"[RADIO] YouTube OAuth preflight unavailable: {e}")
        result["error"] = str(e)

    if result.get("healthy"):
        try:
            from modules.platform_integration.youtube_auth.src.youtube_auth import get_authenticated_service

            expected_channel_id = _get_antifafm_broadcast_channel_id()
            youtube = get_authenticated_service(token_index=token_set)
            response = youtube.channels().list(part="id,snippet", mine=True).execute()
            items = response.get("items", [])
            if items:
                channel = items[0]
                result["channel_id"] = channel.get("id")
                result["channel_title"] = channel.get("snippet", {}).get("title")
                result["channel_match"] = result["channel_id"] == expected_channel_id
                if result["channel_match"]:
                    print(f"[RADIO] YouTube OAuth ready for set {result['healthy'][0]}")
                else:
                    result["reauth_needed"] = True
                    print(
                        f"[RADIO] YouTube OAuth channel mismatch: "
                        f"{result['channel_title']} ({result['channel_id']})"
                    )
                    print(f"[RADIO] Expected broadcast channel: {expected_channel_id}")
                    print(
                        f"[RADIO] Re-auth set {token_set} while selecting the antifaFM brand channel."
                    )
        except Exception as e:
            logger.warning(f"[RADIO] Could not validate YouTube channel identity: {e}")
    elif result.get("reauth_needed"):
        set_label = result.get("token_set", "unknown")
        print(f"[RADIO] YouTube OAuth re-auth required for set {set_label}")
        print(f"[RADIO] Manual fix: python modules/platform_integration/youtube_auth/scripts/authorize_set{set_label}.py")
    elif result.get("missing"):
        print(f"[RADIO] YouTube OAuth token missing for set {result['missing'][0]}")

    return result


def _force_reauth_antifafm_youtube_auth() -> dict:
    """Force a fresh OAuth flow for the configured antifaFM token set."""
    token_set = _get_antifafm_youtube_token_set()
    result = {
        "token_set": token_set,
        "forced": False,
        "success": False,
    }

    if token_set is None:
        result["error"] = "invalid_token_set"
        return result

    script_path = PROJECT_ROOT / "modules" / "platform_integration" / "youtube_auth" / "scripts" / f"authorize_set{token_set}.py"
    if not script_path.exists():
        result["error"] = f"missing_authorize_script:{script_path}"
        return result

    print(f"[RADIO] Forcing YouTube OAuth re-auth for set {token_set}...")
    completed = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(PROJECT_ROOT),
    )
    result["forced"] = True
    result["exit_code"] = completed.returncode
    result["success"] = completed.returncode == 0

    post_check = _preflight_antifafm_youtube_auth(auto_reauth=False)
    result.update(post_check)
    return result


async def _prepare_youtube_live_endpoint():
    """
    Best-effort YouTube Studio activation before FFmpeg starts.

    This keeps the default headless launcher aligned with the documented flow
    and with the existing background-start behavior.

    When ANTIFAFM_USE_OBS=1, this function is skipped entirely since OBS
    handles the stream connection via RTMP directly.
    """
    go_live_driver = None

    # OBS MODE: Skip all browser automation - OBS handles streaming directly
    if os.getenv("ANTIFAFM_USE_OBS", "0") == "1":
        print("[RADIO] OBS MODE: Skipping Go Live automation (OBS handles RTMP)")
        print("[RADIO] OBS MODE: Only chat agents + OBS WebSocket will run")
        return None

    if os.getenv("ANTIFAFM_AUTO_GO_LIVE", "1") != "1":
        return None

    print("[RADIO] Setting up YouTube Live stream...")
    print("[RADIO] Step 1: Connecting to Edge...")
    try:
        from modules.platform_integration.antifafm_broadcaster.src.youtube_go_live import (
            click_go_live,
            _connect_to_chrome,
            _get_studio_page_state,
        )

        go_live_driver = _connect_to_chrome()
        if go_live_driver:
            print("[RADIO] Step 2: Browser connected - preparing Studio stream page...")

            # Use await since we're already in an async context
            go_live_result = await click_go_live(go_live_driver)

            print(f"[RADIO] Go Live result: {go_live_result}")

            if go_live_result.get("success"):
                if go_live_result.get("already_live"):
                    print("[RADIO] Stream already active - ready for FFmpeg!")
                else:
                    print("[RADIO] YouTube Live stream ACTIVATED!")
                    print(f"[RADIO] Stream URL: {go_live_result.get('url', 'N/A')}")

                print("[RADIO] Waiting for YouTube RTMP endpoint to be ready...")
                endpoint_ready = False
                for wait_attempt in range(10):
                    time.sleep(3)
                    try:
                        ready_check = _get_studio_page_state(go_live_driver)
                        ready_check["has_live"] = ready_check.get("has_end_stream", False)
                        print(f"[RADIO] Endpoint check {wait_attempt+1}/10: {ready_check}")

                        encoder_ready = ready_check.get('has_encoder') and not ready_check.get('has_go_live_button')
                        if encoder_ready or ready_check.get('has_end_stream') or ready_check.get('has_live'):
                            endpoint_ready = True
                            print("[RADIO] YouTube RTMP endpoint is READY!")
                            break
                    except Exception as e:
                        print(f"[RADIO] Endpoint check error: {e}")

                if not endpoint_ready:
                    print("[RADIO] WARNING: Could not confirm endpoint ready - FFmpeg may fail!")
            else:
                print(f"[RADIO] WARNING: Go Live may have failed: {go_live_result.get('error')}")
                if go_live_result.get('available'):
                    print(f"[RADIO] Available buttons found: {go_live_result.get('available')[:5]}")
                # Safety wait even when Go Live fails - give endpoint time to stabilize
                print("[RADIO] Waiting 10s for endpoint to stabilize before FFmpeg...")
                time.sleep(10)
        else:
            print("[RADIO] ERROR: Could not connect to Chrome!")
            # Safety wait even when browser connection fails
            print("[RADIO] Waiting 10s before FFmpeg attempt...")
            time.sleep(10)

    except Exception as e:
        import traceback
        print(f"[RADIO] Go Live error: {e}")
        traceback.print_exc()
        # Safety wait on exception
        print("[RADIO] Waiting 10s before FFmpeg attempt...")
        time.sleep(10)

    return go_live_driver


async def main():
    """Run antifaFM broadcaster headless with PID-based instance locking."""
    logger.info("=" * 60)
    logger.info("antifaFM Broadcaster - Headless Mode")
    logger.info("=" * 60)

    # Instance lock management (WSP 84: Don't duplicate processes)
    lock = get_instance_lock("antifafm_broadcaster")

    # Check for duplicates
    duplicates = lock.check_duplicates()
    if duplicates:
        logger.warning(f"Found {len(duplicates)} duplicate antifaFM process(es): {duplicates}")
        print(f"[RADIO] Found {len(duplicates)} orphaned instance(s). Killing...")
        lock.kill_pids(duplicates)
        time.sleep(1)

    # Acquire lock
    if not lock.acquire():
        logger.error("Could not acquire instance lock - another instance is running")
        print("[RADIO] FATAL: Could not acquire instance lock")
        return 1

    logger.info(f"Instance lock acquired (PID: {os.getpid()})")

    # Debug switches for Occam's layering
    skip_browser = os.getenv("ANTIFAFM_SKIP_BROWSER", "0") == "1"
    skip_ffmpeg = os.getenv("ANTIFAFM_SKIP_FFMPEG", "0") == "1"
    wait_before_ffmpeg = int(os.getenv("ANTIFAFM_WAIT_BEFORE_FFMPEG", "10"))
    debug_verbose = os.getenv("ANTIFAFM_DEBUG_VERBOSE", "0") == "1"

    if debug_verbose:
        print(f"[DEBUG] skip_browser={skip_browser}, skip_ffmpeg={skip_ffmpeg}, wait={wait_before_ffmpeg}s")

    # Layer 1: OAuth preflight
    auto_reauth = os.getenv("ANTIFAFM_AUTO_REAUTH_YOUTUBE", "0") == "1"
    _preflight_antifafm_youtube_auth(auto_reauth=auto_reauth)

    # Layer 2: Browser automation (Go Live)
    if not skip_browser:
        await _prepare_youtube_live_endpoint()
    else:
        print(f"[DEBUG] ANTIFAFM_SKIP_BROWSER=1 - skipping browser automation")
        print(f"[DEBUG] Waiting {wait_before_ffmpeg}s before FFmpeg (manual Go Live expected)...")
        time.sleep(wait_before_ffmpeg)

    # Layer 3: FFmpeg streaming
    if skip_ffmpeg:
        print("[DEBUG] ANTIFAFM_SKIP_FFMPEG=1 - skipping FFmpeg")
        print("[DEBUG] Browser automation completed. Check YouTube Studio manually.")
        return 0

    broadcaster = AntifaFMBroadcaster()

    # Handle shutdown signals
    shutdown_event = asyncio.Event()

    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Start broadcasting
        success = await broadcaster.start()
        if not success:
            logger.error("Failed to start broadcaster")
            return 1

        logger.info("Broadcaster running. Press Ctrl+C to stop.")

        # Wait for shutdown signal
        await shutdown_event.wait()

    except Exception as e:
        logger.error(f"Broadcaster error: {e}")
        return 1
    finally:
        await broadcaster.stop()
        lock.release()
        logger.info("Broadcaster stopped. Instance lock released.")

    return 0


def run_antifafm_broadcaster():
    """
    Run antifaFM broadcaster interactively (blocking).

    Called from main menu for on-demand control.
    """
    print("\n[RADIO] antifaFM YouTube Live Broadcaster")
    print("=" * 50)

    # Ensure logs directory
    (PROJECT_ROOT / "logs").mkdir(exist_ok=True)

    exit_code = asyncio.run(main())
    return exit_code


async def _background_broadcaster_task():
    """Background task that runs the broadcaster."""
    global _background_broadcaster

    _background_broadcaster = AntifaFMBroadcaster()

    try:
        success = await _background_broadcaster.start()
        if not success:
            logger.error("[RADIO] Background broadcaster failed to start")
            return

        logger.info("[RADIO] Background broadcaster running")

        # Run until stopped
        while _background_broadcaster and _background_broadcaster.status.value == "broadcasting":
            await asyncio.sleep(5)

    except asyncio.CancelledError:
        logger.info("[RADIO] Background broadcaster cancelled")
    except Exception as e:
        logger.error(f"[RADIO] Background broadcaster error: {e}")
    finally:
        if _background_broadcaster:
            await _background_broadcaster.stop()


def start_antifafm_background() -> bool:
    """
    Start antifaFM broadcaster in background thread.

    Uses PID-based instance lock (same pattern as main.py monitor_youtube)
    to prevent multiple broadcaster instances.

    Returns:
        bool: True if started successfully
    """
    global _background_broadcaster, _background_task, _background_loop, _instance_lock

    if _background_broadcaster is not None:
        print("[RADIO] antifaFM already running in background")
        return True

    # OBS MODE: Skip browser automation entirely - OBS handles streaming directly
    obs_mode = os.getenv("ANTIFAFM_USE_OBS", "0") == "1"
    if obs_mode:
        print("[RADIO] ========================================")
        print("[RADIO] OBS MODE ENABLED (ANTIFAFM_USE_OBS=1)")
        print("[RADIO] - Skipping FFmpeg cleanup (OBS encodes)")
        print("[RADIO] - Skipping Edge automation (not needed)")
        print("[RADIO] - Only OBS WebSocket + Chat Agents run")
        print("[RADIO] ========================================")

    # Kill ALL existing FFmpeg processes for clean start (skip in OBS mode)
    import subprocess
    import time
    if not obs_mode:
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq ffmpeg.exe", "/FO", "CSV"],
                capture_output=True, text=True, timeout=5
            )
            if "ffmpeg.exe" in result.stdout:
                print("[RADIO] Found existing FFmpeg process(es) - killing for clean start...")
                subprocess.run(["taskkill", "/F", "/IM", "ffmpeg.exe"],
                             capture_output=True, timeout=10)
                time.sleep(2)  # Let processes fully terminate
                print("[RADIO] Old FFmpeg processes terminated")
            else:
                print("[RADIO] Health check: No orphaned FFmpeg processes found")
        except Exception as e:
            logger.debug(f"[RADIO] FFmpeg cleanup: {e}")

        # Kill Edge browser for clean start (antifaFM uses dedicated Edge on port 9223)
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq msedge.exe", "/FO", "CSV"],
                capture_output=True, text=True, timeout=5
            )
            if "msedge.exe" in result.stdout:
                print("[RADIO] Closing existing Edge browser for clean start...")
                subprocess.run(["taskkill", "/F", "/IM", "msedge.exe"],
                             capture_output=True, timeout=10)
                time.sleep(2)  # Let Edge fully terminate
                print("[RADIO] Edge closed - will launch fresh")
            else:
                print("[RADIO] Health check: No existing Edge browser")
        except Exception as e:
            logger.debug(f"[RADIO] Edge cleanup: {e}")

        auto_reauth = os.getenv("ANTIFAFM_AUTO_REAUTH_YOUTUBE", "0") == "1"
        _preflight_antifafm_youtube_auth(auto_reauth=auto_reauth)

    # Step 0: Set up YouTube Live stream via browser automation (returns None in OBS mode)
    _go_live_driver = asyncio.run(_prepare_youtube_live_endpoint())

    if False:  # Superseded by _prepare_youtube_live_endpoint()
        print("[RADIO] Setting up YouTube Live stream...")
        print("[RADIO] Step 1: Connecting to Edge...")
        try:
            from modules.platform_integration.antifafm_broadcaster.src.youtube_go_live import (
                click_go_live,
                verify_stream_connected,
                _connect_to_chrome,
            )

            # Connect to Chrome
            _go_live_driver = _connect_to_chrome()
            if _go_live_driver:
                print("[RADIO] Step 2: Chrome connected - clicking Create → Go Live...")

                # Always attempt Go Live - if already live, it just won't find the button
                loop = asyncio.new_event_loop()
                go_live_result = loop.run_until_complete(click_go_live(_go_live_driver))
                loop.close()

                print(f"[RADIO] Go Live result: {go_live_result}")

                if go_live_result.get("success"):
                    if go_live_result.get("already_live"):
                        print("[RADIO] Stream already active - ready for FFmpeg!")
                    else:
                        print(f"[RADIO] YouTube Live stream ACTIVATED!")
                        print(f"[RADIO] Stream URL: {go_live_result.get('url', 'N/A')}")

                    # CRITICAL: Wait for "Connect your encoder" before starting FFmpeg
                    # This ensures YouTube's RTMP endpoint is actually ready
                    print("[RADIO] Waiting for YouTube RTMP endpoint to be ready...")
                    endpoint_ready = False
                    for wait_attempt in range(10):  # Max 30 seconds
                        time.sleep(3)
                        try:
                            ready_check = _go_live_driver.execute_script("""
                                const bodyText = document.body.innerText.toLowerCase();
                                return {
                                    has_encoder: bodyText.includes('connect your encoder'),
                                    has_end_stream: bodyText.includes('end stream'),
                                    has_live: bodyText.includes('you\\'re live') || bodyText.includes('live now')
                                };
                            """)
                            print(f"[RADIO] Endpoint check {wait_attempt+1}/10: {ready_check}")

                            if ready_check.get('has_encoder') or ready_check.get('has_end_stream') or ready_check.get('has_live'):
                                endpoint_ready = True
                                print("[RADIO] YouTube RTMP endpoint is READY!")
                                break
                        except Exception as e:
                            print(f"[RADIO] Endpoint check error: {e}")

                    if not endpoint_ready:
                        print("[RADIO] WARNING: Could not confirm endpoint ready - FFmpeg may fail!")
                else:
                    print(f"[RADIO] WARNING: Go Live may have failed: {go_live_result.get('error')}")
                    if go_live_result.get('available'):
                        print(f"[RADIO] Available buttons found: {go_live_result.get('available')[:5]}")
            else:
                print("[RADIO] ERROR: Could not connect to Chrome!")

        except Exception as e:
            import traceback
            print(f"[RADIO] Go Live error: {e}")
            traceback.print_exc()

    # Ensure logs directory
    (PROJECT_ROOT / "logs").mkdir(exist_ok=True)

    # Instance lock management (WSP 84: Don't duplicate processes)
    _instance_lock = get_instance_lock("antifafm_broadcaster")

    # Check for duplicates
    duplicates = _instance_lock.check_duplicates()
    if duplicates:
        logger.warning(f"[RADIO] Found {len(duplicates)} duplicate antifaFM process(es): {duplicates}")
        print(f"[RADIO] Killing {len(duplicates)} orphaned antifaFM instance(s)...")
        _instance_lock.kill_pids(duplicates)
        time.sleep(1)  # Let processes die

    # Acquire lock
    if not _instance_lock.acquire():
        logger.error("[RADIO] Could not acquire instance lock - another instance is running")
        print("[RADIO] FATAL: Could not acquire instance lock")
        _instance_lock = None
        return False

    logger.info(f"[RADIO] Instance lock acquired (PID: {os.getpid()})")

    # OBS MODE: Skip FFmpeg broadcaster - only run OBS WebSocket + chat agents
    if obs_mode:
        print("[RADIO] OBS MODE: Skipping FFmpeg broadcaster (OBS handles encoding)")

        # Start OBS video orchestration (grid layout + song sync + news ticker + karaoke)
        _start_obs_orchestration()

        # Start chat agents immediately in OBS mode (no stream verification needed)
        if os.getenv("ANTIFAFM_CHAT_AGENTS", "1") == "1":
            print("[RADIO] OBS MODE: Starting chat agents...")
            _start_chat_agents()

        print("[RADIO] OBS MODE: antifaFM running (OBS WebSocket + Chat Agents)")
        return True

    # Non-OBS mode: Start FFmpeg broadcaster in background thread
    def run_in_thread():
        global _background_loop, _background_task
        _background_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_background_loop)
        _background_task = _background_loop.create_task(_background_broadcaster_task())
        try:
            _background_loop.run_until_complete(_background_task)
        except Exception as e:
            logger.error(f"[RADIO] Background thread error: {e}")
        finally:
            _background_loop.close()

    thread = threading.Thread(target=run_in_thread, daemon=True, name="antifafm-broadcaster")
    thread.start()

    # Start OBS video orchestration (grid layout + song sync + news ticker)
    _start_obs_orchestration()

    # Give FFmpeg time to start and connect
    time.sleep(5)

    if _background_broadcaster and _background_broadcaster.status.value == "broadcasting":
        print("[RADIO] FFmpeg started - verifying YouTube connection...")

        # Step 1: Verify stream is connected on YouTube Studio
        if _go_live_driver and os.getenv("ANTIFAFM_VERIFY_STREAM", "1") == "1":
            try:
                from modules.platform_integration.antifafm_broadcaster.src.youtube_go_live import verify_stream_connected

                # Run verification
                verify_loop = asyncio.new_event_loop()
                verify_result = verify_loop.run_until_complete(
                    verify_stream_connected(_go_live_driver, timeout=30)
                )
                verify_loop.close()

                if verify_result.get("verified"):
                    print("[RADIO] Stream VERIFIED on YouTube Studio!")
                    logger.info(f"[RADIO] Stream verified: {verify_result}")

                    # Update stream metadata with clickbait title and M2M description
                    if os.getenv("ANTIFAFM_AUTO_METADATA", "1") == "1":
                        try:
                            from modules.platform_integration.antifafm_broadcaster.src.youtube_broadcast_manager import (
                                YouTubeBroadcastManager, generate_clickbait_title, generate_m2m_description
                            )
                            manager = YouTubeBroadcastManager()
                            title = generate_clickbait_title()
                            description = generate_m2m_description()
                            meta_loop = asyncio.new_event_loop()
                            meta_result = meta_loop.run_until_complete(
                                manager.update_current_broadcast(title=title, description=description)
                            )
                            meta_loop.close()
                            if meta_result.get("success"):
                                print(f"[RADIO] Metadata updated: {title[:40]}...")
                            else:
                                print(f"[RADIO] Metadata update skipped: {meta_result.get('error')}")
                        except Exception as e:
                            print(f"[RADIO] Metadata update error: {e}")

                    # Start chat agents NOW - after stream is live (fixes PID violation)
                    if os.getenv("ANTIFAFM_CHAT_AGENTS", "1") == "1":
                        _start_chat_agents()
                else:
                    print(f"[RADIO] WARNING: Stream verification failed - {verify_result}")
                    logger.warning(f"[RADIO] Stream verification failed: {verify_result}")
            except Exception as e:
                print(f"[RADIO] Verification skipped: {e}")
                logger.warning(f"[RADIO] Verification error: {e}")
        else:
            print("[RADIO] Skipping verification (no driver or ANTIFAFM_VERIFY_STREAM=0)")

        print("[RADIO] antifaFM running in background")
        return True
    else:
        print("[RADIO] antifaFM background start pending...")
        return True  # May still be starting


def stop_antifafm_background() -> bool:
    """
    Stop background antifaFM broadcaster.

    Releases PID-based instance lock on shutdown.

    Returns:
        bool: True if stopped successfully
    """
    global _background_broadcaster, _background_task, _background_loop, _instance_lock

    if _background_broadcaster is None:
        print("[RADIO] antifaFM not running in background")
        return True

    try:
        if _background_loop and _background_task:
            _background_loop.call_soon_threadsafe(_background_task.cancel)

        # Give it time to stop
        import time
        time.sleep(2)

        _background_broadcaster = None
        _background_task = None
        _background_loop = None

        # Release instance lock
        if _instance_lock:
            _instance_lock.release()
            logger.info("[RADIO] Instance lock released")
            _instance_lock = None

        print("[RADIO] antifaFM background stopped")
        return True
    except Exception as e:
        logger.error(f"[RADIO] Error stopping background: {e}")
        return False


def start_antifafm_detached() -> bool:
    """
    Start antifaFM broadcaster as a DETACHED process that survives parent exit.

    This spawns a completely separate process that keeps running even after
    main.py exits. Use this instead of start_antifafm_background() when you
    want the stream to persist.

    Returns:
        bool: True if launched successfully
    """
    import subprocess

    # Check for existing FFmpeg streams first
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq ffmpeg.exe", "/FO", "CSV"],
            capture_output=True, text=True, timeout=5
        )
        if "ffmpeg.exe" in result.stdout:
            print("[RADIO] FFmpeg already running - stream may be active")
            return True
    except Exception:
        pass

    # Launch this script as a detached process
    script_path = Path(__file__).resolve()
    python_exe = sys.executable

    # Windows: CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS
    # This makes the process independent of the parent
    creation_flags = 0
    if sys.platform == "win32":
        creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS

    try:
        # Spawn detached process running this script directly
        process = subprocess.Popen(
            [python_exe, str(script_path)],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            creationflags=creation_flags,
            start_new_session=True if sys.platform != "win32" else False,
        )
        print(f"[RADIO] antifaFM launched as detached process (PID: {process.pid})")
        print("[RADIO] Stream will continue running after menu exit")
        return True
    except Exception as e:
        logger.error(f"[RADIO] Failed to launch detached process: {e}")
        print(f"[RADIO] ERROR: {e}")
        return False


def get_antifafm_status() -> dict:
    """Get current antifaFM broadcaster status."""
    global _background_broadcaster

    if _background_broadcaster is None:
        return {"running": False, "status": "stopped"}

    return {
        "running": True,
        **_background_broadcaster.get_status()
    }


def diagnose_antifafm() -> dict:
    """
    Diagnose antifaFM broadcaster configuration for troubleshooting.

    Run: python -c "from modules.platform_integration.antifafm_broadcaster.scripts.launch import diagnose_antifafm; print(diagnose_antifafm())"
    """
    import json

    results = {
        "stream_key_set": bool(os.getenv("ANTIFAFM_YOUTUBE_STREAM_KEY")),
        "stream_url": os.getenv("ANTIFAFM_STREAM_URL", "https://a12.asurahosting.com/listen/antifafm/radio.mp3"),
        "fx_enabled": os.getenv("ANTIFAFM_FX_ENABLED", "true").lower() in ("true", "1"),
        "visual_path": os.getenv("ANTIFAFM_DEFAULT_VISUAL", "modules/platform_integration/antifafm_broadcaster/assets/default_visual.png"),
        "ffmpeg_available": False,
        "visual_exists": False,
        "visual_effects_import": False,
        "youtube_token_set": _get_antifafm_youtube_token_set(),
        "youtube_oauth_checked": False,
        "youtube_oauth_healthy": False,
        "youtube_oauth_reauth_needed": False,
        "errors": [],
    }

    # Check FFmpeg
    try:
        import subprocess
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True, timeout=5)
        results["ffmpeg_available"] = True
    except Exception as e:
        results["errors"].append(f"FFmpeg: {e}")

    # Check visual
    from pathlib import Path
    visual = Path(results["visual_path"])
    results["visual_exists"] = visual.exists()
    if not visual.exists():
        results["errors"].append(f"Visual not found: {visual}")

    # Check visual effects module
    try:
        from modules.platform_integration.antifafm_broadcaster.src.visual_effects import VisualEffectsBuilder
        results["visual_effects_import"] = True
    except Exception as e:
        results["errors"].append(f"Visual effects import: {e}")

    # Check YouTube OAuth health for the antifaFM credential set
    try:
        oauth_result = _preflight_antifafm_youtube_auth(auto_reauth=False)
        results["youtube_oauth_checked"] = oauth_result.get("checked", False)
        results["youtube_oauth_healthy"] = bool(oauth_result.get("healthy")) and oauth_result.get("channel_match", True) is not False
        results["youtube_oauth_reauth_needed"] = oauth_result.get("reauth_needed", False)
        results["youtube_oauth_missing"] = oauth_result.get("missing", [])
        results["youtube_oauth_expired"] = oauth_result.get("expired", [])
        results["youtube_oauth_channel_id"] = oauth_result.get("channel_id")
        results["youtube_oauth_channel_title"] = oauth_result.get("channel_title")
        results["youtube_oauth_channel_match"] = oauth_result.get("channel_match")
        if oauth_result.get("reauth_needed"):
            results["errors"].append(
                f"YouTube OAuth needs re-auth for set {oauth_result.get('token_set')}"
            )
    except Exception as e:
        results["errors"].append(f"YouTube OAuth preflight: {e}")

    # Summary
    results["ready"] = (
        results["stream_key_set"] and
        results["ffmpeg_available"] and
        results["visual_exists"] and
        results["youtube_oauth_healthy"]
    )

    print("\n[DIAGNOSE] antifaFM Broadcaster Status:")
    print("=" * 50)
    print(f"  Stream Key Set: {'YES' if results['stream_key_set'] else 'NO (required)'}")
    print(f"  FFmpeg Available: {'YES' if results['ffmpeg_available'] else 'NO (required)'}")
    print(f"  Visual Exists: {'YES' if results['visual_exists'] else 'NO (will auto-create)'}")
    print(f"  Effects Enabled: {'YES' if results['fx_enabled'] else 'NO (Layer 1 mode)'}")
    print(f"  Effects Module: {'OK' if results['visual_effects_import'] else 'FAIL'}")
    oauth_status = "OK" if results["youtube_oauth_healthy"] else (
        "UNKNOWN" if not results["youtube_oauth_checked"] else "REAUTH NEEDED"
    )
    print(f"  YouTube OAuth: {oauth_status}")
    print(f"  READY: {'YES' if results['ready'] else 'NO'}")
    if results["errors"]:
        print(f"\n  Errors:")
        for err in results["errors"]:
            print(f"    - {err}")
    print("=" * 50)

    return results


def run_suno_sync_cli(playlist_id: str = None, max_songs: int = 0, headless: bool = True):
    """
    Suno Lyrics Sync - Hybrid Chrome Extension + Import Workflow.

    Since Suno's API requires authentication, this uses the installed
    Chrome extension to download LRC files, then imports them with deduplication.

    Workflow:
    1. Launch Chrome with suno-lyrics extension + 012's playlist
    2. User clicks extension button on each song to download LRCs
    3. Import LRCs to lyrics library with auto-deduplication

    Args:
        playlist_id: Suno playlist UUID (default: 012's FFCPLN playlist)
        max_songs: Not used in Chrome extension mode
        headless: Not used in Chrome extension mode

    Usage:
        python launch.py --suno-sync
    """
    import subprocess
    from pathlib import Path

    pid = playlist_id or "3adb1878-12f8-4c1c-a815-bde3d7d320ed"  # 012's playlist
    scripts_dir = Path(__file__).parent
    data_dir = scripts_dir.parent / "data"
    lrc_output_dir = data_dir / "lrc_downloads"
    lrc_output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("[SUNO-SYNC] Lyrics Extraction Workflow")
    print("=" * 60)
    print()
    print("This workflow uses the Chrome extension approach:")
    print()

    # Step 1: Launch Chrome with extension
    print("[STEP 1/3] Launching Chrome with suno-lyrics extension...")
    ext_installer = scripts_dir.parent.parent.parent / "infrastructure" / "cli" / "src" / "extension_installer.py"

    try:
        result = subprocess.run(
            ["python", str(ext_installer), "launch", "--name", "suno-lyrics",
             "--url", f"https://suno.com/playlist/{pid}"],
            capture_output=True, text=True, timeout=30
        )
        if "Starting Chrome" in result.stdout or result.returncode == 0:
            print("[OK] Chrome launched with extension")
        else:
            print(f"[WARN] {result.stderr or result.stdout}")
    except Exception as e:
        print(f"[ERROR] Could not launch Chrome: {e}")
        print("[FIX] Install extension first:")
        print(f"  python {ext_installer} install --repo https://github.com/zh30/get-suno-lyric --name suno-lyrics")
        return {"success": False, "error": str(e)}

    print()
    print("[STEP 2/3] Download LRCs using the extension...")
    print("=" * 60)
    print("In Chrome:")
    print("  1. Click on any song in the playlist")
    print("  2. Look for the LRC download button (added by extension)")
    print("  3. Click to download .lrc file")
    print("  4. Repeat for all songs you want")
    print()
    print(f"Default download folder: C:\\Users\\{os.getenv('USERNAME', 'user')}\\Downloads")
    print("=" * 60)
    print()
    input("Press ENTER when you've downloaded the LRC files...")

    # Step 3: Import downloaded LRCs
    print()
    print("[STEP 3/3] Importing LRCs with auto-deduplication...")

    # Check default download locations
    download_locations = [
        Path(os.path.expanduser("~/Downloads")),
        lrc_output_dir,
    ]

    lrc_files = []
    for loc in download_locations:
        if loc.exists():
            lrc_files.extend(list(loc.glob("*.lrc")))

    if not lrc_files:
        print("[WARN] No .lrc files found in Downloads folder")
        print(f"[TIP] Move .lrc files to: {lrc_output_dir}")
        return {"success": True, "downloaded": 0, "imported": 0}

    print(f"[FOUND] {len(lrc_files)} LRC files")

    # Import with deduplication
    try:
        sys.path.insert(0, str(scripts_dir))
        from ffcpln_lyrics_library import FFCPLNLyricsLibrary

        library = FFCPLNLyricsLibrary()
        stats = {"imported": 0, "duplicates": 0, "errors": 0}

        for lrc_path in lrc_files:
            try:
                result = library.import_lrc_file(str(lrc_path))
                if result.get("success"):
                    if result.get("duplicate"):
                        stats["duplicates"] += 1
                    else:
                        stats["imported"] += 1
                else:
                    stats["errors"] += 1
            except Exception as e:
                logger.debug(f"Import error for {lrc_path}: {e}")
                stats["errors"] += 1

        print()
        print("=" * 60)
        print("[SUNO-SYNC] COMPLETE")
        print("=" * 60)
        print(f"  LRC files found:    {len(lrc_files)}")
        print(f"  Imported:           {stats['imported']}")
        print(f"  Duplicates:         {stats['duplicates']}")
        print(f"  Errors:             {stats['errors']}")
        print()
        print("[READY] Lyrics available for karaoke mode")

        return {"success": True, **stats}

    except ImportError as e:
        print(f"[ERROR] Lyrics library not available: {e}")
        return {"success": False, "error": str(e)}
    except Exception as e:
        print(f"[ERROR] Import failed: {e}")
        return {"success": False, "error": str(e)}


def run_suno_stt_extract(
    playlist_id: str = None,
    max_songs: int = 0,
    model_size: str = "base",
    force: bool = False
) -> dict:
    """
    Suno STT Lyrics Extraction - FULLY AUTOMATED.

    Uses Speech-to-Text (faster-whisper) to transcribe lyrics directly from
    Suno audio files. No browser automation, no manual work needed.

    "Everything 012 does, 0102 should be able to do" - ZERO manual work.

    Pipeline:
        Suno CDN → Download MP3 → faster-whisper STT → Lyrics → Dedup → DB

    Args:
        playlist_id: Suno playlist UUID (default: 012's FFCPLN playlist)
        max_songs: Max songs to process (0 = all)
        model_size: Whisper model (tiny, base, small, medium, large-v3)
        force: Re-process already processed songs

    Returns:
        Statistics dict with processed/new_lyrics/duplicates/failed counts

    Usage:
        python launch.py --suno-stt                    # Extract all 238 songs
        python launch.py --suno-stt --max 5            # Test with 5 songs
        python launch.py --suno-stt --model small      # Higher accuracy
    """
    from pathlib import Path
    import sys

    scripts_dir = Path(__file__).parent
    sys.path.insert(0, str(scripts_dir))

    pid = playlist_id or "3adb1878-12f8-4c1c-a815-bde3d7d320ed"  # 012's playlist

    print("=" * 70)
    print("[SUNO-STT] Fully Automated Lyrics Extraction via Speech-to-Text")
    print("=" * 70)
    print()
    print("Pipeline: Suno CDN → Download → faster-whisper → Lyrics → Dedup")
    print(f"Playlist: {pid}")
    print(f"Model:    {model_size}")
    if max_songs > 0:
        print(f"Max:      {max_songs} songs")
    print()

    try:
        from suno_stt_lyrics_extractor import SunoSTTLyricsExtractor

        extractor = SunoSTTLyricsExtractor(
            model_size=model_size,
            device="cpu",
            skip_processed=not force
        )

        stats = extractor.extract_from_playlist(
            playlist_id=pid,
            max_songs=max_songs
        )

        print()
        print("=" * 70)
        print("[SUNO-STT] EXTRACTION COMPLETE")
        print("=" * 70)
        print(f"  Total songs:      {stats.get('total', 0)}")
        print(f"  Processed:        {stats.get('processed', 0)}")
        print(f"  New lyrics:       {stats.get('new_lyrics', 0)}")
        print(f"  Duplicates:       {stats.get('duplicates', 0)}")
        print(f"  Failed:           {stats.get('failed', 0)}")
        print(f"  Skipped:          {stats.get('skipped', 0)}")
        print()
        print(f"  Unique in DB:     {stats.get('unique_lyrics', 'N/A')}")
        print(f"  Total in DB:      {stats.get('total_songs', 'N/A')}")
        print(f"  Dedup ratio:      {stats.get('dedup_ratio', 0):.2f}x")
        print()
        print("[READY] Lyrics available for karaoke mode")

        return {"success": True, **stats}

    except ImportError as e:
        print(f"[ERROR] Missing dependency: {e}")
        print("[FIX] Install: pip install faster-whisper librosa")
        return {"success": False, "error": str(e)}
    except Exception as e:
        print(f"[ERROR] Extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def run_stt_to_karaoke_bridge(limit: int = 0) -> dict:
    """
    Bridge STT lyrics from ffcpln_lyrics.db to karaoke cache (lyrics_cache.db).

    This function takes plain text lyrics extracted by STT and converts them
    to timed lyrics format for karaoke display by estimating timing based
    on song duration.

    "Everything 012 does, 0102 should be able to do" - ZERO manual work.

    Args:
        limit: Max songs to import (0 = all)

    Returns:
        Statistics dict with imported/skipped/errors counts

    Usage:
        python launch.py --import-to-cache               # Import all STT lyrics
        python launch.py --import-to-cache --limit 50   # Import first 50
    """
    from pathlib import Path
    import sys

    scripts_dir = Path(__file__).parent
    sys.path.insert(0, str(scripts_dir))

    print("=" * 70)
    print("[KARAOKE-BRIDGE] STT Lyrics → Karaoke Cache Import")
    print("=" * 70)
    print()
    print("Pipeline: ffcpln_lyrics.db → Estimate Timing → lyrics_cache.db")
    if limit > 0:
        print(f"Limit:    {limit} songs")
    print()

    try:
        from suno_stt_lyrics_extractor import import_stt_to_karaoke_cache

        stats = import_stt_to_karaoke_cache(limit=limit)

        print()
        print("=" * 70)
        print("[KARAOKE-BRIDGE] IMPORT COMPLETE")
        print("=" * 70)
        print(f"  Imported:         {stats.get('imported', 0)}")
        print(f"  Skipped:          {stats.get('skipped', 0)}")
        print(f"  Errors:           {stats.get('errors', 0)}")
        print()
        print("[READY] Lyrics available in karaoke cache for live display")

        return {"success": True, **stats}

    except ImportError as e:
        print(f"[ERROR] Missing dependency: {e}")
        return {"success": False, "error": str(e)}
    except Exception as e:
        print(f"[ERROR] Import failed: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def print_cli_usage():
    """Print CLI usage for OpenClaw/IronClaw."""
    print("""
antifaFM Broadcaster CLI - For OpenClaw/IronClaw agents

Usage:
  python launch.py                          # Start broadcaster (foreground)
  python launch.py --start                  # Start in background
  python launch.py --stop                   # Stop background broadcaster
  python launch.py --status                 # Check broadcaster status
  python launch.py --diagnose               # Run diagnostics
  python launch.py --reauth-youtube         # Re-auth antifaFM YouTube token in Edge
  python launch.py --json                   # JSON output (for agents)
  python launch.py --layer1                 # Disable visual effects
  python launch.py --title "Title"          # Set stream title before start
  python launch.py --desc "Description"     # Set stream description

  # SUNO LYRICS AUTOMATION (Layer 7.5)
  python launch.py --suno-stt               # FULLY AUTOMATED STT extraction (RECOMMENDED)
  python launch.py --suno-stt --max 5       # Test with 5 songs
  python launch.py --suno-stt --model small # Higher accuracy
  python launch.py --import-to-cache        # Bridge STT lyrics to karaoke cache
  python launch.py --import-to-cache --import-limit 50  # Import first 50 songs
  python launch.py --suno-sync              # Chrome extension workflow (legacy)

Examples:
  # OpenClaw: Start broadcaster with custom title
  python launch.py --start --json --title "antifaFM Radio - Live Now"

  # IronClaw: Check status
  python launch.py --status --json
  # Output: {"running": true, "status": "broadcasting", "uptime": 3600}

  # Re-auth antifaFM OAuth set in Edge
  python launch.py --reauth-youtube

  # Sync 012's Suno lyrics (238 songs, automated)
  python launch.py --suno-sync
  # Output: Downloads LRCs, deduplicates, imports to karaoke cache

  # Stop broadcaster
  python launch.py --stop --json
  # Output: {"success": true, "stopped": true}

Output (--json mode):
  {"success": true, "status": "started", "pid": 12345}
  {"success": false, "error": "already_running"}
""")


def cli_status_check() -> dict:
    """Check broadcaster status for CLI."""
    global _background_broadcaster

    result = {
        "running": _background_broadcaster is not None,
        "status": "unknown"
    }

    if _background_broadcaster:
        try:
            status = _background_broadcaster.get_status()
            result["status"] = status.get("state", "unknown")
            result["uptime"] = status.get("uptime_seconds", 0)
            result["stream_health"] = status.get("stream_health", {})
        except Exception as e:
            result["error"] = str(e)
    else:
        # Check if process is running via lock file
        lock = get_instance_lock("antifafm_broadcaster")
        duplicates = lock.check_duplicates()
        if duplicates:
            result["running"] = True
            result["status"] = "running_external"
            result["pids"] = duplicates
        else:
            result["status"] = "stopped"

    return result


if __name__ == "__main__":
    import sys as _sys
    import json as _json

    # Ensure logs directory exists
    (PROJECT_ROOT / "logs").mkdir(exist_ok=True)

    # Parse CLI arguments
    args = _sys.argv[1:]
    json_output = "--json" in args
    do_start = "--start" in args
    do_stop = "--stop" in args
    do_status = "--status" in args
    do_diagnose = "--diagnose" in args
    do_reauth_youtube = "--reauth-youtube" in args
    do_suno_sync = "--suno-sync" in args
    do_suno_stt = "--suno-stt" in args
    do_import_to_cache = "--import-to-cache" in args

    # Parse title/description and suno options
    stream_title = None
    stream_desc = None
    suno_max = 0
    suno_playlist = None
    suno_model = "base"
    suno_force = "--force" in args
    suno_visible = "--visible" in args
    import_limit = 0
    for i, arg in enumerate(args):
        if arg == "--title" and i + 1 < len(args):
            stream_title = args[i + 1]
        elif arg == "--desc" and i + 1 < len(args):
            stream_desc = args[i + 1]
        elif arg == "--max" and i + 1 < len(args):
            suno_max = int(args[i + 1])
        elif arg == "--playlist" and i + 1 < len(args):
            suno_playlist = args[i + 1]
        elif arg == "--model" and i + 1 < len(args):
            suno_model = args[i + 1]
        elif arg == "--import-limit" and i + 1 < len(args):
            import_limit = int(args[i + 1])
        elif arg == "--help" or arg == "-h":
            print_cli_usage()
            _sys.exit(0)

    # Set stream title/description in environment for broadcaster to pick up
    if stream_title:
        os.environ["ANTIFAFM_STREAM_TITLE"] = stream_title
    if stream_desc:
        os.environ["ANTIFAFM_STREAM_DESC"] = stream_desc

    # Check for --suno-sync flag (Suno lyrics automation - Chrome extension workflow)
    if do_suno_sync:
        result = run_suno_sync_cli(playlist_id=suno_playlist)
        if json_output:
            print(_json.dumps(result))
        _sys.exit(0 if result.get("success", False) else 1)

    # Check for --suno-stt flag (FULLY AUTOMATED STT extraction - ZERO manual work)
    if do_suno_stt:
        result = run_suno_stt_extract(
            playlist_id=suno_playlist,
            max_songs=suno_max,
            model_size=suno_model,
            force=suno_force
        )
        if json_output:
            print(_json.dumps(result))
        _sys.exit(0 if result.get("success", False) else 1)

    # Check for --import-to-cache flag (Bridge STT lyrics to karaoke cache)
    if do_import_to_cache:
        result = run_stt_to_karaoke_bridge(limit=import_limit)
        if json_output:
            print(_json.dumps(result))
        _sys.exit(0 if result.get("success", False) else 1)

    # Check for --diagnose flag
    if do_diagnose:
        if json_output:
            result = diagnose_antifafm()
            print(_json.dumps(result))
        else:
            diagnose_antifafm()
        _sys.exit(0)

    if do_reauth_youtube:
        result = _force_reauth_antifafm_youtube_auth()
        if json_output:
            print(_json.dumps(result))
        if not (do_start or do_stop or do_status or do_diagnose):
            _sys.exit(0 if result.get("success") else 1)

    # Check for --status flag
    if do_status:
        result = cli_status_check()
        if json_output:
            print(_json.dumps(result))
        else:
            print(f"[STATUS] Running: {result.get('running')}")
            print(f"[STATUS] State: {result.get('status')}")
            if result.get('uptime'):
                print(f"[STATUS] Uptime: {result.get('uptime')}s")
        _sys.exit(0)

    # Check for --stop flag
    if do_stop:
        result = {"success": False}
        try:
            stopped = stop_antifafm_background()
            result["success"] = stopped
            result["stopped"] = stopped
        except Exception as e:
            result["error"] = str(e)

        if json_output:
            print(_json.dumps(result))
        else:
            if result.get("stopped"):
                print("[RADIO] Broadcaster stopped")
            else:
                print("[RADIO] Could not stop broadcaster (may not be running)")
        _sys.exit(0 if result.get("success") else 1)

    # Check for --start flag (background)
    if do_start:
        result = {"success": False}
        try:
            started = start_antifafm_background()
            result["success"] = started
            result["status"] = "started" if started else "failed"
            result["pid"] = os.getpid()
            if stream_title:
                result["title"] = stream_title
        except Exception as e:
            result["error"] = str(e)

        if json_output:
            print(_json.dumps(result))
        else:
            if result.get("success"):
                print(f"[RADIO] Broadcaster started (PID: {result.get('pid')})")
                if stream_title:
                    print(f"[RADIO] Stream title: {stream_title}")
            else:
                print(f"[RADIO] Failed to start: {result.get('error', 'unknown')}")
        _sys.exit(0 if result.get("success") else 1)

    # Check for --layer1 flag (disable effects)
    if "--layer1" in args:
        os.environ["ANTIFAFM_FX_ENABLED"] = "false"
        if not json_output:
            print("[LAYER] Running Layer 1 only (no visual effects)")

    # Default: run in foreground
    if json_output:
        # For foreground with JSON, output start status then run
        print(_json.dumps({"status": "starting", "mode": "foreground", "pid": os.getpid()}))

    exit_code = asyncio.run(main())
    _sys.exit(exit_code)
