"""
Tests for Mall Catalog Refresh Script Safety

Verifies dry-run default, --apply requirement, and backup behavior.
"""
import pytest
import copy
import importlib.util
import json
import os
import subprocess
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).parent.parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "refresh_mall_catalog.py"


@pytest.fixture
def script_content():
    """Load the refresh script."""
    return SCRIPT_PATH.read_text(encoding="utf-8")


class TestRefreshScriptSafety:
    """Refresh script defaults to dry-run for safety."""

    def test_script_exists(self):
        """Refresh script exists."""
        assert SCRIPT_PATH.exists()

    def test_dry_run_documented(self, script_content):
        """Dry-run behavior is documented in docstring."""
        assert "DRY-RUN" in script_content or "dry-run" in script_content

    def test_apply_flag_defined(self, script_content):
        """--apply flag is defined."""
        assert "--apply" in script_content

    def test_dry_run_default_true(self, script_content):
        """dry_run defaults to True (not args.apply)."""
        assert "dry_run = not args.apply" in script_content

    def test_save_catalog_accepts_dry_run(self, script_content):
        """save_catalog function accepts dry_run parameter."""
        assert "def save_catalog(catalog" in script_content
        assert "dry_run" in script_content

    def test_backup_created_on_write(self, script_content):
        """Backup is created before writing."""
        assert ".bak" in script_content or "backup" in script_content.lower()

    def test_dry_run_skips_write(self, script_content):
        """Dry-run mode skips file write."""
        assert "[DRY-RUN]" in script_content

    def test_refresh_catalog_accepts_dry_run(self, script_content):
        """refresh_catalog function accepts dry_run parameter."""
        assert "dry_run: bool = True" in script_content or "dry_run=True" in script_content


class TestRefreshScriptModes:
    """Refresh script supports multiple quota-efficient modes."""

    def test_info_only_mode(self, script_content):
        """--info-only mode exists."""
        assert "--info-only" in script_content

    def test_delta_mode(self, script_content):
        """--delta mode exists."""
        assert "--delta" in script_content

    def test_full_mode(self, script_content):
        """--full mode exists."""
        assert "--full" in script_content

    def test_quota_estimates_documented(self, script_content):
        """Quota estimates are documented."""
        assert "quota" in script_content.lower()
        assert "units" in script_content.lower()


