# [U+1F300] Acoustic Lab - Local Development Installation Guide

**WSP Compliance**: WSP 49 (Module Structure), WSP 71 (Secrets Management)
**Educational Platform**: Teaching Acoustic Triangulation & Audio Analysis

## [TARGET] Quick Start (5 Minutes)

### Prerequisites
- **Python 3.11+** (required for audio processing)
- **Git** (for cloning)
- **Modern browser** (Chrome/Firefox recommended)
- **1GB+ RAM** available

### One-Command Install & Run
```bash
# Clone and navigate to the module
cd modules/platform_integration/acoustic_lab

# Run the complete setup script (coming soon) OR manual setup:
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m src.web_app
```

**That's it!** Access at: http://localhost:5000

## [CLIPBOARD] Detailed Installation

### Step 1: Verify Python Version
```bash
python --version  # Should be 3.11 or higher
```
**Troubleshooting**: If you have multiple Python versions, use `python3.11` instead of `python`

### Step 2: Install Dependencies
```bash
# Navigate to the acoustic_lab module
cd modules/platform_integration/acoustic_lab

# Install Python packages (may take 2-5 minutes)
pip install -r requirements.txt
```

**What gets installed:**
- **Flask** - Web framework
- **Librosa** - Audio processing (MFCC fingerprinting)
- **setuptools 81.0.0** - Runtime `pkg_resources` provider for Librosa 0.10.1
- **NumPy** - Mathematical computations
- **SciPy** - Advanced mathematics
- **Web3.py** - Ethereum integration
- **Pillow** - Image processing
- **Requests** - HTTP client for IP geofencing

### Dependency qualification (2026-10-21)

