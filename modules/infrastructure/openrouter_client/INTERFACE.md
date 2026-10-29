# Reserved OpenRouter client interface

This directory is a dormant reservation with **no tracked implementation and no
public callable API**. The [README](README.md) records the earlier source revert,
`contract_pending` state and the integration manifest's `parked` classification.
Untracked bytecode, a directory name or a remembered import path does not restore
that implementation or authorize a runtime import.

There are no request/response schemas, constructors, network methods, credentials
or provider endpoints exported by this module. The advisory Fusion worker-panel
contract is owned by the existing moltbot bridge adapter; this directory must
not create a second transport or claim that adapter's runtime status.

The reservation's documented boundary forbids enabling runtime registration,
reading OpenRouter credentials here or treating this module as a live client.
Its historical redaction-gate prerequisite remains a boundary of this reservation,
not a claim about every other OpenRouter owner in the repository. No network,
credential lookup, import of orphan bytecode, provider call or activation occurred
for this contract documentation. A future implementation needs a separately
reviewed source change and executable acceptance evidence.