@pytest.fixture
def page_exporter():
    spec = importlib.util.spec_from_file_location("mall_public_page_exporter", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def discovery_records(count=14, videos=13):
    return [{
        "foundup_id": f"lane_{record}",
        "canonical_foundup_id": "move2japan" if record == 0 else None,
        "title": f"Public source {record}",
        "description": "Reviewed public description",
        "one_sentence_pitch": "One public pitch",
        "hero_label": "Reviewed public hero label",
        "outcome": "Reviewed public outcome",
        "solution": "Reviewed public solution",
        "pain": "Reviewed public pain",
        "linkedin_url": "https://www.linkedin.com/company/public-source/",
        "creator_display": "012 public attribution",
        "topic_family": "life",
        "geo": "Not specified",
        "related_lanes": [],
        "display_order": record,
        "discovery_kind": "candidate" if record == 1 else "source",
        "public_plan_url": "https://github.com/FOUNDUPS/Foundups-Agent/blob/main/README.md",
        "lifecycle_stage": "incubating",
        "launch_readiness": "discoverable_only",
        "source_handle": "@public-source",
        "external_url": "https://www.youtube.com/@public-source",
        "tags": ["public"],
        "video_count": 9999,  # Provider totals are not approved page availability.
        "creator_id": "DO_NOT_PUBLISH_CREATOR",
        "data_namespace": "DO_NOT_PUBLISH_NAMESPACE",
        "entry_url": "https://private.example/DO_NOT_PUBLISH_ENTRY",
        "unknown_runtime": {"secret": "DO_NOT_PUBLISH_NESTED"},
        "videos": [{
            "video_id": f"{record * 100 + index:011d}",
            "title": f"Record {record} video {index}",
            "duration_seconds": 20,
            "embed_url": f"https://www.youtube.com/embed/{record * 100 + index:011d}",
            "source_url": f"https://www.youtube.com/watch?v={record * 100 + index:011d}",
            "unknown_private_field": "DO_NOT_PUBLISH_VIDEO",
        } for index in range(videos)],
    } for record in range(count)]


def follow_pages(exporter, assets, start):
    pages = []
    cursor = start
    while cursor:
        key = cursor.removeprefix(exporter.PUBLIC_DISCOVERY_PREFIX)
        assert key not in [item[0] for item in pages], "Paging must terminate without cycles"
        page = assets[key]
        assert len(page["items"]) <= 6
        pages.append((key, page))
        cursor = page["next"]
    return [page for _, page in pages]


class TestPublicDiscoveryPages:
    def test_metadata_is_bounded_and_cannot_publish_runtime_or_nested_video_data(self, page_exporter):
        source = discovery_records()
        before = copy.deepcopy(source)
        assets = page_exporter.build_public_discovery_pages(source)
        first = assets["catalog.json"]
        assert first["kind"] == "catalog" and first["record_id"] is None
        assert first["page"] == 0 and first["total"] == 14
        assert [row["foundup_id"] for row in first["items"]] == [f"lane_{i}" for i in range(6)]
        assert not any("videos" in row for row in first["items"])
        assert "DO_NOT_PUBLISH" not in json.dumps(assets)
        assert source == before, "Pure projection must not mutate the approved source"
        candidate = first["items"][1]
        assert candidate["canonical_foundup_id"] is None
        assert candidate["discovery_kind"] == "candidate"
        assert candidate["one_sentence_pitch"] == source[1]["one_sentence_pitch"]
        assert candidate["public_plan_url"] == source[1]["public_plan_url"]
        assert candidate["lifecycle_stage"] == "incubating"
        assert candidate["launch_readiness"] == "discoverable_only"
        for field in ["outcome", "solution", "pain", "linkedin_url", "creator_display", "hero_label",
                      "source_handle", "topic_family", "geo", "tags", "related_lanes", "display_order"]:
            assert candidate[field] == source[1][field]
        assert candidate["video_count"] == 13
        assert candidate["available_orders"] == ["catalog"]

    def test_selected_record_pages_preserve_identity_order_and_all_items_once(self, page_exporter):
        source = discovery_records()
        assets = page_exporter.build_public_discovery_pages(source)
        catalog_pages = follow_pages(page_exporter, assets, "/member/discovery/catalog.json")
        assert [len(page["items"]) for page in catalog_pages] == [6, 6, 2]
        records = [row for page in catalog_pages for row in page["items"]]
        assert [row["foundup_id"] for row in records] == [row["foundup_id"] for row in source]
        selected = records[7]
        video_pages = follow_pages(page_exporter, assets, selected["video_pages"]["catalog"])
        assert [len(page["items"]) for page in video_pages] == [6, 6, 1]
        assert all(page["kind"] == "videos" and page["record_id"] == "lane_7"
                   and page["order"] == "catalog" and page["available_orders"] == ["catalog"]
                   and page["generation"] == assets["catalog.json"]["generation"] for page in video_pages)
        assert [row["video_id"] for page in video_pages for row in page["items"]] == [
            row["video_id"] for row in source[7]["videos"]
        ]
        assert all("Record 7 video" in row["title"] for page in video_pages for row in page["items"])
        assert video_pages[-1]["next"] is None

    def test_generation_is_deterministic_and_changes_only_with_public_content(self, page_exporter):
        source = discovery_records(2, 2)
        original = page_exporter.build_public_discovery_pages(source)
        reordered_keys = [{key: row[key] for key in reversed(row)} for row in source]
        assert page_exporter.build_public_discovery_pages(reordered_keys) == original
        private_change = copy.deepcopy(source)
        private_change[0]["creator_id"] = "different private identity"
        assert page_exporter.build_public_discovery_pages(private_change) == original
        public_change = copy.deepcopy(source)
        public_change[0]["videos"][0]["title"] = "New approved title"
        changed = page_exporter.build_public_discovery_pages(public_change)
        old_generation = original["catalog.json"]["generation"]
        new_generation = changed["catalog.json"]["generation"]
        assert len(old_generation) == 64 and old_generation != new_generation
        assert all(new_generation in key for key in changed if key != "catalog.json")

    def test_empty_sources_and_records_have_no_phantom_video_page(self, page_exporter):
        empty = page_exporter.build_public_discovery_pages([])
        assert len(empty) == 1 and empty["catalog.json"]["items"] == []
        assert empty["catalog.json"]["next"] is None
        assets = page_exporter.build_public_discovery_pages(discovery_records(1, 0))
        row = assets["catalog.json"]["items"][0]
        assert row["video_count"] == 0 and row["video_pages"] == {"catalog": None}
        assert len(assets) == 1

    @pytest.mark.parametrize("identifier", ["../escape", "", "__proto__", "constructor", "a/b"])
    def test_invalid_record_identity_fails_before_any_export(self, page_exporter, identifier):
        records = discovery_records(1, 1)
        records[0]["foundup_id"] = identifier
        with pytest.raises(ValueError):
            page_exporter.build_public_discovery_pages(records)

    def test_duplicate_identities_and_credential_bearing_links_fail_closed(self, page_exporter):
        records = discovery_records(2, 1)
        records[1]["foundup_id"] = records[0]["foundup_id"]
        with pytest.raises(ValueError, match="Duplicate public discovery"):
            page_exporter.build_public_discovery_pages(records)
        records = discovery_records(1, 1)
        records[0]["videos"] *= 2
        with pytest.raises(ValueError, match="Duplicate video"):
            page_exporter.build_public_discovery_pages(records)
        records = discovery_records(1, 1)
        records[0]["external_url"] = "https://public.example/?access_token=DO_NOT_PUBLISH"
        with pytest.raises(ValueError, match="Credential-bearing"):
            page_exporter.build_public_discovery_pages(records)

    def test_record_paths_cannot_collide_on_case_insensitive_hosts(self, page_exporter):
        records = discovery_records(2, 1)
        records[1]["foundup_id"] = records[0]["foundup_id"].upper()
        with pytest.raises(ValueError, match="Duplicate public discovery"):
            page_exporter.build_public_discovery_pages(records)

    @pytest.mark.parametrize("url", ["https:relative", "https:///nohost"])
    def test_https_links_need_an_actual_hostname(self, page_exporter, url):
        records = discovery_records(1, 1)
        records[0]["external_url"] = url
        with pytest.raises(ValueError):
            page_exporter.build_public_discovery_pages(records)

    def test_generated_root_cannot_redirect_to_another_owned_directory(self, page_exporter, tmp_path):
        root = tmp_path / "public/member/discovery"
        destination = tmp_path / "scripts"
        root.parent.mkdir(parents=True)
        destination.mkdir()
        try:
            root.symlink_to(destination, target_is_directory=True)
        except OSError:
            if os.name != "nt":
                pytest.skip("Directory symlinks unavailable")
            result = subprocess.run(["cmd.exe", "/c", "mklink", "/J", str(root), str(destination)],
                                    capture_output=True, timeout=10)
            if result.returncode:
                pytest.skip("Directory symlinks/junctions unavailable")
        assets = page_exporter.build_public_discovery_pages(discovery_records(1, 1))
        with pytest.raises(ValueError, match="must not be redirected"):
            page_exporter.write_public_discovery_pages(assets, tmp_path, dry_run=False)
        assert list(destination.iterdir()) == []

    def test_redirected_path_resolution_is_rejected_without_link_privileges(self, page_exporter, tmp_path, monkeypatch):
        root = tmp_path / "public/member/discovery"
        destination = tmp_path / "scripts"
        destination.mkdir()
        resolve = Path.resolve

        def redirected(path, *args, **kwargs):
            if path == root:
                return destination
            return resolve(path, *args, **kwargs)

        # Exercise an OS-reported redirection even on hosts that forbid creating
        # symlinks/junctions. The separate test above qualifies real link behavior.
        monkeypatch.setattr(Path, "resolve", redirected)
        assets = page_exporter.build_public_discovery_pages(discovery_records(1, 1))
        with pytest.raises(ValueError, match="must not be redirected"):
            page_exporter.write_public_discovery_pages(assets, tmp_path, dry_run=False)
        assert list(destination.iterdir()) == []

    def test_writer_is_confined_dry_by_default_and_preserves_other_generations(self, page_exporter, tmp_path):
        assets = page_exporter.build_public_discovery_pages(discovery_records(1, 7))
        root = tmp_path / "public/member/discovery"
        assert page_exporter.write_public_discovery_pages(assets, tmp_path) == len(assets)
        assert not root.exists()
        invalid = {**assets, "../outside.json": {"items": []}}
        with pytest.raises(ValueError, match="Invalid generated"):
            page_exporter.write_public_discovery_pages(invalid, tmp_path, dry_run=False)
        assert not root.exists(), "Validate every output before writing any file"
        retained = root / "old-generation-marker.json"
        retained.parent.mkdir(parents=True)
        retained.write_text("retained", encoding="utf-8")
        page_exporter.write_public_discovery_pages(assets, tmp_path, dry_run=False)
        assert retained.read_text(encoding="utf-8") == "retained"
        assert not (tmp_path / "public/member/mall-video-catalog.json").exists()
        for relative, expected in assets.items():
            assert json.loads((root / relative).read_text(encoding="utf-8")) == expected

    def test_offline_cli_never_imports_youtube_or_changes_source_catalog(self, tmp_path):
        harness = r'''
import importlib.abc, importlib.util, json, pathlib, sys
class NoNetworkImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(('google', 'modules.communication', 'modules.platform_integration')):
            raise AssertionError('Offline exporter imported a network/auth owner')
sys.meta_path.insert(0, NoNetworkImports())
spec = importlib.util.spec_from_file_location('offline_pages', sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.REPO_ROOT = pathlib.Path(sys.argv[2])
module.CATALOG_PATH = module.REPO_ROOT / 'source.json'
module.load_catalog = lambda: json.loads(module.CATALOG_PATH.read_text(encoding='utf-8'))
module.CATALOG_PATH.write_text('[]', encoding='utf-8')
sys.argv = ['refresh_mall_catalog.py', '--public-pages-only']
module.main()
assert module.CATALOG_PATH.read_text(encoding='utf-8') == '[]'
assert not (module.REPO_ROOT / 'public').exists()
sys.argv = ['refresh_mall_catalog.py', '--public-pages-only', '--apply']
module.main()
assert module.CATALOG_PATH.read_text(encoding='utf-8') == '[]'
output = module.REPO_ROOT / 'public/member/discovery/catalog.json'
assert json.loads(output.read_text(encoding='utf-8'))['items'] == []
sys.argv = ['refresh_mall_catalog.py', '--public-pages-only', '--scoped-only', '--apply']
try:
    module.main()
except SystemExit as error:
    assert error.code == 2
else:
    raise AssertionError('Conflicting refresh mode was accepted')
'''
        result = subprocess.run([sys.executable, "-B", "-c", harness, str(SCRIPT_PATH), str(tmp_path)],
                                capture_output=True, text=True, timeout=15)
        assert result.returncode == 0, result.stderr
