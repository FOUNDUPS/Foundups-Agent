"""Offline documentation-contract checks; never import live LinkedIn executors."""

from pathlib import Path
import re
import unittest


MODULE = Path(__file__).resolve().parents[1]
ROOT = MODULE.parents[2]
CHILDREN = (
    "linkedin_inbox", "linkedin_connections", "linkedin_notifications",
    "linkedin_group_moderation", "openclaw_group_news", "linkedin_agentic_reply",
    "linkedin_newsletters", "linkedin_foundups_newsletter",
    "linkedin_roc_newsletter", "linkedin_jhr_newsletter", "linkedin_publishing",
    "linkedin_article_targeting", "linkedin_outreach", "linkedin_continuity",
)


class ActivitySkillContracts(unittest.TestCase):
    def text(self, relative):
        return (MODULE / relative).read_text(encoding="utf-8-sig")

    def test_existing_master_owns_routes(self):
        master = self.text("skillz/linkedin_engagement/SKILLz.md")
        self.assertIn("LINKEDIN_ACTIVITY_ROUTING.md", master)
        self.assertIn("instruction-level routing", master)
        route = self.text("docs/LINKEDIN_ACTIVITY_ROUTING.md")
        for name in CHILDREN:
            with self.subTest(child=name):
                self.assertIn(f"../skillz/{name}/SKILLz.md", route)
                child = self.text(f"skillz/{name}/SKILLz.md")
                self.assertTrue(child.startswith("---\n"))
                self.assertIn(f"name: {name}\n", child)
                self.assertIn("promotion_state: prototype", child)

    def test_local_markdown_links_resolve(self):
        paths = [MODULE / "docs/LINKEDIN_ACTIVITY_ROUTING.md",
                 MODULE / "docs/LINKEDIN_REVIEW_WORKFLOW.md"]
        paths += list((MODULE / "skillz/linkedin_newsletters/references").glob("*.md"))
        paths += [MODULE / "docs/audits/LINKEDIN_EDITORIAL_TREE_20260922.md"]
        paths += [MODULE / f"skillz/{name}/SKILLz.md"
                  for name in (*CHILDREN, "linkedin_engagement")]
        paths += [ROOT / relative for relative in (
            "modules/infrastructure/browser_actions/skillz/linkedin_post_hunter/SKILLz.md",
            "modules/infrastructure/browser_actions/skillz/linkedin_engagement_poster/SKILLz.md",
            "modules/ai_intelligence/ai_overseer/skillz/linkedin_company_poster/SKILLz.md",
        )]
        for path in paths:
            for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
                if "://" in target or target.startswith("#"):
                    continue
                with self.subTest(path=str(path), target=target):
                    resolved = (path.parent / target.split("#")[0]).resolve()
                    self.assertTrue(resolved.is_relative_to(ROOT.resolve()))
                    self.assertTrue(resolved.is_file())

    def test_narrow_scope_and_priority_do_not_grant_authority(self):
        route = self.text("docs/LINKEDIN_ACTIVITY_ROUTING.md")
        self.assertIn("A narrow command never silently expands", route)
        self.assertIn("Neither score grants permission", route)
        self.assertIn("Deferability", route)
        self.assertIn("Already approved", route)

    def test_inbox_rechecks_composer_and_uncertain_sends(self):
        inbox = self.text("skillz/linkedin_inbox/SKILLz.md")
        for term in ("Focused", "Other", "unread", "composer", "Hold",
                     "read back first", "unknown", "never blindly retry"):
            self.assertIn(term, inbox)

    def test_membership_not_implied_by_message(self):
        group = self.text("skillz/linkedin_group_moderation/SKILLz.md")
        self.assertIn("Leave the application pending", group)
        self.assertIn("hold a repetitive introduction", group)
        self.assertIn("never automatically accepts", group)
        news = self.text("skillz/openclaw_group_news/SKILLz.md")
        self.assertIn("never starts a scheduler", news)

    def test_all_three_newsletter_lanes_and_verified_states(self):
        news = self.text("skillz/linkedin_newsletters/SKILLz.md")
        routes = {
            "linkedin_foundups_newsletter": ("Eat the Startup", "BoundUps", "Foundups-Agent"),
            "linkedin_roc_newsletter": ("Return on Compute", "PR #202", "BLOCKED_IDENTITY"),
            "linkedin_jhr_newsletter": ("Japan Hyperscaler Report", "NO_REPORT", "7505133867079536640"),
        }
        for skill, terms in routes.items():
            self.assertIn(f"../{skill}/SKILLz.md", news)
            lane = self.text(f"skillz/{skill}/SKILLz.md")
            for term in terms:
                with self.subTest(skill=skill, term=term):
                    self.assertIn(term, lane)
        for term in ("VERIFIED_LIVE", "SCHEDULED_VERIFIED", "draft exists"):
            self.assertIn(term, news)

    def test_continuity_privacy_and_safe_pr_closure(self):
        text = self.text("skillz/linkedin_continuity/SKILLz.md")
        for term in ("private", "next action/owner", "Do not bypass failed checks",
                     "clean local tree", "no-change", "never"):
            # Instructions use imperative capitalization in some clauses.
            self.assertIn(term.lower(), text.lower())


if __name__ == "__main__":
    unittest.main()
