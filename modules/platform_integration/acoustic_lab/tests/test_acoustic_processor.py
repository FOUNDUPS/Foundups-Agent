#!/usr/bin/env python3
"""
Acoustic Lab - Test Suite for Acoustic Processor

Tests the core functionality of audio fingerprinting and triangulation.
"""



import unittest
import numpy as np
from src.acoustic_processor import AcousticProcessor, AudioValidationError, GPSValidationError
from src.audio_library import AudioLibrary


class TestAcousticProcessor(unittest.TestCase):
    """Test cases for acoustic processing functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.processor = AcousticProcessor()
        self.library = AudioLibrary()

    def test_audio_library_initialization(self):
        """Test that audio library initializes with synthetic tones."""
        tones = self.library.get_available_tones()
        self.assertEqual(len(tones), 3)
        self.assertIn('Tone A', tones)
        self.assertIn('Tone B', tones)
        self.assertIn('Tone C', tones)

    def test_fingerprint_matching(self):
        """Test MFCC fingerprint matching against synthetic tones."""
        # Get a known fingerprint
        fingerprint_a = self.library.get_tone_fingerprint('Tone A')

        # Match should return high confidence for same tone
        match, confidence = self.library.match_fingerprint(fingerprint_a)
        self.assertEqual(match, 'Tone A')
        self.assertGreater(confidence, 0.8)

    def test_invalid_metadata(self):
        """Test validation of missing or invalid metadata."""
        # Test missing metadata
        with self.assertRaises(GPSValidationError):
            self.processor._validate_metadata({})

        # Test missing GPS
        with self.assertRaises(GPSValidationError):
            self.processor._validate_metadata({'timestamp': '2025-01-01T00:00:00Z'})

        # Test invalid coordinates
        with self.assertRaises(GPSValidationError):
            self.processor._validate_metadata({
                'gps': {'latitude': 100, 'longitude': 0},
                'timestamp': '2025-01-01T00:00:00Z'
            })

    def test_audio_validation(self):
        """Test audio content validation."""
        # Test silence (should fail)
        silence = np.zeros(1000)
        self.assertFalse(self.library.validate_audio_signature(silence))

        # Test high-frequency content (should pass)
        sample_rate = 22050
        t = np.linspace(0, 0.1, int(0.1 * sample_rate))
        high_freq = np.sin(2 * np.pi * 1500 * t)  # 1.5 kHz tone
        self.assertTrue(self.library.validate_audio_signature(high_freq))

    def test_triangulation_calculation(self):
        """Test basic triangulation functionality."""
        # Test data with known sensor positions
        test_metadata = {
            'gps': {'latitude': 40.7649, 'longitude': -111.8421},
            'timestamp': '2025-10-02T14:30:00Z'
        }

        location, triangulation_data = self.processor._calculate_location(test_metadata)

        # Should return valid coordinates
        self.assertIsInstance(location, tuple)
        self.assertEqual(len(location), 2)
        self.assertIsInstance(triangulation_data, dict)
        self.assertIn('sensors_used', triangulation_data)


class TestAudioLibrary(unittest.TestCase):
    """Test cases for audio library functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.library = AudioLibrary()

    def test_synthetic_tone_generation(self):
        """Test generation of synthetic audio tones."""
        tone_a = self.library._generate_synthetic_tone(1000, 1.0)
        self.assertEqual(len(tone_a), 22050)  # 1 second at 22kHz

        # Check that it contains the expected frequency
        fft = np.fft.fft(tone_a)
        freqs = np.fft.fftfreq(len(tone_a), 1/22050)
        peak_freq_idx = np.argmax(np.abs(fft))
        peak_freq = abs(freqs[peak_freq_idx])
        self.assertAlmostEqual(peak_freq, 1000, delta=10)  # Within 10 Hz

    def test_mfcc_fingerprint_consistency(self):
        """Test that MFCC fingerprints are consistent for same audio."""
        tone = self.library._generate_synthetic_tone(1000, 1.0)

        # Generate fingerprint twice
        fp1 = self.library._compute_mfcc_fingerprint(tone)
        fp2 = self.library._compute_mfcc_fingerprint(tone)

        # Should be identical
        np.testing.assert_array_almost_equal(fp1, fp2)


