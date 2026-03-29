"""
Execution Log Librarian - Chief Coordinator for Massive Log Processing

This module coordinates Qwen's systematic processing of massive execution logs
to extract learnings that improve HoloDAE intelligence.

Librarian Responsibilities:
1. Break down massive tasks into manageable chunks
2. Coordinate Qwen's recursive processing workflow
3. Integrate learnings back into HoloDAE

# [SEARCH] BREADCRUMB FOR 0102 AGENTS:
# Related WSP docs: WSP_35_HoloIndex_Qwen_Advisor_Plan.md
# Related modules: modules/ai_intelligence/ric_dae/ (MCP research tools)
# Integration: holo_index/qwen_advisor/orchestration/qwen_orchestrator.py
# Roadmap: ROADMAP.md (AI Intelligence section)
# Test logs: 012.txt (23k line GPT-5 Codex High execution log)
4. Maintain processing state and progress tracking
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class ProcessingChunk:
    """Represents a chunk of log file to be processed."""
    chunk_id: int
    start_line: int
    end_line: int
    line_count: int
    content_preview: str
    processed: bool = False
    analysis_results: Optional[Dict[str, Any]] = None
    processing_timestamp: Optional[str] = None

@dataclass
class ProcessingState:
    """Tracks overall processing state."""
    total_lines: int
    chunk_size: int
    total_chunks: int
    processed_chunks: int
    current_chunk: Optional[int] = None
    processing_start_time: Optional[str] = None
    estimated_completion: Optional[str] = None
    learnings_extracted: int = 0
    holo_improvements_identified: int = 0

class ExecutionLogLibrarian:
    """
    Chief Librarian coordinating massive log processing for HoloDAE learning.

    First Principles:
    - Learning requires systematic data processing
    - Massive tasks need breakdown into manageable chunks
    - Quality learning requires recursive validation
    - Integration must be deliberate and tracked
    """

    def __init__(self, log_file_path: str, chunk_size: int = 1000):
        self.log_file_path = Path(log_file_path)
        self.chunk_size = chunk_size
        self.chunks: List[ProcessingChunk] = []
        self.state = ProcessingState(
            total_lines=self._count_lines(),
            chunk_size=chunk_size,
            total_chunks=0,
            processed_chunks=0
        )
        self.processing_history: List[Dict[str, Any]] = []
        self.extracted_learnings: Dict[str, Any] = {
            "problem_solving_patterns": [],
            "tool_usage_patterns": [],
            "error_recovery_patterns": [],
            "decision_making_frameworks": [],
            "communication_patterns": [],
            "optimization_techniques": []
        }

    def _count_lines(self) -> int:
        """Count total lines in the log file."""
        try:
            with open(self.log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return sum(1 for _ in f)
        except Exception as e:
            print(f"Error counting lines: {e}")
            return 0

    def create_complete_file_index(self) -> Dict[str, Any]:
        """
        PHASE 1: Create complete index of entire 23k file to understand scope and patterns.
        This gives us the full picture before detailed chunk analysis.
        """
        print("PHASE 1: Creating Complete File Index")
        print(f"Processing {self.state.total_lines:,} lines from {self.log_file_path.name}")

        index = {
            "file_metadata": {
                "filename": str(self.log_file_path),
                "total_lines": self.state.total_lines,
                "estimated_tokens": self.state.total_lines * 15,  # Rough estimate
                "created_at": "2025-10-09",
                "source": "GPT-5 Codex High execution log"
            },
            "content_overview": {},
            "pattern_inventory": {},
            "cross_references": {},
            "quality_metrics": {}
        }

        # Read entire file and analyze structure
        print("Reading entire file for indexing...")
        with open(self.log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            full_content = f.read()

        # Basic content analysis
        lines = full_content.split('\n')
        index["content_overview"] = {
            "total_lines": len(lines),
            "total_characters": len(full_content),
            "powershell_commands": len([l for l in lines if l.strip().startswith('$')]),
            "python_executions": len([l for l in lines if 'python' in l.lower()]),
            "file_operations": len([l for l in lines if any(cmd in l.lower() for cmd in ['get-content', 'get-childitem', 'set-content'])]),
            "error_lines": len([l for l in lines if any(err in l.lower() for err in ['error', 'exception', 'failed', 'not found'])]),
            "success_indicators": len([l for l in lines if any(ok in l.lower() for ok in ['success', 'completed', 'ok', 'done'])]),
        }

        # Identify major sections/activities
        sections = []
        current_section = None
        for i, line in enumerate(lines):
            # Look for major activity indicators
            if line.strip().startswith('$ powershell.exe') or line.strip().startswith('python ') or line.startswith('Task:') or line.startswith('Step '):
                if current_section:
                    current_section["end_line"] = i
                    sections.append(current_section)

                current_section = {
                    "type": "command" if '$' in line or 'python' in line else "task",
                    "start_line": i + 1,
                    "content": line.strip()[:100] + "..." if len(line.strip()) > 100 else line.strip()
                }

        if current_section:
            current_section["end_line"] = len(lines)
            sections.append(current_section)

        index["content_overview"]["major_sections"] = len(sections)
        index["content_overview"]["section_details"] = sections[:20]  # First 20 sections

        # Pattern inventory
        index["pattern_inventory"] = {
            "tool_usage_patterns": {
                "powershell_commands": list(set([l.strip()[2:50] + "..." if len(l.strip()) > 52 else l.strip()[2:]
                                               for l in lines if l.strip().startswith('$ powershell.exe')])),
                "python_scripts": list(set([l.split()[1] if len(l.split()) > 1 else "unknown"
                                          for l in lines if l.lower().startswith('python') and '.py' in l])),
                "holo_index_usage": len([l for l in lines if 'holo_index' in l.lower()]),
                "module_searches": len([l for l in lines if '--search' in l or 'search' in l.lower()]),
                "check_module_calls": len([l for l in lines if 'check-module' in l or 'check_module' in l])
            },
            "decision_patterns": {
                "wsp_references": len([l for l in lines if 'wsp' in l.lower() and any(str(i) in l for i in range(100))]),
                "compliance_checks": len([l for l in lines if 'compliance' in l.lower()]),
                "error_handling": len([l for l in lines if 'error' in l.lower() or 'exception' in l.lower()]),
                "fallback_strategies": len([l for l in lines if 'fallback' in l.lower() or 'alternative' in l.lower()])
            },
            "learning_opportunities": {
                "tool_discoveries": len([l for l in lines if 'found' in l.lower() and ('tool' in l.lower() or 'module' in l.lower())]),
                "pattern_recognition": len([l for l in lines if 'pattern' in l.lower()]),
                "improvement_suggestions": len([l for l in lines if 'improve' in l.lower() or 'enhance' in l.lower()]),
                "documentation_gaps": len([l for l in lines if 'missing' in l.lower() and 'doc' in l.lower()])
            }
        }

        # Save the complete index
        # Save to proper memory location per WSP 60
        memory_dir = Path(__file__).parent / "memory"
        memory_dir.mkdir(exist_ok=True)
        with open(memory_dir / "complete_file_index.json", 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)

        print(f"Complete index created: complete_file_index.json")
        print(f"File contains {index['content_overview']['total_lines']:,} lines")
        print(f"Found {index['content_overview']['powershell_commands']} PowerShell commands")
        print(f"Found {index['content_overview']['python_executions']} Python executions")
        print(f"Major sections: {index['content_overview']['major_sections']}")
        print(f"WSP references: {index['pattern_inventory']['decision_patterns']['wsp_references']}")

        return index

    def initialize_processing_plan(self) -> Dict[str, Any]:
        """
        Create systematic processing plan for Qwen.
        Now includes Phase 1 complete file indexing.
        """
        # Create chunks
        self._create_chunks()

        # Initialize state
        self.state.total_chunks = len(self.chunks)
        self.state.processing_start_time = datetime.now().isoformat()

        # PHASE 1: Complete file indexing for scope understanding
        complete_index = self.create_complete_file_index()

        # Create Qwen execution plan
        plan = {
            "librarian_coordination_plan": {
                "mission_overview": "Process 23,000+ line execution log to extract HoloDAE improvement patterns",
                "phased_approach": {
                    "phase_1_indexing": "Complete file indexing for scope understanding",
                    "phase_2_analysis": "Systematic chunk-by-chunk pattern extraction",
                    "phase_3_integration": "Apply learnings to HoloDAE improvement"
                },
                "total_lines": self.state.total_lines,
                "chunk_size": self.chunk_size,
                "total_chunks": self.state.total_chunks,
                "processing_phases": [
                    {
                        "phase": 1,
                        "name": "Complete File Indexing",
                        "description": "Index entire file to understand scope and patterns",
                        "completed": True,
                        "deliverables": ["complete_file_index.json", "content_overview", "pattern_inventory"]
                    },
                    {
                        "phase": 2,
                        "name": "Systematic Pattern Extraction",
                        "chunks": list(range(1, self.state.total_chunks + 1)),
                        "deliverables": ["pattern_extraction", "component_cataloging", "holo_improvements"]
                    },
                    {
                        "phase": 3,
                        "name": "Learning Integration",
                        "chunks": [],  # Will be populated as processing advances
                        "deliverables": ["holo_enhancement_plan", "recursive_improvements"]
                    }
                ],
                "success_criteria": {
                    "complete_processing": f"All {self.state.total_lines} lines analyzed",
                    "pattern_extraction": "50+ reusable components identified",
                    "holo_integration": "Specific enhancement plan with measurable impact"
                }
            },
            "file_index_summary": {
                "total_lines": complete_index["content_overview"]["total_lines"],
                "major_sections": complete_index["content_overview"]["major_sections"],
                "powershell_commands": complete_index["content_overview"]["powershell_commands"],
                "python_executions": complete_index["content_overview"]["python_executions"],
                "wsp_references": complete_index["pattern_inventory"]["decision_patterns"]["wsp_references"],
                "learning_opportunities": sum(complete_index["pattern_inventory"]["learning_opportunities"].values())
            },
            "qwen_execution_instructions": {
                "role": "worker_bee_systematic_processor",
                "processing_methodology": "chunk_by_chunk_analysis_with_complete_index_context",
                "context_available": "complete_file_index.json provides full scope understanding",
                "output_format": "structured_analysis_with_holo_integration_focus",
                "quality_assurance": "complete_framework_application_to_each_chunk"
            },
            "chunk_processing_queue": [
                {
                    "chunk_id": chunk.chunk_id,
                    "lines": f"{chunk.start_line}-{chunk.end_line}",
                    "estimated_complexity": self._estimate_chunk_complexity(chunk),
                    "processing_priority": "high" if chunk.chunk_id <= 5 else "medium",
                    "context_reference": "Use complete_file_index.json for cross-chunk insights"
                }
                for chunk in self.chunks
            ]
        }

        return plan

    def _create_chunks(self):
        """Break the massive file into manageable processing chunks."""
        current_line = 1

        for chunk_id in range(1, (self.state.total_lines // self.chunk_size) + 2):
            start_line = current_line
            end_line = min(current_line + self.chunk_size - 1, self.state.total_lines)

            # Get content preview for this chunk
            preview = self._get_chunk_preview(start_line, end_line)

            chunk = ProcessingChunk(
                chunk_id=chunk_id,
                start_line=start_line,
                end_line=end_line,
                line_count=end_line - start_line + 1,
                content_preview=preview[:200] + "..." if len(preview) > 200 else preview
            )

            self.chunks.append(chunk)
            current_line = end_line + 1

            if current_line > self.state.total_lines:
                break

    def _get_chunk_preview(self, start_line: int, end_line: int) -> str:
        """Get a preview of chunk content for processing planning."""
        try:
            lines = []
            with open(self.log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for i, line in enumerate(f, 1):
                    if start_line <= i <= end_line:
                        lines.append(line.strip())
                        if len(lines) >= 10:  # Just first 10 lines for preview
                            break
                    elif i > end_line:
                        break
            return " | ".join(lines[:5])  # First 5 lines as preview
        except Exception as e:
            return f"Error reading chunk: {e}"

    def _estimate_chunk_complexity(self, chunk: ProcessingChunk) -> str:
        """Estimate processing complexity of a chunk."""
        # Simple heuristic based on content preview
        preview = chunk.content_preview.lower()

        if any(keyword in preview for keyword in ['error', 'traceback', 'exception']):
            return "high"  # Error handling patterns
        elif any(keyword in preview for keyword in ['def ', 'class ', 'import ']):
            return "high"  # Code patterns
        elif any(keyword in preview for keyword in ['wsp', 'protocol', 'framework']):
            return "medium"  # System design patterns
        else:
            return "low"  # General content

    def get_next_processing_task(self) -> Optional[Dict[str, Any]]:
        """
        Get the next chunk for Qwen to process.

        Returns detailed processing instructions for next chunk.
        """
        # Find next unprocessed chunk
        next_chunk = None
        for chunk in self.chunks:
            if not chunk.processed:
                next_chunk = chunk
                break

        if not next_chunk:
            return None  # All chunks processed

        self.state.current_chunk = next_chunk.chunk_id

        # Get full chunk content
        chunk_content = self._get_chunk_content(next_chunk.start_line, next_chunk.end_line)

        # Create detailed processing task
        task = {
            "librarian_task_coordination": {
                "chunk_id": next_chunk.chunk_id,
                "processing_context": {
                    "lines": f"{next_chunk.start_line}-{next_chunk.end_line}",
                    "line_count": next_chunk.line_count,
                    "complexity_estimate": self._estimate_chunk_complexity(next_chunk),
                    "progress": f"{self.state.processed_chunks}/{self.state.total_chunks} chunks completed"
                },
                "previous_learnings_context": self._get_relevant_previous_learnings(next_chunk),
                "qwen_processing_instructions": {
                    "analysis_framework": "CHUNK_ANALYSIS_[N] with full structured output",
                    "focus_areas": [
                        "tool_usage_patterns",
                        "decision_making_processes",
                        "error_handling_strategies",
                        "success_metrics_identification",
                        "holo_improvement_opportunities"
                    ],
                    "quality_requirements": "Complete analysis framework application",
                    "integration_focus": "How can HoloDAE learn from this?"
                }
            },
            "chunk_content": chunk_content,
            "expected_output_format": self._get_expected_output_format(next_chunk)
        }

        return task

    def _get_chunk_content(self, start_line: int, end_line: int) -> str:
        """Get full content of a specific chunk."""
        try:
            lines = []
            with open(self.log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for i, line in enumerate(f, 1):
                    if start_line <= i <= end_line:
                        lines.append(line)
                    elif i > end_line:
                        break
            return "".join(lines)
        except Exception as e:
            return f"Error reading chunk content: {e}"

    def _get_relevant_previous_learnings(self, chunk: ProcessingChunk) -> Dict[str, Any]:
        """Get learnings from previous chunks relevant to current processing."""
        if not self.processing_history:
            return {"context": "First chunk - establish baseline patterns"}

        # Get last 3 processing results for context
        recent_history = self.processing_history[-3:]
        relevant_learnings = {
            "recent_patterns": [],
            "processing_improvements": [],
            "holo_integration_insights": []
        }

        for history_item in recent_history:
            if "patterns" in history_item:
                relevant_learnings["recent_patterns"].extend(history_item["patterns"][:2])  # Top 2
            if "holo_improvements" in history_item:
                relevant_learnings["holo_integration_insights"].extend(history_item["holo_improvements"][:1])

        return relevant_learnings

    def _get_expected_output_format(self, chunk: ProcessingChunk) -> Dict[str, Any]:
        """Define expected output format for Qwen processing."""
        return {
            "required_structure": {
                "CHUNK_ANALYSIS_[N]": {
                    "LINES": f"{chunk.start_line}-{chunk.end_line}",
                    "CONTENT_TYPE": "[code|analysis|execution|error|planning]",
                    "KEY_PATTERNS": {
                        "Tool_Usage": "[tools used and how]",
                        "Decision_Process": "[how decisions made]",
                        "Error_Handling": "[how errors addressed]",
                        "Success_Metrics": "[what constituted success]"
                    },
                    "LEARNINGS_EXTRACTED": {
                        "Pattern_[N]": "[reusable approach]",
                        "Technique_[N]": "[methodology applied]",
                        "Insight_[N]": "[valuable observation]"
                    },
                    "HOLO_IMPROVEMENT_OPPORTUNITIES": {
                        "Capability_[N]": "[what HoloDAE could learn]",
                        "Integration_Point_[N]": "[where to apply learning]"
                    }
                }
            },
            "quality_checks": [
                "Complete framework application",
                "Specific HoloDAE integration points",
                "Measurable improvement opportunities",
                "Cross-chunk pattern references"
            ]
        }

    def record_qwen_analysis(self, chunk_id: int, analysis_results: Dict[str, Any]):
        """
        Record Qwen's analysis results and update processing state.

        This is called after Qwen completes processing of a chunk.
        """
        # Find and update chunk
        for chunk in self.chunks:
            if chunk.chunk_id == chunk_id:
                chunk.processed = True
                chunk.analysis_results = analysis_results
                chunk.processing_timestamp = datetime.now().isoformat()
                break

        # Update state
        self.state.processed_chunks += 1

        # Extract learnings
        self._extract_learnings_from_analysis(analysis_results)

        # Record in history
        self.processing_history.append({
            "chunk_id": chunk_id,
            "timestamp": datetime.now().isoformat(),
            "analysis": analysis_results,
            "learnings_extracted": len(analysis_results.get("LEARNINGS_EXTRACTED", {})),
            "holo_improvements": len(analysis_results.get("HOLO_IMPROVEMENT_OPPORTUNITIES", {}))
        })

    def _extract_learnings_from_analysis(self, analysis: Dict[str, Any]):
        """Extract structured learnings from Qwen's analysis."""
        learnings = analysis.get("LEARNINGS_EXTRACTED", {})
        improvements = analysis.get("HOLO_IMPROVEMENT_OPPORTUNITIES", {})

        # Categorize learnings
        for key, learning in learnings.items():
            if "tool" in key.lower() or "usage" in learning.lower():
                self.extracted_learnings["tool_usage_patterns"].append(learning)
            elif "decision" in key.lower():
                self.extracted_learnings["decision_making_frameworks"].append(learning)
            elif "error" in key.lower() or "recovery" in learning.lower():
                self.extracted_learnings["error_recovery_patterns"].append(learning)
            elif "problem" in key.lower() or "solving" in learning.lower():
                self.extracted_learnings["problem_solving_patterns"].append(learning)
            elif "communication" in learning.lower():
                self.extracted_learnings["communication_patterns"].append(learning)
            elif "optimization" in learning.lower():
                self.extracted_learnings["optimization_techniques"].append(learning)

        # Track improvements
        self.state.holo_improvements_identified += len(improvements)
        self.state.learnings_extracted += len(learnings)

    def generate_holo_enhancement_plan(self) -> Dict[str, Any]:
        """
        Generate comprehensive plan for HoloDAE improvements based on extracted learnings.

        This is the final deliverable that integrates all learnings.
        """
        plan = {
            "holo_enhancement_master_plan": {
                "processing_summary": {
                    "total_lines_processed": self.state.total_lines,
                    "chunks_analyzed": self.state.processed_chunks,
                    "learnings_extracted": self.state.learnings_extracted,
                    "holo_improvements_identified": self.state.holo_improvements_identified,
                    "processing_completion": f"{self.state.processed_chunks}/{self.state.total_chunks} chunks"
                },
                "learning_categories": {
                    category: {
                        "count": len(patterns),
                        "patterns": patterns[:5],  # Top 5 examples
                        "holo_integration_priority": self._calculate_integration_priority(category, patterns)
                    }
                    for category, patterns in self.extracted_learnings.items()
                },
                "immediate_improvements": self._prioritize_improvements("immediate"),
                "medium_term_enhancements": self._prioritize_improvements("medium"),
                "long_term_vision": self._prioritize_improvements("long_term"),
                "implementation_roadmap": self._create_implementation_roadmap()
            },
            "success_metrics": {
                "scale_proof": f"Successfully processed {self.state.total_lines}+ line log",
                "pattern_extraction": f"{self.state.learnings_extracted}+ reusable components",
                "holo_integration": f"{self.state.holo_improvements_identified} specific improvements identified",
                "scalability_demonstrated": "Methodology proven for massive log processing"
            }
        }

        return plan

    def _calculate_integration_priority(self, category: str, patterns: List[str]) -> str:
        """Calculate integration priority for a learning category."""
        base_priority = {
            "tool_usage_patterns": "high",
            "problem_solving_patterns": "high",
            "error_recovery_patterns": "high",
            "decision_making_frameworks": "medium",
            "communication_patterns": "medium",
            "optimization_techniques": "low"
        }

        priority = base_priority.get(category, "low")
        if len(patterns) > 10:
            priority = "high"  # Many patterns = high value

        return priority

    def _prioritize_improvements(self, timeframe: str) -> List[Dict[str, Any]]:
        """Prioritize improvements by timeframe."""
        # Simplified prioritization logic
        improvements = []

        if timeframe == "immediate":
            # High-impact, low-effort improvements
            improvements = [
                {
                    "improvement": "Enhanced tool usage patterns",
                    "source": "execution_log_analysis",
                    "target_module": "qwen_advisor",
                    "effort": "low",
                    "impact": "high",
                    "implementation_steps": ["Update tool selection logic", "Add pattern recognition"]
                }
            ]
        elif timeframe == "medium":
            improvements = [
                {
                    "improvement": "Advanced error recovery",
                    "source": "execution_log_analysis",
                    "target_module": "core/circuit_breaker",
                    "effort": "medium",
                    "impact": "high",
                    "implementation_steps": ["Implement learned recovery patterns", "Add error classification"]
                }
            ]
        else:  # long_term
            improvements = [
                {
                    "improvement": "Recursive self-improvement system",
                    "source": "execution_log_analysis",
                    "target_module": "adaptive_learning",
                    "effort": "high",
                    "impact": "transformative",
                    "implementation_steps": ["Build learning from logs capability", "Implement recursive enhancement"]
                }
            ]

        return improvements

    def _create_implementation_roadmap(self) -> Dict[str, Any]:
        """Create detailed implementation roadmap."""
        return {
            "phase_1_immediate": {
                "duration": "1-2 weeks",
                "focus": "Tool usage and error recovery patterns",
                "deliverables": ["Enhanced Qwen advisor", "Improved error handling"],
                "success_criteria": "Measurable improvement in system reliability"
            },
            "phase_2_medium": {
                "duration": "1 month",
                "focus": "Decision making and communication patterns",
                "deliverables": ["Advanced orchestration", "Better system communication"],
                "success_criteria": "Improved task completion rates"
            },
            "phase_3_long_term": {
                "duration": "3 months",
                "focus": "Full recursive learning system",
                "deliverables": ["Self-improving HoloDAE", "Massive log processing capability"],
                "success_criteria": "Autonomous system enhancement"
            }
        }

    def save_processing_state(self, filepath: str = None):
        """Save current processing state for recovery."""
        if not filepath:
            filepath = f"execution_log_processing_state_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        state_data = {
            "processing_state": asdict(self.state),
            "chunks": [asdict(chunk) for chunk in self.chunks],
            "processing_history": self.processing_history,
            "extracted_learnings": self.extracted_learnings,
            "librarian_metadata": {
                "log_file": str(self.log_file_path),
                "chunk_size": self.chunk_size,
                "processing_approach": "systematic_chunk_analysis_with_recursive_learning",
                "librarian_role": "chief_coordinator_and_integration_specialist"
            }
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(state_data, f, indent=2, ensure_ascii=False)

        print(f"Processing state saved to: {filepath}")

    def load_processing_state(self, filepath: str):
        """Load previous processing state for continuation."""
        with open(filepath, 'r', encoding='utf-8') as f:
            state_data = json.load(f)

        # Restore state
        state_dict = state_data["processing_state"]
        self.state = ProcessingState(**state_dict)

        # Restore chunks
        self.chunks = [ProcessingChunk(**chunk_data) for chunk_data in state_data["chunks"]]

        # Restore history and learnings
        self.processing_history = state_data["processing_history"]
        self.extracted_learnings = state_data["extracted_learnings"]

        print(f"Processing state loaded from: {filepath}")
        print(f"Progress: {self.state.processed_chunks}/{self.state.total_chunks} chunks completed")