`Pillow==13.0.0` addresses [GHSA-8g5g-8vmr-9782 / CVE-2026-112403](https://github.com/advisories/GHSA-8g5g-8vmr-9782). Pillow 13 requires Python 3.11+, matching this module's declared minimum. Qualification ran on Windows AMD64 CPython 3.12.10; Linux deployment and Python 3.11 execution remain unverified.

Keep `setuptools==81.0.0` in the runtime requirements while Librosa is pinned to 0.10.1. A fresh requirements-only environment previously failed application startup because Librosa imports `pkg_resources`; [setuptools 82 removed that API](https://setuptools.pypa.io/en/latest/history.html#v82-0-0). The existing deployment bootstrap installs setuptools before the requirements file. Install the full requirements afterward to apply the compatible pin, and do not independently upgrade setuptools without qualifying Librosa's replacement API.

This is a temporary compatibility pin. [Setuptools 84.1 release notes](https://setuptools.pypa.io/en/latest/history.html#v84-1-0) describe later security hardening of legacy archive extraction and egg installation that 81.0.0 lacks. Acoustic Lab does not call those APIs, and Librosa uses `pkg_resources.resource_filename` for installed package data; that source review is not proof that the environment is free of vulnerabilities. Follow-up qualification must retire the `pkg_resources` dependency and this older provider.

Full dependency resolution, installation, and `pip check` passed. Network-denied local checks passed for application creation, `/`, `/health`, and three invalid-upload cases. Seven generated-image checks passed for Pillow codecs, resizing, invalid input, and the NumPy bridge. These are package checks: no Python image adapter exists in the application. No successful audio upload, Ethereum RPC, X download, live service, or deployment was exercised.

The unchanged 15-test unit suite has identical results with Pillow 12.3.0 and 13.0.0 when both environments include setuptools 81.0.0: 11 pass and four fail under pytest; native unittest classifies the same four as two failures and two errors. Remaining cases are an ISO timestamp used in numeric triangulation, a stale index-page literal, a multipart bytes fixture rejected as a missing file, and a geolocation mock raising plain `Exception`. No tests were changed or weakened. Pytest used the repository's `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` convention because these unittest-based files need no Web3 plugin; normal autoload separately fails on Web3's `ContractName` import from `eth_typing`. Full application validation remains incomplete. See [ModLog](./ModLog.md) for source and evidence bindings.

### Step 3: Run the Application
```bash
# Development mode (auto-reload on changes)
python -m src.web_app

# OR run directly
python src/web_app.py
```

### Step 4: Verify Installation
Open your browser and go to: **http://localhost:5000**

You should see the Acoustic Lab educational interface with:

- **[TARGET] Hero Section**: Clear value proposition and branding
- **[CLIPBOARD] Step-by-Step Workflow**: Visual progress indicator (3 steps)
- **[U+1F5FA]️ Interactive Map**: Click anywhere to select recording location
- **[U+1F4C1] Drag & Drop Upload**: Simple file upload with visual feedback
- **[DATA] Prominent Results**: Card-based display of analysis results
- **[U+1F4F1] Mobile Responsive**: Works on all device sizes
- **[ART] Modern Design**: Clean, professional interface

**Interface Workflow:**
1. **Set Location** -> Click map or use advanced options
2. **Upload Audio** -> Drag file or paste X video URL
3. **See Results** -> View triangulation analysis

**Quick Test Command**:
```bash
# Test that X video upload works (no more 403 errors)
python test_x_upload.py
# Expected: "[OK] IP geofencing fix is working (no 403 error)"
```

### Step 5: How to Use Manual Coordinate Input

The Acoustic Lab now supports **three ways to select locations**:

#### Method 1: Google Earth/Maps URL (Fastest)
1. Open Google Earth or Google Maps and navigate to your desired location
2. Copy the URL from the address bar
3. Paste it in the "Google Earth/Maps URL" field in Step 1
4. Click "Extract Coordinates" (or press Enter)
5. The coordinates will be automatically extracted and displayed
6. If Google Maps is enabled, the map will center on the location
7. Proceed to upload audio in Step 2

**Example URLs:**
```
Google Earth: https://earth.google.com/web/@40.2767739,-111.71327038,1402.66806842a
Google Maps:  https://www.google.com/maps/@40.2776229,-111.7138613,219m/data=!3m1!1e3
```

#### Method 2: Click on the Map (Easiest)
1. Click anywhere on the Google Map in Step 1
2. Watch the coordinates update automatically
3. Proceed to upload audio in Step 2

#### Method 3: Manual Coordinate Entry
1. Enter latitude and longitude in the input fields
2. Press Enter or click "Update Map" to see the location on the map
3. Green borders = valid coordinates, Red borders = invalid coordinates
4. Proceed to upload audio in Step 2

**Valid Ranges:**
- Latitude: -90 to +90 degrees
- Longitude: -180 to +180 degrees

**Example Coordinates:**
- Salt Lake City: 40.7649, -111.8421
- New York City: 40.7128, -74.0060
- London: 51.5074, -0.1278

### Step 6: Configure Google Maps (Optional but Recommended)

The application works without Google Maps, but with it you'll get an interactive map interface.

#### **Without Google Maps API Key:**
- Shows a helpful setup message in the map area
- Manual coordinate input and Google Earth URL parsing still work perfectly
- All acoustic analysis functionality is available

#### **With Google Maps API Key:**
- Interactive clickable map with satellite imagery
- Visual markers and landmarks
- Enhanced user experience

#### **Setup Instructions:**

1. **Get Google Maps API Key**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/google/maps-apis)
   - Create a new project or select existing
   - Enable "Maps JavaScript API"
   - Create credentials (API Key)
   - **Important**: Restrict the key to your domain for security:
     - In API key settings, add "Application restrictions" -> "HTTP referrers"
     - Add your domain (e.g., `localhost`, `yourdomain.com`)

2. **Update the API Key**:
   - Open `src/web_app.py`
   - Find: `const GOOGLE_MAPS_API_KEY = 'YOUR_GOOGLE_MAPS_API_KEY';`
   - Replace with your actual API key from Google Cloud Console

3. **Restart the Application**:
   - Stop the server (Ctrl+C)
   - Restart: `python -m src.web_app`
   - The map should now load properly

**Troubleshooting:**
- If you see "Google Maps API key not configured", check that you replaced the placeholder
- If you see "Failed to load Google Maps", check your internet connection and API key restrictions
- The coordinate input fields work regardless of map status

### Step 7: Install All Dependencies

Make sure all Python dependencies are installed:

```bash
cd modules/platform_integration/acoustic_lab
pip install --user -r requirements.txt
```

**Important**: The `yt-dlp` package is required for X video processing. If you see "X video processing not available - yt-dlp not installed", run:

```bash
pip install --user yt-dlp==2024.3.10
```

### Step 8: Test with Sample Audio
The application comes with synthetic audio generation. Test both file upload and X video processing:

1. **File Upload Test**:
   - **Using Audacity** (free audio editor):
     - Generate -> Tone -> Sine, 2000 Hz, 0.5 seconds
     - File -> Export -> Export as WAV
     - Save as `test_tone.wav`
   - **Upload to Acoustic Lab**:
     - Drag and drop the WAV file
     - Add GPS coordinates (e.g., 40.7649, -111.8421 for Utah demo)
     - Click "Analyze Audio"

2. **X Video Test**:
   - Find an X (Twitter) post with a video
   - Copy the URL (e.g., https://x.com/username/status/123456789)
   - Paste URL in the "X Video URL" field
   - Add GPS coordinates
   - Click "Process X Video"

**Expected Result**: Detection of "Tone A" with triangulation location and Ethereum hash for both upload methods

## [U+1F9EA] Testing & Validation

### Run Comprehensive Tests
```bash
# Run all Phase 1 functionality tests
python scripts/test_phase1.py
```

**Expected Output:**
```
[CELEBRATE] ALL TESTS PASSED!
[OK] Acoustic Lab Phase 1 implementation is fully functional
[OK] Ready for educational deployment and acoustic learning
```

### Manual Testing Checklist
- [ ] Application starts without errors
- [ ] Health endpoint works: http://localhost:5000/health
- [ ] File upload processes WAV files
- [ ] X video URL processing works
- [ ] IP geofencing allows Utah access
- [ ] Results show triangulation coordinates
- [ ] Ethereum proof-of-existence generates

## [U+1F41B] Troubleshooting

### "Module 'librosa' not found"
```bash
pip install librosa==0.10.1
# On some systems you may need:
# pip install librosa --no-deps
# pip install numpy scipy
```

### "Port 5000 already in use"
```bash
# Use a different port
python -c "from src.web_app import create_app; app = create_app(); app.run(port=5001)"
```

### "No valid audio peak detected"
- Ensure your WAV file contains a clear tone >1kHz
- Use Audacity to generate a pure sine wave at 2000 Hz
- Check file format (must be WAV, not MP3)

### "IP geofencing violation"
- The demo restricts to Utah state for educational purposes
- **Local development**: 127.0.0.1/localhost is automatically allowed for testing [OK]
- **Production**: Only Utah IPs allowed (educational/demo restriction)
- **VPN option**: Use a VPN set to Utah for testing from other locations

### "400 Bad Request: X video processing not available - yt-dlp not installed"
- **Issue**: yt-dlp dependency not installed
- **Solution**: Install yt-dlp package
- **Command**: `pip install --user yt-dlp==2024.3.10`
- **Status**: [OK] Fixed after installing dependencies

### "403 Forbidden on X video upload" (FIXED)
- **Issue**: IP geofencing was blocking localhost access
- **Solution**: Added localhost bypass for development
- **Status**: [OK] Fixed - X video uploads now work from localhost
- **Test**: Run `python test_x_upload.py` to verify

### "Blockchain connection failed"
- Phase 1 uses simulated Ethereum logging
- This is expected and the application falls back gracefully
- Real blockchain integration comes in Phase 3

## [U+1F3D7]️ Development Setup

### Virtual Environment (Recommended)
```bash
# Create virtual environment
python -m venv acoustic_lab_env

# Activate (Windows)
acoustic_lab_env\Scripts\activate

# Activate (Linux/Mac)
source acoustic_lab_env/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run application
python -m src.web_app
```

### IDE Setup
- **PyCharm/VS Code**: Open the `modules/platform_integration/acoustic_lab` folder
- **Debugging**: Set breakpoint in `src/web_app.py` `upload_audio()` function
- **Testing**: Run `scripts/test_phase1.py` for full validation

### Code Structure
```
modules/platform_integration/acoustic_lab/
+-- src/                    # Core application code
[U+2502]   +-- web_app.py         # Flask application
[U+2502]   +-- acoustic_processor.py # Audio analysis engine
[U+2502]   +-- audio_library.py   # Synthetic tone database
[U+2502]   +-- triangulation_engine.py # Location calculation
[U+2502]   +-- ethereum_logger.py # Blockchain proof
+-- scripts/               # Deployment and testing
+-- tests/                 # Test suite
+-- docs/                  # Documentation
+-- requirements.txt       # Dependencies
```

## [ROCKET] Production Deployment

### Local Production Test
```bash
# Test production configuration
export FLASK_ENV=production
python -m src.web_app
```

### VPS Deployment
See `scripts/deploy.sh` for complete production setup on Ubuntu/Google Cloud.

### Docker Deployment (Future)
Docker support planned for Phase 3 MVP.

## [U+1F310] Integration Options

### Hugging Face Spaces
**Not recommended** for this Flask application. Hugging Face is optimized for:
- Machine learning models (Transformers, Diffusers)
- Streamlit/Gradio applications
- Static websites

**Better alternatives:**
- **Railway** - Simple Flask deployment
- **Render** - Free tier for Flask apps
- **Google Cloud Run** - Containerized deployment
- **Vercel** - For static frontend (future Phase 2)

### Git Repository Sharing
```bash
# Clone the entire Foundups-Agent repository
git clone https://github.com/your-org/Foundups-Agent.git
cd Foundups-Agent/modules/platform_integration/acoustic_lab

# Install and run
pip install -r requirements.txt
python -m src.web_app
```

## [DATA] Performance & Requirements

### System Requirements
- **Minimum**: 2GB RAM, Python 3.11+, modern browser
- **Recommended**: 4GB RAM, SSD storage, Chrome/Firefox
- **Production**: 2GB RAM, Ubuntu 20.04+, Nginx, PostgreSQL

### Performance Benchmarks
- **Audio Processing**: <2 seconds for 10-second WAV files
- **Fingerprint Matching**: <0.5 seconds against 3-tone library
- **Triangulation**: <0.1 seconds for coordinate calculation
- **Memory Usage**: <50MB per request (in-memory processing)

## [LOCK] Security & Privacy

### Local Development Security
- **No data persistence** - All processing in memory
- **Synthetic data only** - No real audio recordings stored
- **IP geofencing** - Educational/demo restrictions
- **Automatic cleanup** - Data deleted after processing

### Educational Safety
- **No surveillance capabilities**
- **Fictional scenarios only**
- **Mathematics-focused learning**
- **Safe for classroom use**

## [GRADUATE] Educational Usage

### For Students
1. Upload synthetic WAV files
2. Observe triangulation calculations
3. Learn about MFCC fingerprinting
4. Understand sensor network concepts

### For Educators
1. Demonstrate acoustic principles
2. Show practical applications
3. Teach mathematical foundations
4. Explore signal processing concepts

### For Researchers
1. Study triangulation algorithms
2. Analyze fingerprinting techniques
3. Test acoustic processing methods
4. Validate educational approaches

## [U+1F4DE] Support & Resources

### Documentation
- **[Module README](../README.md)** - Complete overview
- **[API Reference](docs/api_reference.md)** - Technical details
- **[Educational Framework](docs/educational_framework.md)** - Learning objectives

### Testing
- **[Test Suite](scripts/test_phase1.py)** - Comprehensive validation
- **[Health Endpoint](/health)** - Service monitoring

### Development
- **[Architecture Design](docs/architecture_design.md)** - System design
- **[Implementation Walkthrough](docs/implementation_walkthrough.md)** - Code details

---

**Installation completed following WSP 49 standards**
**Ready for acoustic triangulation education and research**
**[U+1F300] Windsurf Protocol - Autonomous Educational Development**
