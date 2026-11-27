"""Offline discovery contracts, not account actions or runtime admission."""
from pathlib import Path
import runpy

from modules.infrastructure.wre_core.skillz.wre_skills_loader import WRESkillsLoader
from modules.infrastructure.wre_core.skillz.wre_skills_discovery import WRESkillsDiscovery

ROOT = Path(__file__).resolve().parents[4]
CANONICAL = Path("modules/communication/moltbot_bridge/skillz/reddog_adsense/SKILLz.md")


def test_registry_resolves_and_loads_single_canonical_prototype():
    loader = WRESkillsLoader(repo_root=ROOT)
    assert "reddog_adsense" in loader.list_skills(agent_type="0102", promotion_state="prototype")
    assert "reddog_adsense" not in loader.list_skills(promotion_state="production")
    assert loader.resolve_skill_file("reddog_adsense") == ROOT / CANONICAL
    assert loader.load_skill("reddog_adsense", "0102", inject_context=False) == (ROOT / CANONICAL).read_bytes().decode("utf-8")
    assert not (ROOT / CANONICAL.parent / "executor.py").exists()
    registry = loader.registry
    assert registry["total_skills"] == len(registry["skills"])
    assert sum(v["location"] == CANONICAL.parent.as_posix() for v in registry["skills"].values()) == 1


def test_filesystem_discovery_reaches_canonical_not_thin_projections():
    hits = [s for s in WRESkillsDiscovery(ROOT).discover_all_skills() if s.skill_name == "reddog_adsense"]
    assert len(hits) == 1
    assert hits[0].skill_path == ROOT / CANONICAL
    assert hits[0].metadata["promotion_state"] == "prototype"
    # The scanner's inferred location label is not registry admission authority.


def test_navigation_and_host_entrypoints_resolve_same_owner():
    nav = runpy.run_path(str(ROOT / "NAVIGATION.py"))["NEED_TO"]
    routes = [p for q, p in nav.items() if "adsense" in q.lower()]
    assert routes and set(routes) == {CANONICAL.as_posix()}
    source = ROOT / ".claude/skills/reddog-adsense/SKILL.md"
    target = ROOT / ".agents/skills/reddog-adsense/SKILL.md"
    assert source.read_bytes() == target.read_bytes()
    assert CANONICAL.as_posix() in source.read_text(encoding="utf-8")
