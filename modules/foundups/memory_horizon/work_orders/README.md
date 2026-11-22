# Memory Horizon autonomous-build work orders

| Order | Assignment | Depends on | Group |
|---|---|---|---|
| MH-RSI-01 | current-source / authority / scope preflight | — | G0 |
| MH-RSI-02 | low-fi game shell + event ledger | 01 | G1 |
| MH-RSI-03 | episodic measurement engine | 01 | G1 |
| MH-RSI-04 | procedural event/form content | 01 | G1 |
| MH-RSI-05 | data export + retention visualization | 01 | G1 |
| MH-RSI-06 | mobile UI + combined Sweep 0/1 integration | 02-05 | G2 |
| MH-RSI-07 | deterministic synthetic/browser acceptance | 06 | G3 |
| MH-RSI-08 | independent measurement/privacy/safety verification | 07 | G4 |
| MH-RSI-09 | WSP 102/104 public-surface integration | 08 | G5 |
| MH-RSI-10 | RSI outcome capture + next-cycle rescore | 08 | G5 |

Start only MH-RSI-01 until its current-source/authority evidence is accepted.

Coordinator starter:

```text
Read PROMETHEUS.md and CONTRACT.md. Bind current main and actual runtime authority.
Use numbered JSON as dispatch inventory. Admit only dependency-ready, non-overlapping
orders. Preserve blocked gates. Require RESULT_TEMPLATE evidence. Independent
verification is mandatory before public-surface work. Re-observe after every accepted
integration and issue narrow repair tickets rather than broad rewrites.
```

Worker starter:

```text
Read CONTRACT.md and your assigned JSON. Execute only that WSP 99 order.
Retrieve current evidence per WSP 97. Stay inside S/I/effect boundaries.
Return a redacted result shaped like RESULT_TEMPLATE.json. If blocked, preserve
useful permitted evidence and state the exact prerequisite; do not widen scope.
```
