from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "site"


class StaticContractTests(unittest.TestCase):
    def test_seven_frames_and_controls(self) -> None:
        html = (DIST / "index.html").read_text(encoding="utf-8")
        self.assertEqual(7, len(re.findall(r'class="frame frame--\d\d', html)))
        self.assertEqual(7, len(re.findall(r'class="chapter(?: is-active)?"', html)))

    def test_seven_chapter_records(self) -> None:
        js = (DIST / "app.js").read_text(encoding="utf-8")
        self.assertEqual(7, len(re.findall(r'\n  \{\n    era:', js)))

    def test_public_docs_do_not_expose_drive_links(self) -> None:
        for path in ROOT.glob("*.md"):
            self.assertNotIn("docs.google.com", path.read_text(encoding="utf-8"), path.name)

    def test_asset_contract_is_private(self) -> None:
        assets = DIST / "assets"
        self.assertTrue((assets / "README.md").is_file())
        self.assertFalse(any(assets.glob("frame-*.png")))


if __name__ == "__main__":
    unittest.main()
