"""Offline evidence for the API publication boundary; no application bootstrap.

Load the actual three owned leaves with inert package parents, use injected fake
clients, and keep all SQLite effects inside each test's disposable directory.
Run this file directly; do not discover the mixed live integration directory.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
import importlib.util
from pathlib import Path
import sqlite3
import sys
from tempfile import TemporaryDirectory
import threading
import types
import unittest
from unittest.mock import patch


_ROOT = Path(__file__).resolve().parents[4]
_SOCIAL = "modules.platform_integration.social_media_orchestrator"
_X = "modules.platform_integration.x_twitter"
_CONTENT = "Listen to AntifaFM: https://antifafm.com/"
_USER_ID, _POST_ID = "1001", "9001"


def _load_leaves():
    modules = {}
    for name in ("modules", "modules.platform_integration", _SOCIAL,
                 _SOCIAL + ".src", _SOCIAL + ".src.core", _X, _X + ".src"):
        package = types.ModuleType(name)
        package.__path__ = []
        modules[name] = package
    for name in (_SOCIAL + ".src.core.publication_store",
                 _X + ".src.verified_x_publisher",
                 _SOCIAL + ".src.unified_x_interface"):
        path = _ROOT / (name.replace(".", "/") + ".py")
        spec = importlib.util.spec_from_file_location(name, path)
        leaf = importlib.util.module_from_spec(spec)
        modules[name] = leaf
        with patch.dict(sys.modules, modules):
            spec.loader.exec_module(leaf)
    return modules


_LEAVES = {}
_INTERFACE = _STORE = _PUBLISHER = None


class FakeXClient:
    def __init__(self):
        self.user_id = _USER_ID
        self.post_id = _POST_ID
        self.text = _CONTENT
        self.author_id = _USER_ID
        self.entities = {}
        self.created = []
        self.reads = []
        self.identities = []
        self.create_error = None
        self.read_error = None
        self.barrier = None

    def get_me(self, *, user_auth):
        self.identities.append(user_auth)
        if self.barrier:
            self.barrier.wait(timeout=5)
        return types.SimpleNamespace(data={"id": self.user_id}, errors=None)

    def create_tweet(self, *, text, user_auth):
        self.created.append((text, user_auth))
        if self.create_error:
            raise self.create_error
        return {"data": {"id": self.post_id}}

    def get_tweet(self, *, id, tweet_fields, user_auth):
        self.reads.append((id, tweet_fields, user_auth))
        if self.read_error:
            raise self.read_error
        return {"data": {"id": self.post_id, "author_id": self.author_id,
                         "text": self.text, "entities": self.entities}}


class TestVerifiedXPublication(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global _LEAVES, _INTERFACE, _STORE, _PUBLISHER
        _LEAVES = _load_leaves()
        _INTERFACE = _LEAVES[_SOCIAL + ".src.unified_x_interface"]
        _STORE = _LEAVES[_SOCIAL + ".src.core.publication_store"]
        _PUBLISHER = _LEAVES[_X + ".src.verified_x_publisher"]

    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.directory = Path(self.stack.enter_context(TemporaryDirectory()))
        self.db = self.directory / "receipts.sqlite3"
        self.stack.enter_context(patch.dict(sys.modules, _LEAVES))
        self.client = FakeXClient()

    def call(self, **changes):
        args = dict(content=_CONTENT, account=_INTERFACE.XAccount.FOUNDUPS,
                    campaign_id="antifafm_station", job_id="day_1",
                    client=self.client, expected_user_id=_USER_ID,
                    db_path=self.db, dry_run=False)
        args.update(changes)

        async def bounded_publication():
            task = asyncio.create_task(_INTERFACE.UnifiedXInterface().post_verified_x(**args))
            # A periodic timer also services worker completions on hosted runtimes
            # whose selector does not wake reliably for thread-safe callbacks.
            for _ in range(1000):
                if task.done():
                    return task.result()
                await asyncio.sleep(0.01)
            task.cancel()
            raise AssertionError("Fake publication did not complete in 10 seconds")

        return asyncio.run(bounded_publication())

    def test_dry_run_has_no_client_or_file_effects(self):
        with patch("builtins.open", side_effect=AssertionError("file access")), \
             patch.object(_STORE.sqlite3, "connect", side_effect=AssertionError("database")), \
             patch.object(_INTERFACE.os, "makedirs", side_effect=AssertionError("mkdir")):
            result = self.call(dry_run=True)
        self.assertEqual(result["status"], "dry_run")
        self.assertTrue(result["success"])
        self.assertIsNone(result["provider_user_id"])
        self.assertEqual(self.client.identities, [])
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_invalid_admission_never_contacts_client(self):
        for override in ({"account": "foundups"}, {"expected_user_id": "simulated"},
                         {"expected_user_id": "０１"}, {"expected_user_id": "0"},
                         {"content": ""}, {"content": "x" * 281},
                         {"job_id": ""}, {"dry_run": "false"}):
            with self.subTest(override=override):
                self.assertEqual(self.call(**override)["status"], "rejected")
        self.assertEqual(self.client.identities, [])
        self.assertFalse(self.db.exists())

    def test_account_mismatch_prevents_claim_and_post(self):
        self.client.user_id = "2002"
        result = self.call()
        self.assertEqual(result["error"], "account_mismatch")
        self.assertEqual(result["provider_user_id"], "2002")
        self.assertEqual(self.client.created, [])
        self.assertFalse(self.db.exists())

    def test_verified_receipt_and_restart_duplicate(self):
        result = self.call()
        self.assertEqual(result["status"], "verified")
        self.assertTrue(result["success"])
        self.assertEqual(result["post_url"], "https://x.com/i/web/status/9001")
        self.assertEqual(self.client.created, [(_CONTENT, True)])
        self.assertEqual(self.client.reads, [(_POST_ID, ["author_id", "entities"], True)])
        second = self.call()
        self.assertEqual(second["status"], "already_verified")
        self.assertEqual(len(self.client.created), 1)
        self.assertEqual(len(self.client.reads), 1)
        with sqlite3.connect(self.db) as conn:
            row = conn.execute("SELECT status, post_id, verified_at FROM x_publications").fetchone()
        self.assertEqual(row[:2], ("verified", _POST_ID))
        self.assertIsNotNone(row[2])

    def test_content_and_account_binding_conflicts(self):
        self.call()
        self.assertEqual(self.call(content="changed")["error"], "content_conflict")
        self.client.user_id = "2002"
        self.assertEqual(self.call(expected_user_id="2002")["error"], "account_conflict")
        self.assertEqual(len(self.client.created), 1)

    def test_unknown_write_never_reposts_after_restart(self):
        self.client.create_error = TimeoutError("secret-example-must-not-escape")
        first = self.call()
        self.assertEqual(first["status"], "outcome_unknown")
        self.assertNotIn("secret-example", str(first))
        self.client.create_error = None
        second = self.call()
        self.assertEqual(second["status"], "outcome_unknown")
        self.assertEqual(len(self.client.created), 1)
        self.assertEqual(self.client.reads, [])

    def test_timed_out_create_returns_without_waiting_for_worker(self):
        released = threading.Event()
        finished = threading.Event()
        original = self.client.create_tweet

        def blocked_create(**kwargs):
            try:
                released.wait(timeout=2)
                return original(**kwargs)
            finally:
                finished.set()

        try:
            with patch.object(self.client, "create_tweet", side_effect=blocked_create), \
                 patch.object(_PUBLISHER, "_API_TIMEOUT_SECONDS", 0.03):
                result = self.call()
            self.assertEqual(result["status"], "outcome_unknown")
            self.assertEqual(self.client.created, [])
            self.assertEqual(self.call()["status"], "outcome_unknown")
        finally:
            released.set()
            self.assertTrue(finished.wait(timeout=2))

    def test_ephemeral_database_names_are_rejected(self):
        for path in (":memory:", "file::memory:?cache=shared"):
            with self.subTest(path=path):
                self.assertEqual(self.call(db_path=path)["status"], "storage_error")
        self.assertEqual(self.client.created, [])

    def test_malformed_create_id_is_unknown_and_never_retried(self):
        for index, bad_id in enumerate(("autonomous_post_123", True, None, "")):
            with self.subTest(bad_id=bad_id):
                self.client = FakeXClient()
                self.client.post_id = bad_id
                path = self.directory / f"bad_{index}.sqlite3"
                first = self.call(db_path=path)
                self.assertEqual(first["status"], "outcome_unknown")
                self.client.post_id = _POST_ID
                self.assertEqual(self.call(db_path=path)["status"], "outcome_unknown")
                self.assertEqual(len(self.client.created), 1)

    def test_known_id_pending_readback_only_retries_get(self):
        self.client.read_error = TimeoutError("private transport detail")
        first = self.call()
        self.assertEqual(first["status"], "readback_pending")
        self.assertEqual(first["post_id"], _POST_ID)
        self.client.read_error = None
        second = self.call()
        self.assertEqual(second["status"], "verified")
        self.assertEqual(len(self.client.created), 1)
        self.assertEqual(len(self.client.reads), 2)

    def test_expanded_station_link_verifies_complete_text(self):
        self.client.text = "Listen to AntifaFM: https://t.co/aB123"
        self.client.entities = {"urls": [{"url": "https://t.co/aB123",
                                           "expanded_url": "https://antifafm.com/"}]}
        self.assertEqual(self.call()["status"], "verified")

    def test_readback_mismatch_retains_id_and_does_not_repost(self):
        self.client.text = "An unrelated old post https://antifafm.com/"
        first = self.call()
        self.assertEqual(first["status"], "verification_failed")
        self.assertFalse(first["success"])
        self.client.text = _CONTENT
        self.client.author_id = "2002"
        self.assertEqual(self.call()["status"], "verification_failed")
        self.client.author_id = _USER_ID
        self.assertEqual(self.call()["status"], "verified")
        self.assertEqual(len(self.client.created), 1)

    def test_storage_claim_failure_prevents_write(self):
        with patch.object(_STORE.sqlite3, "connect", side_effect=sqlite3.OperationalError("private")):
            result = self.call()
        self.assertEqual(result["status"], "storage_error")
        self.assertEqual(result["error"], "claim_not_durable")
        self.assertEqual(self.client.created, [])

    def test_id_persistence_failure_blocks_second_create(self):
        with patch.object(_STORE.PublicationStore, "record_post_id", side_effect=OSError("private")):
            result = self.call()
        self.assertEqual(result["status"], "storage_error")
        self.assertEqual(result["post_id"], _POST_ID)
        self.assertEqual(self.call()["status"], "outcome_unknown")
        self.assertEqual(len(self.client.created), 1)
        self.assertEqual(self.client.reads, [])

    def test_verification_storage_failure_retries_only_readback(self):
        with patch.object(_STORE.PublicationStore, "record_readback", side_effect=OSError("private")):
            result = self.call()
        self.assertEqual(result["status"], "storage_error")
        self.assertFalse(result["success"])
        self.assertEqual(self.call()["status"], "verified")
        self.assertEqual(len(self.client.created), 1)

    def test_daily_cap_and_distinct_account(self):
        with patch.object(_STORE.time, "time", return_value=1000000):
            self.assertEqual(self.call()["status"], "verified")
            self.assertEqual(self.call(job_id="day_2")["status"], "rate_limited")
            self.client.user_id = self.client.author_id = "2002"
            self.assertEqual(self.call(account=_INTERFACE.XAccount.ANTIFAFM,
                                       expected_user_id="2002")["status"], "verified")
        self.client.user_id = self.client.author_id = _USER_ID
        with patch.object(_STORE.time, "time", return_value=1086401):
            self.assertEqual(self.call(job_id="day_2")["status"], "verified")

    def test_concurrent_claim_sends_at_most_once(self):
        self.client.barrier = threading.Barrier(2)
        with ThreadPoolExecutor(max_workers=2) as workers:
            futures = [workers.submit(self.call) for _ in range(2)]
            results = [future.result(timeout=10) for future in futures]
        self.assertEqual(len(self.client.created), 1)
        self.assertIn("verified", [r["status"] for r in results])
        self.assertTrue(all(r["status"] in {"verified", "already_verified", "outcome_unknown"}
                            for r in results))

    def test_new_account_is_blocked_before_legacy_transport(self):
        interface = _INTERFACE.UnifiedXInterface()
        request = _INTERFACE.XPostRequest(
            content=_CONTENT, content_type=_INTERFACE.XContentType.GENERAL_POST,
            account=_INTERFACE.XAccount.ANTIFAFM,
        )
        with patch.object(interface, "check_duplicate", side_effect=AssertionError("legacy history")):
            result = asyncio.run(interface.post_to_x(request))
        self.assertFalse(result.success)
        self.assertFalse(interface._post_direct_via_selenium(request)[0])


class TestRealPackageImports(unittest.TestCase):
    def test_real_imports_and_dry_run_do_not_initialize_runtime_owners(self):
        """Import actual package parents with runtime reads/writes/network denied."""
        denied = AssertionError("Runtime I/O is not admitted during import/dry-run")
        with ExitStack() as stack:
            stack.enter_context(patch.dict(sys.modules))
            for name in tuple(sys.modules):
                if name == "modules" or name.startswith("modules."):
                    del sys.modules[name]
            stack.enter_context(patch.object(sys, "path", [str(_ROOT), *sys.path]))
            stack.enter_context(patch.object(sys, "dont_write_bytecode", True))
            for target in (
                "builtins.open", "pathlib.Path.open", "pathlib.Path.mkdir",
                "os.mkdir", "os.makedirs", "sqlite3.connect",
                "socket.socket.connect", "socket.socket.connect_ex",
                "socket.create_connection", "subprocess.Popen",
            ):
                stack.enter_context(patch(target, side_effect=denied))
            interface = importlib.import_module(_SOCIAL + ".src.unified_x_interface")
            importlib.import_module(_X + ".src.verified_x_publisher")
            importlib.import_module(_SOCIAL + ".src.core.publication_store")
            result = asyncio.run(interface.post_verified_x(
                _CONTENT, interface.XAccount.ANTIFAFM, "antifafm_station", "day_1",
                client=object(), expected_user_id=_USER_ID,
                db_path="not-created/receipts.sqlite3", dry_run=True,
            ))
            self.assertEqual(result["status"], "dry_run")
            self.assertIsNone(result["post_id"])
            for name in (_X + ".src.x_twitter_dae",
                         _SOCIAL + ".src.simple_posting_orchestrator",
                         "modules.infrastructure.foundups_selenium.src.browser_manager"):
                self.assertNotIn(name, sys.modules)


if __name__ == "__main__":
    unittest.main()
