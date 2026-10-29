# ZeroClaw specified Rust interfaces

Source: [src/lib.rs](src/lib.rs). Status: SPECIFIED_NOT_IMPLEMENTED for the engine;
the tracked source declares types and traits, without concrete execution behavior.

memory_layout::ExecutionContext uses repr(C) and fields program_id: [u8; 32],
max_compute_units: u32, nonce: u64. No wire encoder, deserializer or accepted
target-specific layout is provided by this file.

execution::ExecutionError declares ComputeExceeded, InvariantViolation and
MemoryLayoutInvalid. TradingAction declares execute_in_place(&mut self,
context: &mut ExecutionContext) -> Result<(), ExecutionError> and
compute_cost(&self) -> u32. ZeroClawSupervisor declares tick(&mut self) ->
Result<(), ExecutionError> and emergency_halt(&self).

There are no trait implementations, wallet/signing/settlement integrations,
Cargo manifest or dedicated tests in this module at this revision. Comments
about zero allocation, compute limits and high-frequency execution are intended
constraints; these declarations cannot enforce or validate them on their own.
No financial operation, network call, build or performance benchmark was run.