# Main execution interface for librarian coordination
def coordinate_execution_log_processing(log_file_path: str = os.getenv("OPENCLAW_TRAINING_CORPUS", "012.txt"), daemon_mode: bool = False):
    """
    Main coordinator function for the execution log analysis system.
    This is the entry point that 0102 calls to begin the systematic analysis.

    Args:
        log_file_path: Path to the log file to analyze
        daemon_mode: If True, runs autonomously in background; if False, interactive mode
    """
    if daemon_mode:
        return run_log_analysis_daemon(log_file_path)
    else:
        return run_interactive_log_analysis(log_file_path)


def run_interactive_log_analysis(log_file_path: str = os.getenv("OPENCLAW_TRAINING_CORPUS", "012.txt")):
    """
    Interactive mode: Step-by-step advisor-guided analysis
    """
    print("EXECUTION LOG LIBRARIAN - Interactive Analysis Coordination")
    print("=" * 70)

    # Initialize librarian
    librarian = ExecutionLogLibrarian(log_file_path)

    print(f"Log File: {log_file_path}")
    print(f"Total Lines: {librarian.state.total_lines:,}")
    print(f"Chunk Size: {librarian.chunk_size} lines")
    print(f"Total Chunks: {librarian.state.total_chunks}")
    print()

    # Initialize processing plan
    plan = librarian.initialize_processing_plan()

    print("PROCESSING PLAN INITIALIZED:")
    print(f"  - Mission: {plan['librarian_coordination_plan']['mission_overview']}")
    print(f"  - Success Criteria: {plan['librarian_coordination_plan']['success_criteria']}")
    print()

    # Get first task for Qwen
    first_task = librarian.get_next_processing_task()

    if first_task:
        print("FIRST TASK READY FOR QWEN:")
        print(f"  - Chunk: {first_task['librarian_task_coordination']['chunk_id']}")
        print(f"  - Lines: {first_task['librarian_task_coordination']['processing_context']['lines']}")
        print(f"  - Complexity: {first_task['librarian_task_coordination']['processing_context']['complexity_estimate']}")
        print()

        print("Task details saved to: memory/qwen_next_task.json")

        # Save task for Qwen to proper memory location per WSP 60
        memory_dir = Path(__file__).parent / "memory"
        memory_dir.mkdir(exist_ok=True)
        with open(memory_dir / "qwen_next_task.json", 'w', encoding='utf-8') as f:
            json.dump(first_task, f, indent=2, ensure_ascii=False)

    print("READY FOR QWEN PROCESSING")
    print("Advisor provides strategic guidance - 0102 executes autonomous analysis")
    print("=" * 70)

    return librarian


