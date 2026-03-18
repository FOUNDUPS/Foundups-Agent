// modules/platform_integration/zeroclaw/src/lib.rs
// ZeroClaw Core Engine Traits

/// ZeroClaw High-Frequency Trading Engine (Solana Pivot).
/// Focus: Zero-allocation and strict memory layout patterns.

pub mod memory_layout {
    /// Represents the strict memory-layout constraints for a ZeroClaw action.
    /// Uses #[repr(C)] to ensure predictable memory layout for zero-copy deserialization
    /// and minimal allocation overhead required for Solana's compute restrictions.
    #[repr(C)]
    pub struct ExecutionContext {
        pub program_id: [u8; 32],
        pub max_compute_units: u32,
        pub nonce: u64,
    }
}

pub mod execution {
    use crate::memory_layout::ExecutionContext;

    #[derive(Debug)]
    pub enum ExecutionError {
        ComputeExceeded,
        InvariantViolation,
        MemoryLayoutInvalid,
    }

    /// The base trait for a single execution action in the HFT loop.
    pub trait TradingAction {
        /// Zero-allocation execution: mutates state in place.
        fn execute_in_place(&mut self, context: &mut ExecutionContext) -> Result<(), ExecutionError>;
        
        /// Validates the precise compute unit cost before execution begins.
        fn compute_cost(&self) -> u32;
    }

    /// The core execution loop constraints for the ZeroClaw engine.
    /// Enforces that the supervisor can tick the HFT engine predictably
    /// without garbage collection or unbounded pauses.
    pub trait ZeroClawSupervisor {
        /// Tick the state machine forward by one predictable cycle.
        fn tick(&mut self) -> Result<(), ExecutionError>;
        
        /// Halt operations immediately on invariant violation (WSP 95 compliance).
        fn emergency_halt(&self);
    }
}
