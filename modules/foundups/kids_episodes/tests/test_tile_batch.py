"""Planning/record structure only; no live runtime or media quality proof."""
import copy
import unittest
from modules.foundups.kids_episodes.src.tile_batch import (
    CHECKS, CONTRACT, prepare_tile_batch, check_review_record,
)


def plan(**overrides):
    return prepare_tile_batch(**(dict(batch_id="next-set", brief_sha256="a"*64,
                                     tile_ids=[f"tile-{i}" for i in range(5)]) | overrides))


def review():
    return dict(artifact_sha256="b"*64, reviewer_id="verifier", contract=CONTRACT,
                checks={key: dict(grade=4, observed=True, evidence="fixture:observed-output")
                        for key in CHECKS})


def check(record, **overrides):
    return check_review_record(**(dict(author_id="author", reviewer_id="verifier",
                                      artifact_sha256="b"*64, record=record) | overrides))


class TileBatchTests(unittest.TestCase):
    def test_order_and_binding(self):
        result = plan()
        self.assertEqual(result, plan())
        self.assertEqual(result["status"], "PLANNED_NOT_ADMITTED")
        self.assertFalse(result["runtime_activation"])
        self.assertEqual(len(result["tickets"]), 11)
        self.assertEqual(result["tickets"][2]["depends_on"], ["tile-0:review"])
        self.assertEqual(result["tickets"][-1]["depends_on"],
                         [f"tile-{i}:review" for i in range(5)])
        self.assertNotEqual(plan(brief_sha256="b"*64)["plan_sha256"], result["plan_sha256"])
        self.assertNotEqual(plan(max_repairs=1)["plan_sha256"], result["plan_sha256"])

    def test_invalid_batch(self):
        for change in [dict(tile_ids=["x"]*5), dict(tile_ids=["x"]*4),
                       dict(tile_ids=["x"]*6), dict(tile_ids="abcde"),
                       dict(batch_id="../x"), dict(brief_sha256="approval"),
                       dict(max_repairs=True), dict(max_repairs=4)]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                plan(**change)

    def test_complete_and_binding(self):
        self.assertEqual(check(review()), [])  # Completeness, not authentication.
        self.assertEqual(check(review(), author_id="verifier"), ["independent_output_review"])
        self.assertEqual(check(review(), artifact_sha256="c"*64), ["artifact_binding"])
        self.assertEqual(check(review() | {"reviewer_id": "other"}), ["review_binding"])
        self.assertEqual(check(review() | {"contract": "old"}), ["review_binding"])

    def test_every_criterion_blocks_individually(self):
        for criterion in CHECKS:
            for bad in [None, dict(grade=3, observed=True, evidence="frame"),
                        dict(grade=5, observed=False, evidence="not tested"),
                        dict(grade=5, observed=True, evidence=""),
                        dict(grade=True, observed=True, evidence="frame")]:
                with self.subTest(criterion=criterion, bad=bad):
                    record = copy.deepcopy(review())
                    record["checks"][criterion] = bad
                    self.assertEqual(check(record), [criterion])


if __name__ == "__main__":
    unittest.main()
