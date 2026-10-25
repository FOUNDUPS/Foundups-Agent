#!/usr/bin/env python3
"""
Acoustic Lab - Ethereum Proof-of-Existence Logger

Logs SHA-256 hashes of acoustic analysis results to Ethereum testnet
for educational proof-of-existence demonstrations.
"""

import hashlib
import json
import time
from typing import Dict, Any, Optional
try:
    from web3 import Web3
    from web3.middleware import ExtraDataToPOAMiddleware
    WEB3_AVAILABLE = True
except ImportError:
    WEB3_AVAILABLE = False


class EthereumLogger:
    """
    Educational Ethereum logger for proof-of-existence.

    Logs acoustic analysis hashes to Ethereum testnet to demonstrate
    immutable timestamping of educational acoustic computations.
    """

    def __init__(self, testnet_url: str = "https://sepolia.infura.io/v3/YOUR_INFURA_KEY"):
        """
        Initialize Ethereum logger.

        Args:
            testnet_url: Ethereum testnet RPC URL (Sepolia recommended for education)
        """
        self.testnet_url = testnet_url
        self.web3 = None
        self.contract_address = None
        self.contract = None

        # For Phase 1, we'll simulate the logging unless web3 is available
        # In a full implementation, this would connect to actual Ethereum testnet
        self.simulate_only = not WEB3_AVAILABLE

        if not self.simulate_only:
            self._initialize_web3()

    def _initialize_web3(self):
        """Initialize Web3 connection to Ethereum testnet."""
        try:
            self.web3 = Web3(Web3.HTTPProvider(self.testnet_url))
            self.web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

            if not self.web3.is_connected():
                print("[U+26A0]️  Ethereum connection failed - simulating logging")
                self.simulate_only = True
            else:
                print("[OK] Connected to Ethereum testnet")
                # In a real implementation, load contract ABI and address here

        except Exception as e:
            print(f"[U+26A0]️  Ethereum initialization failed: {e} - simulating logging")
            self.simulate_only = True

    def log_acoustic_analysis(self, analysis_results: Dict[str, Any]) -> str:
        """
        Log acoustic analysis results to Ethereum for proof-of-existence.

        Args:
            analysis_results: Complete analysis results dictionary

        Returns:
            Transaction hash or simulation identifier
        """
        # Create deterministic hash of the analysis results
        results_hash = self._create_results_hash(analysis_results)

        if self.simulate_only:
            return self._simulate_logging(results_hash, analysis_results)
        else:
            return self._real_logging(results_hash, analysis_results)

    def _create_results_hash(self, results: Dict[str, Any]) -> str:
        """
        Create SHA-256 hash of analysis results for immutable logging.

        Args:
            results: Analysis results dictionary

        Returns:
            Hex string of SHA-256 hash
        """
        # Create deterministic JSON representation
        # Exclude ethereum_hash field to avoid circular reference
        hash_data = {k: v for k, v in results.items() if k != 'ethereum_hash'}
        json_str = json.dumps(hash_data, sort_keys=True, separators=(',', ':'))

        # Generate SHA-256 hash
        hash_obj = hashlib.sha256(json_str.encode('utf-8'))
        return hash_obj.hexdigest()

    def _simulate_logging(self, results_hash: str, results: Dict[str, Any]) -> str:
        """
        Simulate Ethereum logging for educational purposes.

        Args:
            results_hash: SHA-256 hash of analysis results
            results: Original analysis results

        Returns:
            Simulation transaction identifier
        """
        # Create a simulated transaction hash for educational demonstration
        timestamp = int(time.time())
        simulation_data = f"{results_hash}:{timestamp}:acoustic_lab"

        simulated_tx_hash = hashlib.sha256(simulation_data.encode()).hexdigest()

        # Log the simulated transaction for educational purposes
        print("[TARGET] Educational Proof-of-Existence (Simulated)")
        print(f"   [DATA] Analysis Hash: {results_hash}")
        print(f"   [U+26D3]️  Simulated TX: 0x{simulated_tx_hash[:64]}")
        print(f"   [PIN] Location: {results.get('location', 'Unknown')}")
        print(f"   [U+1F50A] Sound Type: {results.get('sound_type', 'Unknown')}")
        print(f"   [TARGET] Confidence: {results.get('confidence', 0):.3f}")
        print("   [BOOKS] Educational Note: This demonstrates how blockchain provides immutable proof-of-existence")
        print("   [LINK] In production, this hash would be permanently stored on Ethereum testnet")
        return f"simulated_{simulated_tx_hash[:32]}"

    def _real_logging(self, results_hash: str, results: Dict[str, Any]) -> str:
        """
        Log hash to actual Ethereum testnet (for future implementation).

        Args:
            results_hash: SHA-256 hash to log
            results: Original analysis results

        Returns:
            Actual Ethereum transaction hash
        """
        # This would implement actual Ethereum transaction in Phase 2/3
        # For now, fall back to simulation
        print("[U+26A0]️  Real Ethereum logging not implemented in Phase 1")
        return self._simulate_logging(results_hash, results)

    def verify_log(self, transaction_hash: str) -> Optional[Dict[str, Any]]:
        """
        Verify a logged transaction (educational demonstration).

        Args:
            transaction_hash: Transaction hash to verify

        Returns:
            Verification details or None if not found
        """
        if self.simulate_only or transaction_hash.startswith('simulated_'):
            return {
                'verified': True,
                'timestamp': int(time.time()),
                'block_number': 'simulated',
                'educational_note': 'This demonstrates blockchain verification concepts'
            }
        else:
            # Real verification would query Ethereum node
            return None

    def get_network_stats(self) -> Dict[str, Any]:
        """Get educational statistics about the logging network."""
        if self.simulate_only:
            return {
                'network': 'Educational Simulation',
                'total_logs': 1,  # Would track in real implementation
                'educational_purpose': 'Demonstrates blockchain proof-of-existence concepts',
                'phase': 'Phase 1 (Educational Prototype)'
            }
        else:
            return {
                'network': self.web3.eth.chain_id,
                'latest_block': self.web3.eth.block_number,
                'gas_price': self.web3.eth.gas_price,
                'educational_purpose': 'Real blockchain proof-of-existence'
            }


# Global logger instance
_ethereum_logger_instance = None

def get_ethereum_logger() -> EthereumLogger:
    """Get the global Ethereum logger instance (singleton pattern)."""
    global _ethereum_logger_instance
    if _ethereum_logger_instance is None:
        _ethereum_logger_instance = EthereumLogger()
    return _ethereum_logger_instance

# Educational demonstration function
def demonstrate_proof_of_existence():
    """Demonstrate the proof-of-existence concept with sample data."""
    logger = get_ethereum_logger()

    # Sample acoustic analysis results
    sample_results = {
        'location': [40.7649, -111.8421],
        'sound_type': 'Tone A',
        'confidence': 0.84,
        'triangulation_data': {
            'sensors_used': 3,
            'error_estimate': 15.2
        }
    }

    # Log and demonstrate verification
    tx_hash = logger.log_acoustic_analysis(sample_results)
    verification = logger.verify_log(tx_hash)

    print("\n[GRADUATE] Educational Proof-of-Existence Demonstration Complete")
    print(f"   [OK] Transaction: {tx_hash}")
    print(f"   [OK] Verification: {verification is not None}")

    return tx_hash, verification
