# Acoustic Lab - Interface Documentation (WSP 11)

## Public API Definition

### Web Application Interface

#### `create_app() -> Flask`
Creates and configures the Flask web application instance.

**Parameters**: None

**Returns**: Configured Flask application object

**Usage**:
```python
from modules.platform_integration.acoustic_lab.src.web_app import create_app
app = create_app()
app.run()
```

#### `/upload (POST)`
Process uploaded audio file or X video URL for acoustic analysis.

**Content-Type**: `multipart/form-data`

**Input Methods**:

**File Upload:**
- `audio`: WAV file (required for file upload)
- `metadata`: JSON string with GPS coordinates and timestamp

**X URL Processing:**
- `x_url`: X/Twitter post URL string (required for X processing)
- `metadata`: JSON string with GPS coordinates and timestamp

**Metadata Format**:
```json
{
  "gps": {
    "latitude": 40.7649,
    "longitude": -111.8421
  },
  "timestamp": "2025-10-02T12:00:00Z",
  "source": "x_video|direct_upload"
}
```

**Response**: JSON analysis results or error message

**Success Response (200)**:
```json
{
  "location": [40.7649, -111.8421],
  "sound_type": "Tone A",
  "confidence": 0.92,
  "triangulation_data": {
    "sensors_used": 3,
    "error_estimate": 5.2
  },
  "ethereum_hash": "a665a459...",
  "source": "x_video"
}
```

**Error Responses**:
- `400`: Invalid file format, missing audio, or invalid X URL
- `403`: Geographic access restriction (IP geofencing)
- `413`: Multipart request exceeds Werkzeug's parsing limits
- `500`: Internal processing error

Werkzeug 3.1.9 limits each multipart non-file field to 500,000 bytes by default.
The upload handler preserves `RequestEntityTooLarge` as a JSON error with HTTP
413 before audio processing or Ethereum logging. This is not a total file-upload
size limit; the existing application `MAX_CONTENT_LENGTH` setting is unchanged.

#### `/health (GET)`
Service health monitoring endpoint.

**Response**: JSON health status

**Response Format**:
```json
{
  "status": "healthy",
  "service": "Acoustic Lab",
  "version": "1.0.0",
  "stats": {
    "total_processed": 150,
    "success_rate": 0.98,
    "avg_processing_time": 2.3
  }
}
```

### Core Processing Classes

#### `AcousticProcessor`
Main audio processing engine for fingerprinting and analysis.

##### Methods:

**`process_audio(file_data: bytes, metadata: dict) -> dict`**
Process uploaded audio file and return analysis results.

**Parameters**:
- `file_data`: Raw WAV file bytes
- `metadata`: Dictionary containing GPS coordinates and timestamp

**Returns**: Analysis results dictionary with location, sound type, and confidence

**Raises**:
- `AudioValidationError`: Invalid audio format or missing required peaks
- `GPSValidationError`: Missing or invalid GPS coordinates

#### `AudioLibrary`
Manages the synthetic audio fingerprint database.

##### Methods:

**`match_fingerprint(mfcc_features: np.ndarray) -> tuple[str, float]`**
Match extracted MFCC features against known audio signatures.

**Parameters**:
- `mfcc_features`: MFCC feature array from audio analysis

**Returns**: Tuple of (sound_type, confidence_score)

#### `TriangulationEngine`
Calculates sound source location from multiple sensor positions.

##### Methods:

**`calculate_location(sensor_positions: list, time_delays: list) -> tuple[float, float]`**
Compute triangulated location using time-of-arrival differences.

**Parameters**:
- `sensor_positions`: List of (lat, lon) tuples for sensor locations
- `time_delays`: List of time delays from each sensor to sound detection

**Returns**: Tuple of (latitude, longitude) for calculated sound source

## API Endpoints

### POST /upload
Upload and process synthetic audio file for acoustic analysis.

**Request**:
- Content-Type: multipart/form-data
- Body: WAV file + metadata JSON

**Response**:
```json
{
  "location": [40.7649, -111.8421],
  "sound_type": "Tone A",
  "confidence": 0.84,
  "triangulation_data": {
    "sensors_used": 3,
    "time_delays": [0.0, 0.012, 0.025],
    "error_estimate": 15.2
  },
  "ethereum_hash": "0x1234...abcd"
}
```

**Status Codes**:
- 200: Success
- 400: Invalid audio or missing GPS
- 403: IP geofencing violation
- 413: Multipart parsing limit exceeded
- 500: Processing error

## Error Handling

### AudioValidationError
Raised when uploaded audio doesn't meet requirements.
- Missing sharp peaks (>1kHz)
- Invalid WAV format
- Audio too short for analysis

### GPSValidationError
Raised when GPS metadata is missing or invalid.
- Missing latitude/longitude
- Coordinates outside valid range
- Missing timestamp

### IPGeofencingError
Raised when request originates outside allowed geographic area.
- Currently restricted to Utah state for educational purposes

## Data Structures

### Audio Metadata Format
```json
{
  "gps": {
    "latitude": 40.7649,
    "longitude": -111.8421
  },
  "timestamp": "2025-10-02T14:30:00Z",
  "sensor_id": "sensor_001"
}
```

### Analysis Results Format
```json
{
  "location": [float, float],
  "sound_type": "string",
  "confidence": float,
  "triangulation_data": {
    "sensors_used": int,
    "time_delays": [float, ...],
    "error_estimate": float
  },
  "ethereum_hash": "string"
}
```

## Performance Characteristics

- **Audio Processing**: <2 seconds for 10-second WAV files
- **Fingerprint Matching**: <0.5 seconds against 3-tone library
- **Triangulation**: <0.1 seconds for 3-sensor calculations
- **Memory Usage**: <50MB per request (in-memory processing only)

## Security Considerations

- No file system persistence
- Automatic memory cleanup after processing
- IP-based geographic restrictions
- Synthetic data only (no real audio recordings)
- Ethereum testnet logging for educational verification

## Testing

Unit tests available in `tests/` directory:
- `test_acoustic_processor.py`: Audio processing validation
- `test_triangulation_engine.py`: Location calculation verification
- `test_audio_library.py`: Fingerprint matching accuracy
- `test_web_app.py`: API endpoint functionality

Run tests with: `python -m pytest tests/`

---

**Interface documented per WSP 11 standards**
**Last updated: 2025-10-02**
