from pathlib import Path
import json


ESINGULARITY = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL = ESINGULARITY / "skillz" / "yumori_contact_ledger" / "SKILLz.md"
CITY = ESINGULARITY / "skillz" / "fukui_city_procedure" / "SKILLz.md"
REGISTRY = REPO_ROOT / "modules" / "infrastructure" / "wre_core" / "skillz" / "skills_registry_v2.json"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_proxy_voice_contract_is_explicit():
    text = _text(SKILL)
    assert "Canonical 0102 proxy voice" in text
    assert "third person" in text
    assert "do not open with" in text
    assert "0102です" in text
    assert "Default sign-off" in text


def test_monk_actions_are_not_written_as_0102_actions():
    text = _text(SKILL)
    assert "Never imply that 0102 personally performed a field action completed by the monk." in text
    assert "月曜日には、この僧がPPPによる再利用提案を正式に提出する予定です。" in text


def test_recursive_learning_is_required_for_meaningful_failures():
    text = _text(SKILL)
    assert "Recursive self-improvement" in text
    assert "RED DOG CANDIDATE" in text
    assert "Routine successful runs do not create learning entries." in text


def test_city_procedure_delegates_correspondence_contract():
    text = _text(CITY)
    assert "yumori_contact_ledger/SKILLz.md" in text
    assert "canonical 0102 proxy voice" in text
    assert "third-person monk reference" in text


def test_registry_points_to_canonical_parent():
    registry = json.loads(_text(REGISTRY))
    item = registry["skills"]["yumori_contact_ledger"]
    assert item["location"] == "modules/foundups/esingularity/skillz/yumori_contact_ledger"
    assert item["primary_agent"] == "0102"
    assert item["version"] == "0.6.0"
