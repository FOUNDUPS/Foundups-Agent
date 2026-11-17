"""Launch orchestrator for FoundUps Agent Market.

Provides service-level entrypoint for launching tokenized FoundUps with
deterministic, adapter-driven behavior suitable for tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4

from .exceptions import NotFoundError, ValidationError
from .interfaces import (
    FoundupRegistryService,
    ObservabilityService,
    RepoProvisioningAdapter,
    TaskPipelineService,
    TokenFactoryAdapter,
)
from .models import Foundup, Task, TaskStatus, TokenTerms


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class LaunchEvent:
    """Auditable event from launch orchestration."""

    event_id: str
    event_type: str
    foundup_id: str
    actor_id: str
    payload: Dict[str, object]
    timestamp: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class LaunchResult:
    """Result of launch_foundup orchestration."""

    foundup: Foundup
    token_address: Optional[str]
    repo_url: Optional[str]
    initial_task: Optional[Task]
    events: List[LaunchEvent]
    success: bool
    error: Optional[str] = None


class LaunchOrchestrator:
    """Orchestrates the full launch flow for a Foundup.

    Adapter-driven and deterministic for tests.
    """

    def __init__(
        self,
        registry: FoundupRegistryService,
        token_adapter: TokenFactoryAdapter,
        task_pipeline: Optional[TaskPipelineService] = None,
        repo_adapter: Optional[RepoProvisioningAdapter] = None,
        observability: Optional[ObservabilityService] = None,
    ):
        self.registry = registry
        self.token_adapter = token_adapter
        self.task_pipeline = task_pipeline
        self.repo_adapter = repo_adapter
        self.observability = observability
        self._events: List[LaunchEvent] = []

    def _emit(
        self,
        event_type: str,
        foundup_id: str,
        actor_id: str,
        payload: Dict[str, object],
    ) -> LaunchEvent:
        """Emit auditable event."""
        event = LaunchEvent(
            event_id=f"launch_ev_{uuid4().hex[:10]}",
            event_type=event_type,
            foundup_id=foundup_id,
            actor_id=actor_id,
            payload=payload,
        )
        self._events.append(event)
        if self.observability:
            self.observability.emit_event(
                event_type,
                actor_id,
                {"foundup_id": foundup_id, **payload},
            )
        return event

    def launch_foundup(
        self,
        foundup: Foundup,
        token_terms: Optional[TokenTerms] = None,
        repo_name: Optional[str] = None,
        repo_provider: str = "github",
        initial_task_params: Optional[Dict[str, object]] = None,
        actor_id: str = "system",
    ) -> LaunchResult:
        """Execute full launch flow for a Foundup.

        Steps:
        0. Validate the optional initial task before adapter effects
        1. Validate/create Foundup in registry
        2. Token deploy adapter call (if token_terms provided)
        3. Repo provision adapter call (if repo_name provided)
        4. Optional initial task creation
        5. Emit auditable events

        Args:
            foundup: The Foundup to launch
            token_terms: Optional token deployment terms
            repo_name: Optional repository name to provision
            repo_provider: Repository provider (default: github)
            initial_task_params: Optional dict with task params (title, description, etc.)
            actor_id: Actor performing the launch

        Returns:
            LaunchResult with all launch artifacts and events
        """
        self._events = []
        token_address: Optional[str] = None
        repo_url: Optional[str] = None
        initial_task: Optional[Task] = None
        error: Optional[str] = None

        try:
            task = None
            if initial_task_params:
                task = Task(
                    task_id=initial_task_params.get("task_id", f"task_{uuid4().hex[:10]}"),
                    foundup_id=foundup.foundup_id,
                    title=str(initial_task_params.get("title", "Initial Task")),
                    description=str(initial_task_params.get("description", "First task for the foundup")),
                    acceptance_criteria=list(
                        initial_task_params.get("acceptance_criteria", ["Complete the task"])
                    ),
                    reward_amount=initial_task_params.get("reward_amount", 100),
                    creator_id=actor_id,
                    status=TaskStatus.OPEN,
                )

            # Step 1: Validate/create Foundup
            try:
                existing = self.registry.get_foundup(foundup.foundup_id)
                self._emit(
                    "launch.foundup_exists",
                    foundup.foundup_id,
                    actor_id,
                    {"name": existing.name},
                )
            except NotFoundError:
                self.registry.create_foundup(foundup)
                self._emit(
                    "launch.foundup_created",
                    foundup.foundup_id,
                    actor_id,
                    {"name": foundup.name, "token_symbol": foundup.token_symbol},
                )

            # Step 2: Token deploy (if terms provided)
            if token_terms:
                token_address = self.token_adapter.deploy_token(foundup, token_terms)
                self.token_adapter.configure_vesting(token_address, token_terms)
                self._emit(
                    "launch.token_deployed",
                    foundup.foundup_id,
                    actor_id,
                    {"token_address": token_address, "max_supply": token_terms.max_supply},
                )

            # Step 3: Repo provision (if repo_name provided and adapter available)
            if repo_name and self.repo_adapter:
                repo_url = self.repo_adapter.provision_repo(
                    foundup.foundup_id,
                    repo_name,
                    provider=repo_provider,
                )
                self._emit(
                    "launch.repo_provisioned",
                    foundup.foundup_id,
                    actor_id,
                    {"repo_url": repo_url, "provider": repo_provider},
                )

            # Step 4: Initial task creation (if params provided)
            if task is not None:
                if self.task_pipeline:
                    initial_task = self.task_pipeline.create_task(task)
                    self._emit(
                        "launch.initial_task_created",
                        foundup.foundup_id,
                        actor_id,
                        {"task_id": task.task_id, "title": task.title},
                    )
                else:
                    initial_task = task
                    self._emit(
                        "launch.initial_task_prepared",
                        foundup.foundup_id,
                        actor_id,
                        {"task_id": task.task_id, "title": task.title},
                    )

            # Step 5: Final launch complete event
            self._emit(
                "launch.complete",
                foundup.foundup_id,
                actor_id,
                {
                    "has_token": token_address is not None,
                    "has_repo": repo_url is not None,
                    "has_initial_task": initial_task is not None,
                },
            )

            return LaunchResult(
                foundup=foundup,
                token_address=token_address,
                repo_url=repo_url,
                initial_task=initial_task,
                events=list(self._events),
                success=True,
            )

        except (ValidationError, NotFoundError) as e:
            error = str(e)
            self._emit(
                "launch.failed",
                foundup.foundup_id,
                actor_id,
                {"error": error},
            )
            return LaunchResult(
                foundup=foundup,
                token_address=token_address,
                repo_url=repo_url,
                initial_task=initial_task,
                events=list(self._events),
                success=False,
                error=error,
            )


def launch_foundup(
    registry: FoundupRegistryService,
    token_adapter: TokenFactoryAdapter,
    foundup: Foundup,
    token_terms: Optional[TokenTerms] = None,
    repo_name: Optional[str] = None,
    repo_adapter: Optional[RepoProvisioningAdapter] = None,
    task_pipeline: Optional[TaskPipelineService] = None,
    initial_task_params: Optional[Dict[str, object]] = None,
    actor_id: str = "system",
    observability: Optional[ObservabilityService] = None,
) -> LaunchResult:
    """Convenience function for launch orchestration.

    Creates a LaunchOrchestrator and executes the launch flow.
    """
    orchestrator = LaunchOrchestrator(
        registry=registry,
        token_adapter=token_adapter,
        task_pipeline=task_pipeline,
        repo_adapter=repo_adapter,
        observability=observability,
    )
    return orchestrator.launch_foundup(
        foundup=foundup,
        token_terms=token_terms,
        repo_name=repo_name,
        initial_task_params=initial_task_params,
        actor_id=actor_id,
    )