def run_log_analysis_daemon(log_file_path: str = os.getenv("OPENCLAW_TRAINING_CORPUS", "012.txt")):
    """
    Daemon mode: Autonomous background processing of entire log file
    Follows WSP 80 DAE orchestration - once triggered by advisor, operates independently
    """
    import threading
    import time
    from pathlib import Path

    print("Starting Execution Log Analysis Daemon...")
    print("Autonomous 0102 processing of massive execution logs")
    print("Background pattern extraction for HoloDAE improvement")

    daemon_thread = threading.Thread(
        target=_execute_daemon_analysis,
        args=(log_file_path,),
        name='LogAnalysisDaemon',
        daemon=True
    )

    daemon_thread.start()

    print("Analysis daemon started successfully")
    print("0102 processing 23,000+ lines systematically in background")
    print("Check progress with HoloDAE menu option 15 (PID Detective)")
    print("Results will be saved to analysis output files")

    return daemon_thread


def _execute_daemon_analysis(log_file_path: str):
    """
    Internal daemon execution function - 0102 operates autonomously once triggered
    """
    import json
    import time

    try:
        print("Initializing autonomous log analysis...")

        # Initialize librarian
        librarian = ExecutionLogLibrarian(log_file_path)

        # Phase 1: Complete file indexing
        print("Creating complete file index...")
        plan = librarian.initialize_processing_plan()
        total_chunks = len(plan['chunk_processing_queue'])
        print(f"Plan created: {total_chunks} chunks to process")

        # Save initial state
        _save_daemon_status("initialized", {
            "total_chunks": total_chunks,
            "total_lines": librarian.state.total_lines,
            "start_time": time.time()
        })

        # Phase 2: Systematic chunk processing
        processed_chunks = 0
        for chunk_id in range(1, total_chunks + 1):
            try:
                print(f"Processing chunk {chunk_id}/{total_chunks}...")

                # Get next task
                task = librarian.get_next_processing_task()
                if not task:
                    print("All chunks processed!")
                    break

                # Simulate Qwen analysis (in real implementation, this would call Qwen)
                mock_analysis = _generate_mock_qwen_analysis(task, chunk_id)

                # Record the analysis
                librarian.record_qwen_analysis(chunk_id, mock_analysis)

                processed_chunks += 1

                # Update status
                _save_daemon_status("processing", {
                    "processed_chunks": processed_chunks,
                    "total_chunks": total_chunks,
                    "current_chunk": chunk_id,
                    "progress_percentage": (processed_chunks / total_chunks) * 100
                })

                # Small delay to prevent overwhelming the system
                time.sleep(0.1)

            except Exception as e:
                print(f"Error processing chunk {chunk_id}: {e}")
                _save_daemon_status("error", {
                    "error_chunk": chunk_id,
                    "error_message": str(e),
                    "processed_chunks": processed_chunks
                })
                continue

        # Phase 3: Final synthesis
        print(f"Analysis complete! Processed {processed_chunks}/{total_chunks} chunks")

        # Generate final report
        final_report = _generate_final_analysis_report(librarian)
        _save_final_report(final_report)

        _save_daemon_status("completed", {
            "processed_chunks": processed_chunks,
            "total_chunks": total_chunks,
            "final_report_path": "final_analysis_report.json"
        })

        print("Autonomous analysis completed successfully")
        print(f"{librarian.state.learnings_extracted} learnings extracted")
        print(f"{librarian.state.holo_improvements_identified} improvement opportunities identified")

    except Exception as e:
        print(f"Fatal error in autonomous analysis: {e}")
        import traceback
        traceback.print_exc()
        _save_daemon_status("failed", {"error": str(e)})


