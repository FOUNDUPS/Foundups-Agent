# PAL Runtime Wiring Note

The Principal Activity Ledger is part of RedDog's executable runtime closure through:

`extension.js -> principal_memex_disclosure_source -> principal_activity_extension_adapter -> principal_activity_ledger`

Runtime data is intentionally **not** part of the Git repository. Code, tests, schemas and governance are bounded to the codebase; principal activity data remains in extension-local storage encrypted for the principal, with the key held in SecretStorage.

This distinction is intentional: source control governs the mechanism, but does not become 012's personal memory store.

The current executable alpha exposes explicit local capture, local context inspection, and local status commands. Automatic ingestion from every RedDog turn or phone/app activity remains a later adapter slice and must preserve the same capture-authority / disclosure-authority separation.
