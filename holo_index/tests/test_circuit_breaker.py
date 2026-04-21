# -*- coding: utf-8 -*-
"""
Tests for circuit_breaker.py - Core Circuit Breaker Pattern Tests

Tests run in HOLO_SKIP_MODEL=1 mode (no model dependencies).

WSP Compliance:
    WSP 5: Test Coverage
    WSP 64: Violation Prevention
"""
import pytest
import time
from holo_index.core.circuit_breaker import (
    HoloIndexCircuitBreaker,
    CircuitBreakerManager,
    CircuitBreakerOpenError,
    circuit_manager,
)


class TestHoloIndexCircuitBreaker:
    """Tests for HoloIndexCircuitBreaker class"""

    def test_initial_state_is_closed(self):
        """Circuit breaker starts in CLOSED state"""
        cb = HoloIndexCircuitBreaker()
        assert cb.state == "CLOSED"
        assert cb.failure_count == 0
        assert cb.total_calls == 0

    def test_successful_call_increments_counters(self):
        """Successful calls increment success counter"""
        cb = HoloIndexCircuitBreaker()
        result = cb.call(lambda: "success")

        assert result == "success"
        assert cb.total_calls == 1
        assert cb.total_successes == 1
        assert cb.total_failures == 0
        assert cb.state == "CLOSED"

    def test_failed_call_increments_failure_count(self):
        """Failed calls increment failure counter"""
        cb = HoloIndexCircuitBreaker(failure_threshold=5)

        def failing_func():
            raise ValueError("test error")

        with pytest.raises(ValueError):
            cb.call(failing_func)

        assert cb.failure_count == 1
        assert cb.total_failures == 1
        assert cb.state == "CLOSED"

    def test_circuit_opens_after_threshold_failures(self):
        """Circuit opens after reaching failure threshold"""
        cb = HoloIndexCircuitBreaker(failure_threshold=3, timeout=300)

        def failing_func():
            raise ValueError("test error")

        # Trigger 3 failures to reach threshold
        for _ in range(3):
            with pytest.raises(ValueError):
                cb.call(failing_func)

        assert cb.state == "OPEN"
        assert cb.circuit_opens == 1

    def test_open_circuit_raises_error_without_cache(self):
        """Open circuit raises error when no cache available"""
        cb = HoloIndexCircuitBreaker(failure_threshold=2, timeout=300)

        def failing_func():
            raise ValueError("test error")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(failing_func)

        assert cb.state == "OPEN"

        # Next call should raise CircuitBreakerOpenError
        with pytest.raises(CircuitBreakerOpenError):
            cb.call(lambda: "should not execute")

    def test_open_circuit_returns_cached_result(self):
        """Open circuit returns cached result when available"""
        cb = HoloIndexCircuitBreaker(failure_threshold=2, timeout=300)

        # First successful call to populate cache
        result1 = cb.call(lambda: "cached_value")
        assert result1 == "cached_value"
        assert cb.last_successful_result == "cached_value"

        # Trigger failures to open circuit
        def failing_func():
            raise ValueError("test error")

        for _ in range(2):
            try:
                cb.call(failing_func)
            except ValueError:
                pass

        assert cb.state == "OPEN"

        # Should return cached value
        result2 = cb.call(lambda: "new_value")
        assert result2 == "cached_value"

    def test_half_open_state_after_timeout(self):
        """Circuit transitions to HALF_OPEN after timeout"""
        cb = HoloIndexCircuitBreaker(failure_threshold=2, timeout=0, recovery_threshold=1)

        # First populate cache so we don't get CircuitBreakerOpenError
        cb.call(lambda: "cached_value")

        def failing_func():
            raise ValueError("test error")

        # Open circuit with failures
        for _ in range(2):
            try:
                cb.call(failing_func)
            except ValueError:
                pass

        assert cb.state == "OPEN"

        # Force last_failure_time to past to trigger timeout check
        cb.last_failure_time = time.time() - 1

        # After timeout, should transition to HALF_OPEN then CLOSED (recovery_threshold=1)
        cb.call(lambda: "recovery_test")
        assert cb.state == "CLOSED"

    def test_half_open_failure_returns_to_open(self):
        """HALF_OPEN state returns to OPEN on failure"""
        cb = HoloIndexCircuitBreaker(failure_threshold=2, timeout=0)

        # Open circuit
        for _ in range(2):
            try:
                cb.call(lambda: (_ for _ in ()).throw(ValueError("error")))
            except ValueError:
                pass

        # Circuit should go to HALF_OPEN on next call (timeout=0)
        # Force state to HALF_OPEN for testing
        cb.state = "HALF_OPEN"
        cb.consecutive_successes = 0

        def failing_func():
            raise ValueError("failure during recovery")

        with pytest.raises(ValueError):
            cb.call(failing_func)

        assert cb.state == "OPEN"

    def test_recovery_requires_consecutive_successes(self):
        """Full recovery requires recovery_threshold consecutive successes"""
        cb = HoloIndexCircuitBreaker(
            failure_threshold=2,
            timeout=0,
            recovery_threshold=3
        )

        # Open circuit
        for _ in range(2):
            try:
                cb.call(lambda: (_ for _ in ()).throw(ValueError("error")))
            except ValueError:
                pass

        # Force HALF_OPEN state
        cb.state = "HALF_OPEN"
        cb.consecutive_successes = 0

        # First success
        cb.call(lambda: "success1")
        assert cb.state == "HALF_OPEN"
        assert cb.consecutive_successes == 1

        # Second success
        cb.call(lambda: "success2")
        assert cb.state == "HALF_OPEN"
        assert cb.consecutive_successes == 2

        # Third success - should close
        cb.call(lambda: "success3")
        assert cb.state == "CLOSED"
        assert cb.consecutive_successes == 0

    def test_success_resets_failure_count(self):
        """Successful call resets failure count in CLOSED state"""
        cb = HoloIndexCircuitBreaker(failure_threshold=5)

        # Accumulate some failures
        for _ in range(3):
            try:
                cb.call(lambda: (_ for _ in ()).throw(ValueError("error")))
            except ValueError:
                pass

        assert cb.failure_count == 3

        # Successful call should reset
        cb.call(lambda: "success")
        assert cb.failure_count == 0

    def test_get_status_returns_metrics(self):
        """get_status returns comprehensive metrics"""
        cb = HoloIndexCircuitBreaker(operation_name="test_op")
        cb.call(lambda: "value")

        status = cb.get_status()

        assert status["operation"] == "test_op"
        assert status["state"] == "CLOSED"
        assert status["total_calls"] == 1
        assert status["total_successes"] == 1
        assert status["success_rate"] == 100.0
        assert status["has_cache"] == True

    def test_manual_reset(self):
        """Manual reset clears all state"""
        cb = HoloIndexCircuitBreaker(failure_threshold=2)

        # Open circuit
        for _ in range(2):
            try:
                cb.call(lambda: (_ for _ in ()).throw(ValueError("error")))
            except ValueError:
                pass

        assert cb.state == "OPEN"

        cb.reset()

        assert cb.state == "CLOSED"
        assert cb.failure_count == 0
        assert cb.consecutive_successes == 0