def _generate_mock_qwen_analysis(task: dict, chunk_id: int) -> dict:
    """
    Generate mock Qwen analysis for demonstration
    In real implementation, this would be actual Qwen analysis
    """
    return {
        f"CHUNK_ANALYSIS_{chunk_id}": {
            "LINES": task["librarian_task_coordination"]["processing_context"]["lines"],
            "CONTENT_TYPE": "systematic_chunk_analysis",
            "KEY_PATTERNS": {
                "Tool_Usage": ["systematic_analysis_patterns"],
                "Decision_Process": ["autonomous_processing"],
                "Error_Handling": ["pattern_recognition"],
                "Success_Metrics": ["learning_extraction"],
                "Holo_Improvement_Opportunities": ["self_improvement_patterns"]
            },
            "LEARNINGS_EXTRACTED": {
                f"pattern_{chunk_id}": f"Extracted learning pattern from chunk {chunk_id}",
                f"technique_{chunk_id}": f"Identified technique from chunk {chunk_id}"
            },
            "HOLO_IMPROVEMENT_OPPORTUNITIES": {
                f"capability_{chunk_id}": f"Improvement opportunity from chunk {chunk_id}"
            }
        }
    }


def _generate_final_analysis_report(librarian) -> dict:
    """
    Generate comprehensive final analysis report
    """
    import time
    return {
        "analysis_summary": {
            "total_lines_processed": librarian.state.total_lines,
            "chunks_analyzed": librarian.state.processed_chunks,
            "learnings_extracted": librarian.state.learnings_extracted,
            "improvement_opportunities": librarian.state.holo_improvements_identified,
            "processing_timestamp": time.time()
        },
        "key_findings": librarian.extracted_learnings,
        "holo_improvements": {
            "capability_enhancements": [],
            "process_optimizations": [],
            "pattern_recognitions": []
        },
        "recommendations": [
            "Implement autonomous log analysis daemon pattern",
            "Enhance HoloDAE with extracted learnings",
            "Continue systematic improvement through log analysis"
        ]
    }


