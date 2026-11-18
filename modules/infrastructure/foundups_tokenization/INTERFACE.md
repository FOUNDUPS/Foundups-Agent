# FoundUps tokenization design interface

This directory currently contains design and handoff documents only. It has no
tracked Python service, Solidity contract, executable entrypoint, deployment
manifest or test implementation. Its interface status is
**SPECIFIED_NOT_IMPLEMENTED within this directory**; it must not be imported as
an operational tokenization API.

The [implementation handoff](IMPLEMENTATION_HANDOFF.md) contains historical
proposed class/contract names and method signatures. They are design examples,
not exported symbols, callable endpoints or deployed contract addresses. This
document neither instantiates those proposals nor changes the current blockchain
architecture owned elsewhere in the repository.

For the documented CABR semantics, follow the later correction in
[CABR_INTEGRATION.md](docs/CABR_INTEGRATION.md) and [ModLog.md](ModLog.md): PoB gates
the flow, CABR scales routing from treasury, and CABR does not mint UPS. Earlier
README/handoff mint-trigger language remains historical drift and must not be
treated as a current implementation contract. [TOKENOMICS.md](docs/TOKENOMICS.md)
is a design reference, not evidence of reserves, yield, issuance or live operation.

No wallet, funds, deployment, provider, contract call or financial claim was
verified or changed in this documentation layer. Future implementation requires
an owned executable boundary, current architecture reconciliation and acceptance
evidence before a runtime or deployment status can be asserted.