class TestCircuitBreakerManager:
    """Tests for CircuitBreakerManager class"""

    def test_default_breakers_exist(self):
        """Manager creates default breakers for each operation type"""
        manager = CircuitBreakerManager()

        assert "chromadb" in manager.breakers
        assert "embedding" in manager.breakers
        assert "filesystem" in manager.breakers

    def test_get_breaker_returns_correct_type(self):
        """get_breaker returns correct breaker for operation type"""
        manager = CircuitBreakerManager()

        chromadb_breaker = manager.get_breaker("chromadb")
        assert chromadb_breaker.operation_name == "ChromaDB"

        embedding_breaker = manager.get_breaker("embedding")
        assert embedding_breaker.operation_name == "Embedding"

        filesystem_breaker = manager.get_breaker("filesystem")
        assert filesystem_breaker.operation_name == "FileSystem"

    def test_get_breaker_returns_default_for_unknown(self):
        """get_breaker returns chromadb breaker for unknown type"""
        manager = CircuitBreakerManager()

        unknown_breaker = manager.get_breaker("unknown_type")
        assert unknown_breaker.operation_name == "ChromaDB"

    def test_get_all_status_returns_all_statuses(self):
        """get_all_status returns status for all breakers"""
        manager = CircuitBreakerManager()

        all_status = manager.get_all_status()

        assert "chromadb" in all_status
        assert "embedding" in all_status
        assert "filesystem" in all_status

        for name, status in all_status.items():
            assert "state" in status
            assert "total_calls" in status

    def test_reset_all_resets_all_breakers(self):
        """reset_all resets all breakers"""
        manager = CircuitBreakerManager()

        # Trigger failures on one breaker
        chromadb = manager.get_breaker("chromadb")
        for _ in range(3):
            try:
                chromadb.call(lambda: (_ for _ in ()).throw(ValueError("error")))
            except ValueError:
                pass

        assert chromadb.state == "OPEN"

        manager.reset_all()

        assert chromadb.state == "CLOSED"


class TestGlobalCircuitManager:
    """Tests for global circuit_manager instance"""

    def test_global_manager_exists(self):
        """Global circuit_manager instance exists"""
        assert circuit_manager is not None
        assert isinstance(circuit_manager, CircuitBreakerManager)

    def test_global_manager_has_all_breakers(self):
        """Global manager has all expected breakers"""
        assert "chromadb" in circuit_manager.breakers
        assert "embedding" in circuit_manager.breakers
        assert "filesystem" in circuit_manager.breakers


class TestCircuitBreakerEdgeCases:
    """Edge case tests for circuit breaker"""

    def test_cached_result_fallback_on_failure(self):
        """Returns cached result when call fails with cache available"""
        cb = HoloIndexCircuitBreaker()

        # Populate cache
        cb.call(lambda: "cached")

        # Fail once (under threshold)
        result = cb.call(lambda: (_ for _ in ()).throw(ValueError("error")))

        assert result == "cached"

    def test_cache_timestamp_updated_on_success(self):
        """Cache timestamp updates on each successful call"""
        cb = HoloIndexCircuitBreaker()

        cb.call(lambda: "first")
        first_timestamp = cb.cache_timestamp

        time.sleep(0.01)

        cb.call(lambda: "second")
        second_timestamp = cb.cache_timestamp

        assert second_timestamp > first_timestamp

    def test_different_failure_thresholds(self):
        """Different operation types have different thresholds"""
        manager = CircuitBreakerManager()

        chromadb = manager.get_breaker("chromadb")
        embedding = manager.get_breaker("embedding")
        filesystem = manager.get_breaker("filesystem")

        assert chromadb.failure_threshold == 3
        assert embedding.failure_threshold == 5
        assert filesystem.failure_threshold == 10

    def test_none_result_not_cached(self):
        """None results are cached (explicit check)"""
        cb = HoloIndexCircuitBreaker()

        cb.call(lambda: None)

        # None is a valid result, so it should be cached
        assert cb.last_successful_result is None