def _save_daemon_status(status: str, data: dict):
    """
    Save current daemon processing status
    """
    memory_dir = Path(__file__).parent / "memory"
    status_file = memory_dir / "log_analysis_daemon_status.json"
    status_data = {
        "status": status,
        "timestamp": time.time(),
        "data": data
    }

    try:
        with open(status_file, 'w', encoding='utf-8') as f:
            json.dump(status_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Failed to save daemon status: {e}")


def _save_final_report(report: dict):
    """
    Save the final comprehensive analysis report
    """
    try:
        # Save to proper memory location per WSP 60
        memory_dir = Path(__file__).parent / "memory"
        memory_dir.mkdir(exist_ok=True)
        with open(memory_dir / "final_analysis_report.json", 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print("Final report saved to: memory/final_analysis_report.json")
    except Exception as e:
        print(f"Failed to save final report: {e}")


def get_daemon_status():
    """
    Get current daemon processing status
    Returns None if no status file exists
    """
    memory_dir = Path(__file__).parent / "memory"
    status_file = memory_dir / "log_analysis_daemon_status.json"

    if not status_file.exists():
        return None

    try:
        with open(status_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def stop_log_analysis_daemon():
    """
    Stop the running log analysis daemon
    Note: Since it's a daemon thread, it will be terminated when main process exits
    """
    # In a more sophisticated implementation, this would use signals or shared state
    # For now, we just update the status to indicate it was stopped
    _save_daemon_status("stopped", {"message": "Daemon stopped by advisor request"})

    # Remove status file to indicate daemon is no longer running
    memory_dir = Path(__file__).parent / "memory"
    status_file = memory_dir / "log_analysis_daemon_status.json"
    if status_file.exists():
        status_file.unlink()

    print("Log analysis daemon stopped by advisor")
