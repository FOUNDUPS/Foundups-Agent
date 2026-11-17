"""Bounded v12 protected model selections; no new verification authority."""

from .reddog_runtime_artifact_manifest_contract import RuntimeArtifactManifestError, is_sha256

SCHEMA = 'reddog_model_verifier_selection_authority.v1'
MAX_READS = 54
MAX_INPUT_BYTES = 8 * 1024 * 1024


def validate_selection_authority(value, *, validate_bundle):
    if (type(value) is not dict or set(value) != {'schema_version', 'issued_at', 'expires_at', 'entries'}
            or value['schema_version'] != SCHEMA or type(value['entries']) is not list
            or not 1 <= len(value['entries']) <= 9):
        raise RuntimeArtifactManifestError('model_selection_authority_invalid')
    identities, digests = set(), set()
    for entry in value['entries']:
        if (type(entry) is not dict or set(entry) != {'selection_receipt_id', 'selection_receipt_digest', 'inputs'}
                or type(entry['selection_receipt_id']) is not str
                or not entry['selection_receipt_id'].startswith('model_selection_receipt:')
                or not is_sha256('sha256:' + entry['selection_receipt_id'].removeprefix('model_selection_receipt:'))
                or not is_sha256(entry['selection_receipt_digest'])
                or entry['selection_receipt_id'] in identities
                or entry['selection_receipt_digest'] in digests):
            raise RuntimeArtifactManifestError('model_selection_descriptor_invalid')
        identities.add(entry['selection_receipt_id'])
        digests.add(entry['selection_receipt_digest'])
        validate_bundle(dict(issued_at=value['issued_at'], expires_at=value['expires_at'], inputs=entry['inputs']))


def select_bundle(value, selection_id, selection_digest):
    matches = [entry for entry in value['entries']
               if entry['selection_receipt_id'] == selection_id
               and entry['selection_receipt_digest'] == selection_digest]
    if len(matches) != 1:
        raise RuntimeArtifactManifestError('model_selection_descriptor_missing')
    return dict(issued_at=value['issued_at'], expires_at=value['expires_at'], inputs=matches[0]['inputs'])


class SelectionReadBudget:
    """One complete author/reviewer pass, never reset between selected records."""

    def __init__(self):
        self.reads, self.bytes = 0, 0

    def begin(self):
        if self.reads >= MAX_READS or self.bytes >= MAX_INPUT_BYTES:
            raise RuntimeArtifactManifestError('model_selection_read_budget_exhausted')
        self.reads += 1
        return min(1024 * 1024, MAX_INPUT_BYTES - self.bytes)

    def finish(self, raw):
        self.bytes += len(raw)
        if self.bytes > MAX_INPUT_BYTES:
            raise RuntimeArtifactManifestError('model_selection_read_budget_exhausted')
