"""Disposable Ed25519 model evidence and actual descriptor files, no model calls."""

import json
from pathlib import Path

from modules.communication.moltbot_bridge.tests import model_runtime_binding_receipt_test_helpers as fixtures
from modules.ai_intelligence.ai_gateway.tests import model_signed_evidence_test_helpers as signatures
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import digest, raw_digest
from modules.communication.moltbot_bridge.src.reddog_model_verifier_selection_inputs import SCHEMA


def model_inputs(monkeypatch, root, *, now=1000):
    fixtures._real_model_evidence_signatures(monkeypatch)
    monkeypatch.setattr(signatures, 'NOW', now)
    records, entries = [], []
    for index in range(3):
        model_id = 'synthetic/model-' + str(index)
        selection, binding = fixtures.model_selection_and_runtime_binding_receipts(
            runtime_surface='reddog_artifact_generation', model_id=model_id, verified_at_epoch=now)
        verifier = fixtures.model_runtime_binding_test_verifier(binding)
        payloads = dict(catalog=verifier.catalog_snapshot,
            benchmarks={'benchmark_evidence_receipts': verifier.benchmark_evidence_receipts},
            promotions={'promotion_evidence_receipts': verifier.promotion_evidence_receipts},
            evidence=verifier.verified_evidence_bundle, policy=verifier.runtime_policy,
            trusted_keys=verifier.trusted_keys_payload)
        inputs = {}
        for name, payload in payloads.items():
            path = Path(root) / ('selection-' + str(index) + '-' + name + '.json')
            raw = json.dumps(payload, sort_keys=True).encode('utf-8')
            path.write_bytes(raw)
            inputs[name] = dict(path=str(path), raw_digest=raw_digest(raw))
        entries.append(dict(selection_receipt_id=selection['receipt_id'],
                            selection_receipt_digest=digest(selection), inputs=inputs))
        records.append(dict(model_id=model_id, selection=selection, binding=binding))
    authority = dict(schema_version=SCHEMA, issued_at=now - 1, expires_at=now + 30, entries=entries)
    return dict(author=records[0], reviewers={'reviewer:test': records[1], 'reviewer:second': records[2]}), authority
