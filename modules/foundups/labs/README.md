# FoundUps Labs — educational FoundUp module

**Status: scaffold/specification only; no runtime, deployed host, student data, affiliation or access grant.**

FoundUps Labs is an education sector of Play FoundUps Mall. Its intended direct entry is `lab.foundups.com` (DNS unverified). It reuses the existing p.fMALL shell, Fractal identity, tile grid, HPC-sized stage/player and caller-return state. **Do not fork HPC or create another backend.**

## Product
Public: discover STEM programs and founder-owned student FoundUps; browse by program, cohort, year and project status; open project boards in the same stage as optional video. Member: existing FoundUps invite gate plus separately enforced program/project permissions for publishing and participation. Independent programs can appear without endorsement; a dog affiliate mark is reserved for consented, verified affiliation. Student founders retain ownership and export rights after leaving a school/program.

## Source and boundaries
- [Federation architecture and 2010 historical prospectus](../docs/FOUNDUPS_LABS_FEDERATION_ARCHITECTURE_20261121.md)
- [Interface contract](INTERFACE.md)
- [Delivery roadmap](ROADMAP.md)
- [ModLog](ModLog.md)
- [Existing p.fMALL interface](../pfmall/INTERFACE.md)
- [Shared navigation contract](../docs/PFMALL_MALL_NAVIGATION_CONTRACT.md)
- [HPC reference shell](../hpc/README.md)

## Proposed route namespace
`lab.foundups.com` direct entry; `/f/labs` within shared Mall **only after** existing manifest/route admission and collision checks. Do not register an unverified host or add a new gate. Current implementation is not established by these documents.

## Module boundaries
Labs owns education program/project content requirements, not the shared shell, player, authentication, authorization infrastructure, Fractal graph or membership service. Runtime code and tests should be added only after the P0 census and WSP_15 prioritization.
