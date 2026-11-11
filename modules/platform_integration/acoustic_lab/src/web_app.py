#!/usr/bin/env python3
"""
Acoustic Lab - Flask Web Application

Educational web application for acoustic triangulation and audio signature analysis.
Provides REST API endpoint for processing synthetic audio files with IP geofencing.
"""



import os
import json
import io
import subprocess
import requests
from flask import Flask, request, jsonify, render_template_string
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge
from .acoustic_processor import get_acoustic_processor, AudioValidationError, GPSValidationError
from .ethereum_logger import get_ethereum_logger

try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    YT_DLP_AVAILABLE = False
    yt_dlp = None


class IPGeofencingError(Exception):
    """Raised when request originates outside allowed geographic area."""
    pass


def create_app() -> Flask:
    """
    Create and configure the Flask application.

    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__)

    # Initialize acoustic processor
    processor = get_acoustic_processor()

    @app.route('/')
    def index():
        """Serve the educational web interface."""
        return render_template_string(get_html_template())

    @app.route('/upload', methods=['POST'])
    def upload_audio():
        """
        Process uploaded synthetic audio file or X video URL for acoustic analysis.

        Expects multipart/form-data with:
        - For file upload: 'audio' (WAV file) + 'metadata' (JSON string)
        - For X URL: 'x_url' (string) + 'metadata' (JSON string)

        Returns JSON analysis results or error message.
        """
        try:
            # Check IP geofencing (educational restriction to Utah)
            check_ip_geofencing(request.remote_addr)

            # Get metadata
            metadata_str = request.form.get('metadata', '{}')
            try:
                metadata = json.loads(metadata_str)
            except json.JSONDecodeError:
                raise BadRequest("Invalid metadata JSON")

            # Handle X URL processing
            if 'x_url' in request.form:
                x_url = request.form['x_url'].strip()
                if not x_url or not ('x.com' in x_url or 'twitter.com' in x_url):
                    raise BadRequest("Invalid X post URL")

                # Process X video URL
                file_data = process_x_video_url(x_url)
                metadata['source'] = 'x_video'

            # Handle direct file upload
            elif 'audio' in request.files:
                audio_file = request.files['audio']
                if not audio_file.filename or not audio_file.filename.endswith('.wav'):
                    raise BadRequest("Only WAV files are accepted")
                file_data = audio_file.read()
                metadata['source'] = 'direct_upload'

            else:
                raise BadRequest("Missing audio file or X URL")

            # Process audio data
            results = processor.process_audio(file_data, metadata)

            # Log to Ethereum testnet for educational proof-of-existence
            log_to_ethereum_testnet(results)

            return jsonify(results)

        except IPGeofencingError as e:
            return jsonify({'error': str(e)}), 403
        except AudioValidationError as e:
            return jsonify({'error': f'Audio validation failed: {str(e)}'}), 400
        except GPSValidationError as e:
            return jsonify({'error': f'GPS validation failed: {str(e)}'}), 400
        except (BadRequest, RequestEntityTooLarge) as e:
            return jsonify({'error': str(e)}), e.code
        except Exception as e:
            app.logger.error(f"Processing error: {str(e)}")
            return jsonify({'error': 'Internal processing error'}), 500

    @app.route('/health')
    def health_check():
        """Health check endpoint for monitoring."""
        stats = processor.get_processing_stats()
        return jsonify({
            'status': 'healthy',
            'service': 'Acoustic Lab',
            'version': '1.0.0',
            'stats': stats
        })

    return app


def check_ip_geofencing(client_ip: str):
    """
    Check if client IP is within allowed geographic area (Utah state).

    Args:
        client_ip: Client IP address string

    Raises:
        IPGeofencingError: If IP is outside Utah or API fails
    """
    # Allow localhost for development and testing
    if client_ip in ['127.0.0.1', 'localhost', '::1']:
        print("Development mode: Allowing localhost access")
        return

    try:
        # Use ip-api.com for free IP geolocation
        response = requests.get(f'http://ip-api.com/json/{client_ip}', timeout=5)
        response.raise_for_status()

        data = response.json()

        if data.get('status') != 'success':
            raise IPGeofencingError("Unable to determine location")

        # Check if in Utah (region code: UT)
        region = data.get('region', '').upper()
        if region != 'UT':
            state_name = data.get('regionName', 'Unknown')
            raise IPGeofencingError(
                f"Educational access restricted to Utah state. "
                f"Detected location: {state_name} ({region})"
            )

    except requests.RequestException as e:
        # Allow access if geolocation service is unavailable (graceful degradation)
        print(f"Warning: IP geolocation check failed: {e}")
        print("Allowing access for educational purposes")


def _extract_x_audio(temp_video_path: str) -> bytes:
    """Own one FFmpeg child; failed settlement is never reported as a timeout alone."""
    command = ['ffmpeg', '-i', temp_video_path, '-f', 'wav', '-t', '3',
               '-ac', '1', '-ar', '44100', 'pipe:1']
    process = subprocess.Popen(command, stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    try:
        audio_data, _ = process.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        try:
            process.kill()
            # communicate bounds reader-thread joins and wait, and closes drained
            # pipes. Never manually close/join a potentially active Windows reader.
            process.communicate(timeout=5)
            if process.returncode is None:
                raise OSError("Owned FFmpeg child was not reaped")
        except (OSError, subprocess.TimeoutExpired) as cleanup_error:
            raise RuntimeError("Audio extraction timeout; child cleanup failed") from cleanup_error
        raise
    if process.returncode != 0 or len(audio_data) < 1000:
        raise BadRequest("No audio detected in X video or extraction failed")
    return audio_data


def _remove_x_video(temp_video_path: str, primary_error: Exception | None) -> None:
    """Retain a processing failure if removal of its owned temporary file fails."""
    try:
        if os.path.exists(temp_video_path):
            os.unlink(temp_video_path)
    except OSError as cleanup_error:
        if primary_error is not None:
            primary_error.add_note("Temporary video cleanup failed: " + type(cleanup_error).__name__)
            raise primary_error
        raise


def process_x_video_url(x_url: str) -> bytes:
    """
    Download X video and extract audio in-memory for acoustic analysis.

    Args:
        x_url: X (Twitter) post URL containing video

    Returns:
        WAV audio data as bytes

    Raises:
        BadRequest: If video processing fails or no audio detected
    """
    if not YT_DLP_AVAILABLE:
        raise BadRequest("X video processing not available - yt-dlp not installed")

    try:
        # yt-dlp options for in-memory processing
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'format': 'best[height<=720]',  # Limit video quality
            'outtmpl': '-',  # Output to stdout (pipe)
            'extract_flat': False,
        }

        # Download video to memory buffer
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract info first to validate URL
            try:
                info = ydl.extract_info(x_url, download=False)
                if not info or 'formats' not in info:
                    raise BadRequest("Invalid X post or no video content found")
            except Exception as e:
                raise BadRequest(f"Unable to access X video: {str(e)}")

            # Download video data to memory
            with io.BytesIO() as video_buffer:
                ydl_opts_download = ydl_opts.copy()
                ydl_opts_download['outtmpl'] = '-'

                # Use subprocess to pipe video data
                import tempfile
                import os

                # Create temporary file for video download
                with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_video:
                    temp_video_path = temp_video.name

                primary_error = None
                try:
                    # Download video to temp file (necessary for ffmpeg)
                    ydl_opts_temp = {
                        'quiet': True,
                        'no_warnings': True,
                        'format': 'best[height<=720]',
                        'outtmpl': temp_video_path,
                        'extract_flat': False,
                    }

                    with yt_dlp.YoutubeDL(ydl_opts_temp) as ydl_download:
                        ydl_download.download([x_url])

                    return _extract_x_audio(temp_video_path)
                except Exception as error:
                    primary_error = error
                    raise
                finally:
                    _remove_x_video(temp_video_path, primary_error)

    except subprocess.TimeoutExpired:
        raise BadRequest("Audio extraction timeout")
    except Exception as e:
        raise BadRequest(f"X video processing failed: {str(e)}")


def log_to_ethereum_testnet(results: dict):
    """
    Log SHA-256 hash of analysis results to Ethereum testnet for educational proof-of-existence.

    Args:
        results: Analysis results dictionary containing ethereum_hash
    """
    try:
        logger = get_ethereum_logger()
        tx_hash = logger.log_acoustic_analysis(results)

        # Update results with actual transaction hash
        results['ethereum_tx_hash'] = tx_hash

    except Exception as e:
        print(f"[WARNING] Ethereum logging failed (non-critical): {e}")
        results['ethereum_tx_hash'] = 'logging_failed'


def get_html_template() -> str:
    """Get the redesigned HTML template with simplified, user-friendly interface."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Acoustic Lab - Learn Acoustic Triangulation</title>

    <!-- Google Maps JavaScript API -->
    <script>
        // Google Maps API Key Configuration
        const GOOGLE_MAPS_API_KEY = 'YOUR_GOOGLE_MAPS_API_KEY';
        let googleMapsLoaded = false;
        let googleMapsError = false;
    </script>
    <script>
        function loadGoogleMaps() {
            if (GOOGLE_MAPS_API_KEY === 'YOUR_GOOGLE_MAPS_API_KEY') {
                showGoogleMapsError();
                return;
            }

            const script = document.createElement('script');
            script.src = `https://maps.googleapis.com/maps/api/js?key=${GOOGLE_MAPS_API_KEY}&libraries=places&callback=initMap`;
            script.async = true;
            script.defer = true;
            script.onerror = function() { showGoogleMapsError(); };
            document.head.appendChild(script);

            setTimeout(() => {
                if (!googleMapsLoaded && !googleMapsError) {
                    showGoogleMapsError();
                }
            }, 10000);
        }

        function showGoogleMapsError() {
            googleMapsError = true;
            const mapContainer = document.getElementById('map');
            if (mapContainer) {
                mapContainer.innerHTML = `
                    <div style="height: 100%; display: flex; align-items: center; justify-content: center; background: #f5f5f5; border-radius: 10px;">
                        <div style="text-align: center; padding: 20px;">
                            <div style="font-size: 48px; color: #666; margin-bottom: 10px;">[U+1F5FA]️</div>
                            <div style="color: #666; font-size: 14px;">Interactive map requires Google Maps API key</div>
                            <div style="color: #999; font-size: 12px; margin-top: 10px;">You can still use manual coordinates below</div>
                        </div>
                    </div>
                `;
            }
            // Enable coordinate input functionality
            document.addEventListener('DOMContentLoaded', () => {
                addInputEventListeners();
                updateCoordinatesDisplay();
            });
        }
    </script>

    <style>
        * {
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            margin: 0;
            padding: 0;
            min-height: 100vh;
        }

        .hero {
            background: rgba(255, 255, 255, 0.95);
            padding: 40px 20px;
            text-align: center;
            margin-bottom: 20px;
        }

        .hero h1 {
            font-size: 2.5rem;
            margin: 0 0 10px 0;
            background: linear-gradient(45deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .hero p {
            font-size: 1.2rem;
            color: #666;
            margin: 0;
            max-width: 600px;
            margin: 0 auto;
        }

        .container {
            max-width: 1000px;
            margin: 0 auto;
            padding: 0 20px;
        }

        .workflow {
            display: flex;
            justify-content: space-between;
            margin: 30px 0;
            position: relative;
        }

        .workflow::before {
            content: '';
            position: absolute;
            top: 25px;
            left: 0;
            right: 0;
            height: 2px;
            background: #ddd;
            z-index: 1;
        }

        .step {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            text-align: center;
            position: relative;
            z-index: 2;
            flex: 1;
            margin: 0 10px;
            border: 3px solid #e0e0e0;
        }

        .step.active {
            border-color: #667eea;
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
        }

        .step-number {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: #e0e0e0;
            color: #666;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            margin: 0 auto 15px;
            font-size: 18px;
        }

        .step.active .step-number {
            background: #667eea;
            color: white;
        }

        .step h3 {
            margin: 0 0 10px 0;
            color: #333;
            font-size: 1.2rem;
        }

        .step p {
            margin: 0;
            color: #666;
            font-size: 0.9rem;
        }

        .map-section {
            background: white;
            border-radius: 15px;
            padding: 25px;
            margin: 20px 0;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }

        .map-container {
            height: 350px;
            width: 100%;
            border-radius: 10px;
            margin: 15px 0;
            border: 2px solid #e0e0e0;
        }

        .coordinates-display {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            font-family: 'Courier New', monospace;
            font-size: 16px;
            font-weight: bold;
            color: #333;
            border: 1px solid #dee2e6;
        }

        .upload-section {
            background: white;
            border-radius: 15px;
            padding: 25px;
            margin: 20px 0;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }

        .upload-zone {
            border: 3px dashed #667eea;
            border-radius: 12px;
            padding: 40px 20px;
            text-align: center;
            background: #f8f9ff;
            transition: all 0.3s ease;
            cursor: pointer;
            margin: 20px 0;
        }

        .upload-zone:hover {
            border-color: #5a67d8;
            background: #f0f2ff;
        }

        .upload-zone.dragover {
            border-color: #00ff00;
            background: #f0fff0;
        }

        .upload-zone input[type="file"] {
            display: none;
        }

        .upload-zone .upload-icon {
            font-size: 48px;
            color: #667eea;
            margin-bottom: 10px;
        }

        .upload-zone h4 {
            margin: 0 0 10px 0;
            color: #333;
        }

        .upload-zone p {
            margin: 0;
            color: #666;
        }

        .x-url-section {
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
        }

        .x-url-section input[type="text"] {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 16px;
            margin-bottom: 10px;
        }

        .results-section {
            background: white;
            border-radius: 15px;
            padding: 25px;
            margin: 20px 0;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            min-height: 200px;
        }

        .results-section h3 {
            margin-top: 0;
            color: #333;
            text-align: center;
        }

        .result-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }

        .result-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            border: 1px solid #dee2e6;
        }

        .result-card .value {
            font-size: 24px;
            font-weight: bold;
            color: #667eea;
            margin: 10px 0;
        }

        .result-card .label {
            color: #666;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .btn {
            padding: 12px 24px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 500;
            transition: all 0.2s ease;
        }

        .btn:hover {
            background: #5a67d8;
            transform: translateY(-1px);
        }

        .btn:disabled {
            background: #a0aec0;
            cursor: not-allowed;
            transform: none;
        }

        .error {
            background: #fee;
            color: #c33;
            padding: 15px;
            border-radius: 8px;
            margin: 10px 0;
            border: 1px solid #fcc;
        }

        .loading {
            color: #ffa500;
            font-weight: bold;
        }

        .advanced-toggle {
            text-align: center;
            margin: 15px 0;
        }

        .advanced-toggle button {
            background: none;
            border: none;
            color: #667eea;
            cursor: pointer;
            text-decoration: underline;
            font-size: 14px;
        }

        .advanced-options {
            display: none;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
        }

        .manual-input-section {
            display: flex;
            gap: 10px;
            align-items: center;
            justify-content: center;
            flex-wrap: wrap;
        }

        .manual-input-section input[type="number"] {
            width: 120px;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }

        .manual-input-section label {
            display: block;
            margin-bottom: 5px;
            font-size: 12px;
            color: #666;
        }

        @media (max-width: 768px) {
            .workflow {
                flex-direction: column;
                gap: 20px;
            }

            .workflow::before {
                display: none;
            }

            .step {
                margin: 0;
            }

            .hero h1 {
                font-size: 2rem;
            }

            .result-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <!-- Hero Section -->
    <div class="hero">
        <h1>[TARGET] Acoustic Lab</h1>
        <p>Learn acoustic triangulation and audio fingerprinting through hands-on experimentation</p>
    </div>

    <div class="container">
        <!-- Workflow Visualization -->
        <div class="workflow">
            <div class="step active">
                <div class="step-number">1</div>
                <h3>Set Location</h3>
                <p>Click the map to choose where the audio was recorded</p>
            </div>
            <div class="step">
                <div class="step-number">2</div>
                <h3>Upload Audio</h3>
                <p>Drop a WAV file or paste an X video URL</p>
            </div>
            <div class="step">
                <div class="step-number">3</div>
                <h3>See Results</h3>
                <p>Watch the triangulation algorithm work</p>
            </div>
        </div>

        <!-- Map Section -->
        <div class="map-section">
            <h3 style="text-align: center; margin-bottom: 20px; color: #333;">[PIN] Step 1: Select Recording Location</h3>
            <div id="map" class="map-container"></div>

            <div class="coordinates-display" id="coordinatesDisplay">
                Selected Location: <span id="selectedCoords">Click on the map to select coordinates</span>
            </div>

            <div class="advanced-toggle">
                <button onclick="toggleAdvancedOptions()">Advanced Options [U+25BC]</button>
            </div>

            <div class="advanced-options" id="advancedOptions">
                <h4 style="margin-top: 0; color: #333;">Manual Coordinate Entry</h4>

                <!-- Google Earth/Maps URL Input -->
                <div style="margin-bottom: 15px;">
                    <label for="earthUrlInput" style="display: block; margin-bottom: 5px; color: #333; font-weight: bold;">
                        Google Earth/Maps URL:
                    </label>
                    <input type="text" id="earthUrlInput" placeholder="Paste Google Earth or Google Maps URL here..."
                           style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; margin-bottom: 5px;">
                    <button class="btn" onclick="parseGoogleEarthUrl()" style="padding: 5px 10px; font-size: 12px;">Extract Coordinates</button>
                </div>

                <!-- Manual Coordinate Input -->
                <div class="manual-input-section">
                    <div>
                        <label for="latInput">Latitude:</label>
                        <input type="number" id="latInput" step="0.0001" min="-90" max="90" value="40.7649">
                    </div>
                    <div>
                        <label for="lngInput">Longitude:</label>
                        <input type="number" id="lngInput" step="0.0001" min="-180" max="180" value="-111.8421">
                    </div>
                    <div>
                        <button class="btn" onclick="updateLocationFromInputs()" style="padding: 8px 12px; font-size: 14px;">Update Map</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Upload Section -->
        <div class="upload-section">
            <h3 style="text-align: center; margin-bottom: 20px; color: #333;">[U+1F3B5] Step 2: Upload Audio for Analysis</h3>

            <div class="upload-zone" id="uploadZone">
                <input type="file" id="audioFile" accept=".wav" />
                <label for="audioFile">
                    <div class="upload-icon">[U+1F3B5]</div>
                    <h4>Drop WAV File Here</h4>
                    <p>Or click to browse your computer</p>
                    <p style="font-size: 12px; color: #888;">Synthetic audio files only - for educational purposes</p>
                </label>
            </div>

            <div class="x-url-section">
                <h4 style="margin-bottom: 10px; color: #333;">Alternative: Analyze X (Twitter) Video</h4>
                <input type="text" id="xurl" placeholder="Paste X video URL here (https://x.com/...)" />
                <button class="btn" onclick="submitX()" id="xButton" style="width: 100%; margin-top: 10px;">Analyze X Video</button>
            </div>
        </div>

        <!-- Results Section -->
        <div class="results-section" id="resultsSection">
            <h3>[SEARCH] Step 3: Analysis Results</h3>
            <div id="results" style="display: none;"></div>
            <div id="error" class="error" style="display: none;"></div>
            <div style="text-align: center; color: #999; margin-top: 20px;">
                <p>Upload audio above to see triangulation results</p>
                <p style="font-size: 14px;">The algorithm will calculate the sound source location using your selected coordinates</p>
            </div>
        </div>
    </div>

    <script>
        // Global variables for map and coordinates
        let map;
        let selectedLat = 40.7649;  // Default: Salt Lake City
        let selectedLng = -111.8421;
        let marker;

        // Initialize map when Google Maps API loads
        window.initMap = function() {
            try {
                googleMapsLoaded = true;

                // Initialize Google Map centered on Utah
                const utahCenter = { lat: selectedLat, lng: selectedLng };

                map = new google.maps.Map(document.getElementById('map'), {
                    zoom: 10,
                    center: utahCenter,
                    mapTypeId: google.maps.MapTypeId.ROADMAP,
                    styles: [
                        {
                            featureType: "poi",
                            elementType: "labels",
                            stylers: [{ visibility: "off" }]
                        }
                    ]
                });

                // Add click handler for coordinate selection
                map.addListener('click', function(event) {
                    selectedLat = event.latLng.lat();
                    selectedLng = event.latLng.lng();
                    updateMarker();
                    updateCoordinatesDisplay();
                });

                // Add initial marker
                updateMarker();

                // Add some educational markers for Salt Lake City area
                addEducationalMarkers();

                // Update coordinates display
                updateCoordinatesDisplay();

                // Add keyboard and input validation support
                addInputEventListeners();

            } catch (error) {
                console.error('Error initializing Google Maps:', error);
                googleMapsError = true;
                showGoogleMapsError('Error initializing Google Maps: ' + error.message);
            }
        }

        // Load Google Maps when page loads
        document.addEventListener('DOMContentLoaded', function() {
            loadGoogleMaps();
        });

        function addInputEventListeners() {
            // Add Enter key support to coordinate input fields
            document.getElementById('latInput').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    updateLocationFromInputs();
                }
            });

            document.getElementById('lngInput').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    updateLocationFromInputs();
                }
            });

            // Add Enter key support to Google Earth URL input
            document.getElementById('earthUrlInput').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    parseGoogleEarthUrl();
                }
            });

            // Update coordinates when inputs change (real-time feedback)
            document.getElementById('latInput').addEventListener('input', function() {
                const lat = parseFloat(this.value);
                if (!isNaN(lat) && lat >= -90 && lat <= 90) {
                    this.style.borderColor = '#00ff00'; // Green for valid
                } else {
                    this.style.borderColor = '#ff6666'; // Red for invalid
                }
            });

            document.getElementById('lngInput').addEventListener('input', function() {
                const lng = parseFloat(this.value);
                if (!isNaN(lng) && lng >= -180 && lng <= 180) {
                    this.style.borderColor = '#00ff00'; // Green for valid
                } else {
                    this.style.borderColor = '#ff6666'; // Red for invalid
                }
            });
        }

        function updateMarker() {
            // Remove existing marker
            if (marker) {
                marker.setMap(null);
            }

            // Add new marker
            marker = new google.maps.Marker({
                position: { lat: selectedLat, lng: selectedLng },
                map: map,
                title: `Selected Location: ${selectedLat.toFixed(4)}, ${selectedLng.toFixed(4)}`,
                animation: google.maps.Animation.DROP
            });

            // Add info window
            const infoWindow = new google.maps.InfoWindow({
                content: `<div style="max-width: 200px;">
                    <strong>Selected Location</strong><br>
                    Latitude: ${selectedLat.toFixed(4)}<br>
                    Longitude: ${selectedLng.toFixed(4)}<br>
                    <small>Click map to change location</small>
                </div>`
            });

            marker.addListener('click', function() {
                infoWindow.open(map, marker, encoding="utf-8");
            });

            // Auto-open info window
            setTimeout(() => infoWindow.open(map, marker, encoding="utf-8"), 1000);
        }

        function updateCoordinatesDisplay() {
            const coordsElement = document.getElementById('selectedCoords');
            coordsElement.textContent = `${selectedLat.toFixed(4)}, ${selectedLng.toFixed(4)}`;

            // Also update the input fields
            document.getElementById('latInput').value = selectedLat.toFixed(4);
            document.getElementById('lngInput').value = selectedLng.toFixed(4);
        }

        function parseGoogleEarthUrl() {
            const urlInput = document.getElementById('earthUrlInput');
            const url = urlInput.value.trim();

            if (!url) {
                alert('Please enter a Google Earth or Google Maps URL');
                return;
            }

            // Check if it's a supported URL type
            const isGoogleEarth = url.includes('earth.google.com');
            const isGoogleMaps = url.includes('maps.google.com') || url.includes('google.com/maps');

            if (!isGoogleEarth && !isGoogleMaps) {
                alert('Please enter a valid Google Earth or Google Maps URL');
                return;
            }

            try {
                // Find the @ symbol which precedes the coordinates
                const atIndex = url.indexOf('@');
                if (atIndex === -1) {
                    alert('Invalid URL: No coordinates found after @ symbol');
                    return;
                }

                // Extract the coordinate part after @
                const coordPart = url.substring(atIndex + 1);

                // Split by comma and take first two values (lat,lng)
                // For both Google Earth and Google Maps, coordinates are the first two values
                const coordParts = coordPart.split(',').slice(0, 2);
                if (coordParts.length < 2) {
                    alert('Invalid URL: Could not parse coordinates');
                    return;
                }

                const newLat = parseFloat(coordParts[0]);
                const newLng = parseFloat(coordParts[1]);

                // Validate coordinates
                if (isNaN(newLat) || isNaN(newLng)) {
                    alert('Invalid coordinates extracted from URL');
                    return;
                }

                if (newLat < -90 || newLat > 90) {
                    alert('Latitude must be between -90 and 90 degrees');
                    return;
                }

                if (newLng < -180 || newLng > 180) {
                    alert('Longitude must be between -180 and 180 degrees');
                    return;
                }

                // Update coordinates
                selectedLat = newLat;
                selectedLng = newLng;

                // Update map if available
                if (googleMapsLoaded && map) {
                    const newCenter = { lat: selectedLat, lng: selectedLng };
                    map.setCenter(newCenter);
                    updateMarker();
                    // Pan to the new location smoothly
                    map.panTo(newCenter);
                }

                // Always update coordinate display
                updateCoordinatesDisplay();

                // Clear the URL input to show success
                urlInput.style.borderColor = '#00ff00';
                setTimeout(() => {
                    urlInput.style.borderColor = '#777';
                }, 2000);

                console.log(`Successfully parsed Google Earth coordinates: ${newLat}, ${newLng}`);

            } catch (error) {
                alert('Error parsing Google Earth URL: ' + error.message);
                urlInput.style.borderColor = '#ff6666';
                setTimeout(() => {
                    urlInput.style.borderColor = '#777';
                }, 2000);
            }
        }

        function updateLocationFromInputs() {
            const latInput = document.getElementById('latInput');
            const lngInput = document.getElementById('lngInput');

            const newLat = parseFloat(latInput.value);
            const newLng = parseFloat(lngInput.value);

            // Validate coordinates
            if (isNaN(newLat) || isNaN(newLng)) {
                alert('Please enter valid numbers for latitude and longitude');
                return;
            }

            if (newLat < -90 || newLat > 90) {
                alert('Latitude must be between -90 and 90 degrees');
                return;
            }

            if (newLng < -180 || newLng > 180) {
                alert('Longitude must be between -180 and 180 degrees');
                return;
            }

            // Update coordinates
            selectedLat = newLat;
            selectedLng = newLng;

            // Update map if available
            if (googleMapsLoaded && map) {
                const newCenter = { lat: selectedLat, lng: selectedLng };
                map.setCenter(newCenter);
                updateMarker();
                // Pan to the new location smoothly
                map.panTo(newCenter);
            }

            // Always update coordinate display
            updateCoordinatesDisplay();
        }

        function resetLocation() {
            selectedLat = 40.7649;  // Salt Lake City
            selectedLng = -111.8421;

            const newCenter = { lat: selectedLat, lng: selectedLng };
            map.setCenter(newCenter);
            map.setZoom(10);
            updateMarker();
            updateCoordinatesDisplay();
        }


        function addEducationalMarkers() {
            // Add some landmarks to help with education
            const landmarks = [
                {
                    position: { lat: 40.7608, lng: -111.8910 },
                    title: "Temple Square",
                    description: "Historic religious site in downtown Salt Lake City"
                },
                {
                    position: { lat: 40.7649, lng: -111.8421 },
                    title: "Salt Lake City Center",
                    description: "Downtown Salt Lake City business district"
                },
                {
                    position: { lat: 40.7784, lng: -111.9307 },
                    title: "University of Utah",
                    description: "Major research university in Salt Lake City"
                }
            ];

            landmarks.forEach(function(landmark) {
                const marker = new google.maps.Marker({
                    position: landmark.position,
                    map: map,
                    title: landmark.title,
                    icon: {
                        url: 'https://maps.google.com/mapfiles/ms/icons/blue-dot.png',
                        scaledSize: new google.maps.Size(32, 32)
                    }
                });

                const infoWindow = new google.maps.InfoWindow({
                    content: `<div>
                        <strong>${landmark.title}</strong><br>
                        <small>${landmark.description}</small><br>
                        <em>Educational landmark</em>
                    </div>`
                });

                marker.addListener('click', function() {
                    infoWindow.open(map, marker, encoding="utf-8");
                });
            });
        }

        // File upload functionality
        const uploadZone = document.getElementById('uploadZone');
        const audioFile = document.getElementById('audioFile');
        const resultsDiv = document.getElementById('results');
        const errorDiv = document.getElementById('error');

        // Drag and drop functionality
        uploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadZone.classList.add('dragover');
        });

        uploadZone.addEventListener('dragleave', () => {
            uploadZone.classList.remove('dragover');
        });

        uploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadZone.classList.remove('dragover');

            const files = e.dataTransfer.files;
            if (files.length > 0 && files[0].name.endsWith('.wav')) {
                audioFile.files = files;
                processFile(files[0]);
            } else {
                showError('Please drop a valid WAV file');
            }
        });

        // File selection
        audioFile.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                processFile(e.target.files[0]);
            }
        });

        function processFile(file) {
            // Update workflow to show step 2 is active
            document.querySelectorAll('.step').forEach(step => step.classList.remove('active'));
            document.querySelectorAll('.step')[1].classList.add('active'); // Mark step 2 as active

            showLoading('Processing acoustic analysis...');

            // Use selected coordinates from map
            const metadata = {
                gps: {
                    latitude: selectedLat,
                    longitude: selectedLng
                },
                timestamp: new Date().toISOString(),
                source: 'direct_upload'
            };

            // Create form data
            const formData = new FormData();
            formData.append('audio', file);
            formData.append('metadata', JSON.stringify(metadata));

            // Send to server
            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showError(data.error);
                } else {
                    showResults(data);
                }
            })
            .catch(error => {
                showError('Network error: ' + error.message);
            });
        }

        function showLoading(message) {
            resultsDiv.style.display = 'none';
            errorDiv.style.display = 'block';
            errorDiv.className = 'loading';
            errorDiv.textContent = message;
        }

        function showError(message) {
            resultsDiv.style.display = 'none';
            errorDiv.style.display = 'block';
            errorDiv.className = 'error';
            errorDiv.textContent = message;
        }

        function submitX() {
            const url = document.getElementById('xurl').value;
            if (!url.includes('x.com') && !url.includes('twitter.com')) {
                showError('Invalid X link - must be an X.com or Twitter.com URL');
                return;
            }

            // Update workflow to show step 2 is active
            document.querySelectorAll('.step').forEach(step => step.classList.remove('active'));
            document.querySelectorAll('.step')[1].classList.add('active'); // Mark step 2 as active

            // Disable button during processing
            const button = document.getElementById('xButton');
            button.disabled = true;
            button.textContent = 'Processing...';

            showLoading('Downloading and analyzing X video audio...');

            // Use selected coordinates from map
            const metadata = {
                gps: {
                    latitude: selectedLat,
                    longitude: selectedLng
                },
                timestamp: new Date().toISOString(),
                source: 'x_video'
            };

            // Create form data with URL as file parameter
            const formData = new FormData();
            formData.append('x_url', url);
            formData.append('metadata', JSON.stringify(metadata));

            // Send to server
            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                // Re-enable button
                button.disabled = false;
                button.textContent = 'Analyze X Video';

                if (data.error) {
                    showError(data.error);
                } else {
                    showResults(data);
                }
            })
            .catch(error => {
                // Re-enable button
                button.disabled = false;
                button.textContent = 'Analyze X Video';
                showError('Network error: ' + error.message);
            });
        }

        function toggleAdvancedOptions() {
            const advancedOptions = document.getElementById('advancedOptions');
            const toggleButton = event.target;

            if (advancedOptions.style.display === 'none' || advancedOptions.style.display === '') {
                advancedOptions.style.display = 'block';
                toggleButton.textContent = 'Advanced Options [U+25B2]';
            } else {
                advancedOptions.style.display = 'none';
                toggleButton.textContent = 'Advanced Options [U+25BC]';
            }
        }

        function showResults(data) {
            errorDiv.style.display = 'none';
            resultsDiv.style.display = 'block';

            // Update workflow to show completion
            document.querySelectorAll('.step').forEach(step => step.classList.remove('active'));
            document.querySelectorAll('.step')[2].classList.add('active'); // Mark step 3 as active

            resultsDiv.innerHTML = `
                <div class="result-grid">
                    <div class="result-card">
                        <div class="value">${data.sound_type}</div>
                        <div class="label">Sound Type</div>
                    </div>
                    <div class="result-card">
                        <div class="value">${(data.confidence * 100).toFixed(1)}%</div>
                        <div class="label">Confidence</div>
                    </div>
                    <div class="result-card">
                        <div class="value">${data.triangulation_data.sensors_used}</div>
                        <div class="label">Sensors Used</div>
                    </div>
                    <div class="result-card">
                        <div class="value">±${data.triangulation_data.error_estimate}m</div>
                        <div class="label">Accuracy</div>
                    </div>
                </div>

                <div style="margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 8px;">
                    <h4 style="margin-top: 0; color: #333;">[DATA] Detailed Analysis</h4>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-top: 15px;">
                        <div>
                            <strong>Recording Location:</strong><br>
                            ${selectedLat.toFixed(4)}, ${selectedLng.toFixed(4)}
                        </div>
                        <div>
                            <strong>Calculated Sound Source:</strong><br>
                            ${data.location[0].toFixed(4)}, ${data.location[1].toFixed(4)}
                        </div>
                        <div>
                            <strong>Audio Source:</strong><br>
                            ${data.source || 'Direct upload'}
                        </div>
                        <div>
                            <strong>Blockchain Hash:</strong><br>
                            <small style="font-family: monospace;">${data.ethereum_hash.substring(0, 16)}...</small>
                        </div>
                    </div>
                </div>

                <div style="margin-top: 20px; padding: 15px; background: #e8f4fd; border-radius: 8px; border-left: 4px solid #667eea;">
                    <strong>[GRADUATE] Educational Insight:</strong> The triangulation algorithm calculated the sound source location
                    using time-of-arrival differences from multiple sensors. This demonstrates how mathematics can precisely
                    locate audio events in physical space using geometric principles.
                </div>
            `;

            // Scroll to results
            document.getElementById('resultsSection').scrollIntoView({ behavior: 'smooth' });
        }
    </script>
</body>
</html>
    """


# Development server
if __name__ == '__main__':
    app = create_app()
    print("[EDUCATION] Acoustic Lab Educational Server Starting...")
    print("[ACCESS] Educational Access: Restricted to Utah state")
    print("[WEB] Open http://localhost:5000 in your browser")
    app.run(debug=True, host='0.0.0.0', port=5000)
