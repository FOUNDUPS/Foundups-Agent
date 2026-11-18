# Implementation TODO — RedDog Ephemeral Authority Worker Routing

Canonical implementation tracking is GitHub issue #1584.

This file exists only as an in-repository breadcrumb for workers that operate without GitHub issue discovery.

Do not implement from this file alone. Follow WSP 97, retrieve current WSP 15, WSP 71, WSP 81, RedDog model-routing evidence, AI Gateway runtime-binding contracts, and `docs/architecture/REDDOG_EPHEMERAL_AUTHORITY_WORKER_ROUTING.md` before changing runtime code.

Required future closure:

1. Define WorkOrder task-compute requirements independently from WSP 15 priority.
2. Bind requirements to AI Gateway `ModelTaskRequirements` and verified runtime topology.
3. Bind RedDog/WRE worker reservation to the approved work order and runtime binding.
4. Implement an Ephemeral Authority Broker PoC with fake/test authority only.
5. Prefer gateway/proxy execution so workers never see credentials.
6. Enforce single-use/short-TTL/resource/action/work-order/worker-lease bounds and fail closed.
7. Prove closed worker environments contain no ambient durable credentials.
8. Red-team worker/supply-chain compromise and prove principal credentials remain outside the blast radius.

Truth label: `SPECIFIED_NOT_IMPLEMENTED` until runtime code and direct tests close the contract.