class TestEthereumLoggerCompatibility(unittest.TestCase):
    """Real Web3 middleware with an in-memory provider; run under the effect guard."""

    def setUp(self):
        from importlib.metadata import version
        from web3 import Web3
        from web3.middleware import ExtraDataToPOAMiddleware
        from src import ethereum_logger

        self.assertEqual(version('web3'), '7.15.0')
        self.assertEqual(version('eth-account'), '0.13.6')
        self.assertTrue(ethereum_logger.WEB3_AVAILABLE)
        self.assertIs(ethereum_logger.Web3, Web3)
        self.module = ethereum_logger
        self.web3_class = Web3
        self.poa = ExtraDataToPOAMiddleware
        self.providers = []

    def tearDown(self):
        for provider in self.providers:
            self.assertEqual(provider.unexpected, [])
            self.assertEqual(provider.calls, provider.expected)

    def _provider(self, replies):
        from copy import deepcopy
        from web3.providers.base import JSONBaseProvider

        class ControlledProvider(JSONBaseProvider):
            def __init__(self):
                super().__init__()
                self.calls = []
                self.unexpected = []
                self.expected = [(method, params) for method, params, _ in replies]

            def make_request(self, method, params):
                call = (str(method), list(params))
                position = len(self.calls)
                self.calls.append(call)
                if position >= len(replies) or call != self.expected[position]:
                    self.unexpected.append(call)
                    raise AssertionError('Unexpected synthetic provider method/params')
                response = replies[position][2]
                if isinstance(response, Exception):
                    raise response
                return deepcopy(response)

        provider = ControlledProvider()
        self.providers.append(provider)
        return provider

    @staticmethod
    def _response(result):
        return {'jsonrpc': '2.0', 'id': 1, 'result': result}

    def _logger(self, provider):
        from unittest.mock import patch

        url = 'https://acoustic-compatibility.invalid'
        with patch.object(self.web3_class, 'HTTPProvider', return_value=provider) as factory:
            logger = self.module.EthereumLogger(testnet_url=url)
        factory.assert_called_once_with(url)
        self.assertIsInstance(logger.web3, self.web3_class)
        self.assertIs(logger.web3.provider, provider)
        return logger

    def test_actual_constructor_preserves_default_middleware(self):
        provider = self._provider([
            ('web3_clientVersion', [], self._response('synthetic-web3')),
        ])
        logger = self._logger(provider)
        self.assertFalse(logger.simulate_only)
        defaults = self.web3_class(provider).middleware_onion.as_tuple_of_middleware()
        actual = logger.web3.middleware_onion.as_tuple_of_middleware()
        self.assertEqual(actual[:-1], defaults)
        self.assertIs(actual[-1], self.poa)

    def test_actual_poa_block_transform_and_default_rejection(self):
        from hexbytes import HexBytes
        from web3.exceptions import ExtraDataLengthError

        extra = '0x' + '11' * 33
        result = {'number': '0x2a', 'extraData': extra}
        identifiers = [('latest', 'eth_getBlockByNumber'),
                       ('0x' + '22' * 32, 'eth_getBlockByHash')]
        for identifier, method in identifiers:
            with self.subTest(identifier=identifier):
                provider = self._provider([
                    ('web3_clientVersion', [], self._response('synthetic-web3')),
                    (method, [identifier, False], self._response(result)),
                ])
                logger = self._logger(provider)
                self.assertFalse(logger.simulate_only)
                block = logger.web3.eth.get_block(identifier)
                self.assertNotIn('extraData', block)
                self.assertEqual(block['proofOfAuthorityData'], HexBytes(extra))
                self.assertIsInstance(block['proofOfAuthorityData'], HexBytes)
                self.assertEqual(block['number'], 42)
                for outer_poa in (False, True):
                    with self.subTest(outer_poa=outer_poa):
                        control = self._provider([
                            (method, [identifier, False], self._response(result)),
                        ])
                        web3 = self.web3_class(control)
                        if outer_poa:
                            web3.middleware_onion.add(self.poa)
                        with self.assertRaises(ExtraDataLengthError):
                            web3.eth.get_block(identifier)

    def test_connection_failures_preserve_simulation_fallback(self):
        failures = [
            {'jsonrpc': '2.0', 'id': 1,
             'error': {'code': -32000, 'message': 'synthetic unavailable'}},
            OSError('synthetic unavailable'),
            RuntimeError('synthetic initialization failure'),
        ]
        for response in failures:
            with self.subTest(response_type=type(response).__name__):
                provider = self._provider([('web3_clientVersion', [], response)])
                logger = self._logger(provider)
                self.assertTrue(logger.simulate_only)
                self.assertEqual(logger.get_network_stats()['network'],
                                 'Educational Simulation')

    def test_actual_web3_network_stat_conversions(self):
        provider = self._provider([
            ('web3_clientVersion', [], self._response('synthetic-web3')),
            ('eth_chainId', [], self._response('0xaa36a7')),
            ('eth_blockNumber', [], self._response('0x2a')),
            ('eth_gasPrice', [], self._response('0x7')),
        ])
        logger = self._logger(provider)
        self.assertFalse(logger.simulate_only)
        self.assertEqual(logger.get_network_stats(), {
            'network': 11155111, 'latest_block': 42, 'gas_price': 7,
            'educational_purpose': 'Real blockchain proof-of-existence',
        })

    def test_results_hash_is_canonical_and_ignores_ethereum_hash(self):
        import hashlib

        provider = self._provider([
            ('web3_clientVersion', [], self._response('synthetic-web3')),
        ])
        logger = self._logger(provider)
        expected = hashlib.sha256(b'{"confidence":0.5,"sound_type":"Tone A"}').hexdigest()
        first = {'sound_type': 'Tone A', 'confidence': 0.5, 'ethereum_hash': 'old'}
        reordered = {'ethereum_hash': 'new', 'confidence': 0.5, 'sound_type': 'Tone A'}
        self.assertEqual(logger._create_results_hash(first), expected)
        self.assertEqual(logger._create_results_hash(reordered), expected)
        self.assertNotEqual(logger._create_results_hash({**first, 'confidence': 0.6}),
                            expected)

    def test_connected_logging_remains_simulated_without_provider_calls(self):
        import hashlib
        from unittest.mock import patch

        provider = self._provider([
            ('web3_clientVersion', [], self._response('synthetic-web3')),
        ])
        logger = self._logger(provider)
        self.assertFalse(logger.simulate_only)
        results = {'confidence': 0.5, 'sound_type': 'Tone A'}
        digest = hashlib.sha256(b'{"confidence":0.5,"sound_type":"Tone A"}').hexdigest()
        expected = 'simulated_' + hashlib.sha256(
            f'{digest}:1700000000:acoustic_lab'.encode()).hexdigest()[:32]
        with patch.object(self.module.time, 'time', return_value=1700000000):
            identifier = logger.log_acoustic_analysis(results)
            self.assertEqual(identifier, expected)
            self.assertEqual(logger.verify_log(identifier), {
                'verified': True, 'timestamp': 1700000000,
                'block_number': 'simulated',
                'educational_note': 'This demonstrates blockchain verification concepts',
            })
        self.assertIsNone(logger.verify_log('not-a-chain-receipt'))


if __name__ == '__main__':
    unittest.main()
