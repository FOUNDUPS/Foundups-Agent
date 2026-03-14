# PQN Alignment Module Interface

## Control-Plane Boundary

Canonical Claw-era split:

- `main.py` = readiness preflight + bootstrap
- `OpenClaw (0102)` = conversational research control plane
- `PQNAlignmentDAE` = detector-first execution engine
- `PQN MCP` = gated external/tool surface

This module is not the primary conversational surface. It is the research engine invoked by the active control plane.

## Public API Functions

### Core Detection and Analysis
- `run_detector(config: Dict) -> Tuple[str, str]`: Run PQN detection on a script
- `run_sweep(config: Dict) -> str`: Execute parameter sweep analysis
- `phase_sweep(config: Dict) -> str`: CLI wrapper for parameter sweep
- `council_run(config: Dict) -> Tuple[str, str]`: Run council optimization cycle

### Results Database Management
- `init_db(db_path: Optional[str] = None) -> None`: Initialize results database
- `index_run(log_path: str, db_path: Optional[str] = None) -> Dict[str, Any]`: Index campaign results
- `index_council_run(summary_path: str, db_path: Optional[str] = None) -> Dict[str, Any]`: Index council results
- `query_runs(filters: Dict[str, object] | None = None, db_path: Optional[str] = None) -> List[Dict[str, Any]]`: Query results
- `query_cross_analysis(filters: Dict[str, object] | None = None, db_path: Optional[str] = None) -> List[Dict[str, Any]]`: Cross-analysis queries

### Data Management
- `promote(source_path: str, target_dir: str) -> str`: Promote results to State 0 archive

## Configuration Parameters

### Detector Configuration
- `script`: Script string to analyze
- `steps`: Number of simulation steps
- `steps_per_sym`: Steps per symbol
- `dt`: Time step parameter
- `out_dir`: Output directory
- `log_csv`: CSV log filename
- `events`: Events JSONL filename

### Sweep Configuration
- `sweep_type`: Type of sweep (resonance, coherence, collapse)
- `parameter_ranges`: Parameter ranges to sweep
- `seeds`: Random seeds for reproducibility
- `output_format`: Output format specification

### Council Configuration
- `proposals`: List of proposal dictionaries with scripts
- `seeds`: Random seeds for evaluation
- `steps`: Simulation steps per evaluation
- `topN`: Number of top results to return

### Database Configuration
- `db_path`: Optional custom database path
- `filters`: Query filters for results retrieval

## Return Values

### Detection Results
- `events_path`: Path to events JSONL file
- `metrics_csv`: Path to metrics CSV file

### Sweep Results
- `sweep_output_path`: Path to sweep results

### Council Results
- `summary_json_path`: Path to summary JSON
- `archive_json_path`: Path to archive JSON

### Database Results
- `summary_dict`: Dictionary with indexed summary data
- `query_results`: List of dictionaries matching query filters

## Error Handling

### FileNotFoundError
- Raised when required input files are missing
- Includes detailed error message with file path

### ValueError
- Raised for invalid configuration parameters
- Includes parameter name and valid range

### SQLiteError
- Raised for database operation failures
- Includes SQL error details

## Usage Examples

### Basic Detection
```python
from modules.ai_intelligence.pqn_alignment import run_detector

config = {
    "script": "^&^&^&",
    "steps": 1200,
    "dt": 0.5/7.05,
    "out_dir": "output"
}
events_path, metrics_csv = run_detector(config)
```

### Campaign Results Indexing
```python
from modules.ai_intelligence.pqn_alignment import index_run

summary = index_run("campaign_log.json")
print(f"Indexed run: {summary['run_id']}")
```

### Council Results Indexing
```python
from modules.ai_intelligence.pqn_alignment import index_council_run

summary = index_council_run("council_summary.json")
print(f"Top script: {summary['top_script']}")
```

### Cross-Analysis Querying
```python
from modules.ai_intelligence.pqn_alignment import query_cross_analysis

results = query_cross_analysis({
    "run_type": "campaign",
    "model": "claude-3.5-haiku"
})
print(f"Found {len(results)} matching runs")
```
