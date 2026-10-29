# ZeroClaw interface sketch

The tracked implementation is `src/lib.rs`, a Rust interface sketch for a proposed execution engine. It defines memory_layout::ExecutionContext (program_id, max_compute_units, nonce), execution::ExecutionError, and the TradingAction and ZeroClawSupervisor traits.

TradingAction declares execute_in_place and compute_cost. ZeroClawSupervisor declares tick and emergency_halt. The file contains no concrete execution loop, action implementation, wallet, signing, broadcasting, exchange or settlement integration. The comments describing high-frequency trading and zero allocation are design intentions, not validated operational guarantees.

ExecutionContext uses repr(C); no wire encoding or target-specific layout acceptance is established here. There is no tracked Cargo manifest, build target or dedicated test suite in this module. Keep this source as specified interface work until a separately scoped implementation and executable acceptance exist. No financial or network operation was run for this documentation.
