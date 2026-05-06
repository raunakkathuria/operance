"""Daemon skeleton for Milestone M1."""

from __future__ import annotations

import logging
from time import monotonic, perf_counter
from dataclasses import dataclass, field
from typing import Mapping

from .adapters import build_default_adapter_set
from .adapters.base import AdapterSet
from .audit import AuditEntry, AuditStore
from .config import AppConfig
from .confirmation import build_confirmation_metadata
from .executor import ActionExecutor
from .intent import DeterministicIntentMatcher
from .logger import configure_logging
from .models.actions import ActionPlan
from .models.events import (
    ActionPlanEvent,
    ActionResultEvent,
    PlanValidationEvent,
    ResponseEvent,
    RuntimeState,
    TranscriptEvent,
    WakeEvent,
)
from .planner import (
    PlannerClientError,
    PlannerContextWindow,
    PlannerParseError,
    PlannerRoutingPolicy,
    PlannerServiceClient,
    PlannerServiceConfig,
    parse_planner_payload,
)
from .policy import ExecutionPolicy
from .registry import build_default_action_registry
from .responder import ResponseBuilder
from .runtime.event_bus import InMemoryEventBus
from .runtime.metrics import CommandMetrics, MetricsCollector
from .runtime.state_machine import RuntimeStateMachine
from .status import StatusSnapshot
from .validator import PlanValidator


@dataclass(slots=True)
class OperanceDaemon:
    config: AppConfig
    adapters: AdapterSet = field(default_factory=AdapterSet)
    event_bus: InMemoryEventBus = field(default_factory=InMemoryEventBus)
    intent_matcher: DeterministicIntentMatcher = field(default_factory=DeterministicIntentMatcher)
    metrics: MetricsCollector = field(default_factory=MetricsCollector)
    validator: PlanValidator = field(default_factory=lambda: PlanValidator(build_default_action_registry()))
    policy: ExecutionPolicy = field(default_factory=ExecutionPolicy)
    executor: ActionExecutor = field(init=False)
    response_builder: ResponseBuilder = field(default_factory=ResponseBuilder)
    planner_client: PlannerServiceClient | None = field(default=None)
    planner_context_window: PlannerContextWindow = field(default_factory=PlannerContextWindow)
    audit_store: AuditStore = field(init=False)
    logger: logging.Logger = field(init=False)
    planner_routing_policy: PlannerRoutingPolicy = field(init=False)
    state_machine: RuntimeStateMachine = field(init=False)
    running: bool = field(default=False, init=False)
    last_transcript: str | None = field(default=None, init=False)
    last_response: str | None = field(default=None, init=False)
    last_command_status: str | None = field(default=None, init=False)
    last_plan_source: str | None = field(default=None, init=False)
    last_routing_reason: str | None = field(default=None, init=False)
    last_planner_error: str | None = field(default=None, init=False)
    planner_consecutive_failures: int = field(default=0, init=False)
    planner_cooldown_until: float | None = field(default=None, init=False)
    last_undo_token: str | None = field(default=None, init=False)
    last_undo_tool: str | None = field(default=None, init=False)
    pending_confirmation_plan: object | None = field(default=None, init=False)
    pending_confirmation_started_at: float | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        if _adapter_set_is_empty(self.adapters):
            self.adapters = build_default_adapter_set(self.config)
        self.logger = configure_logging(self.config.logging)
        self.audit_store = AuditStore(self.config.paths.data_dir / "audit.sqlite3")
        self.executor = ActionExecutor(adapters=self.adapters)
        self.planner_routing_policy = PlannerRoutingPolicy(
            min_confidence=self.config.planner.min_confidence
        )
        if self.config.planner.enabled and self.planner_client is None:
            self.planner_client = PlannerServiceClient(
                PlannerServiceConfig(
                    endpoint=self.config.planner.endpoint,
                    model=self.config.planner.model,
                    timeout_seconds=self.config.planner.timeout_seconds,
                    max_retries=self.config.planner.max_retries,
                )
            )
        self.state_machine = RuntimeStateMachine(event_bus=self.event_bus)

    @classmethod
    def build_default(cls, env: Mapping[str, str] | None = None) -> "OperanceDaemon":
        config = AppConfig.from_env(env)
        adapters = build_default_adapter_set(config)
        return cls(config=config, adapters=adapters)

    def start(self) -> None:
        if self.running:
            return

        self.config.ensure_directories()
        self.running = True
        self.logger.info(
            "daemon_started",
            extra={
                "environment": self.config.environment,
                "state": self.state_machine.current_state.value,
                "data_dir": self.config.paths.data_dir,
            },
        )

    def stop(self) -> None:
        if not self.running:
            return

        self.running = False
        self.logger.info("daemon_stopped", extra={"state": self.state_machine.current_state.value})

    def complete_response_cycle(self) -> None:
        if self.state_machine.current_state != RuntimeState.RESPONDING:
            return

        self.state_machine.transition_to(RuntimeState.COOLDOWN, "response delivered")
        self.state_machine.transition_to(RuntimeState.IDLE, "cooldown completed")
        self.logger.info("response_cycle_completed", extra={"state": self.state_machine.current_state.value})

    def status_snapshot(self) -> StatusSnapshot:
        pending_plan = (
            self.pending_confirmation_plan
            if isinstance(self.pending_confirmation_plan, ActionPlan)
            else None
        )
        planner_context_messages = list(self.planner_context_window.active_messages())
        planner_cooldown_remaining_seconds = self.planner_cooldown_remaining_seconds()
        confirmation_metadata = build_confirmation_metadata(
            pending_plan,
            timeout_seconds=(
                self.config.runtime.confirmation_timeout_seconds if pending_plan is not None else None
            ),
        )
        return StatusSnapshot(
            current_state=self.state_machine.current_state,
            last_transcript=self.last_transcript,
            last_response=self.last_response,
            last_command_status=self.last_command_status,
            last_plan_source=self.last_plan_source,
            last_routing_reason=self.last_routing_reason,
            last_planner_error=self.last_planner_error,
            planner_consecutive_failures=self.planner_consecutive_failures,
            planner_cooldown_remaining_seconds=planner_cooldown_remaining_seconds,
            planner_context_entry_count=len(planner_context_messages),
            planner_context_messages=planner_context_messages,
            pending_confirmation=bool(confirmation_metadata["pending_confirmation"]),
            pending_plan_id=confirmation_metadata["pending_plan_id"],
            pending_plan_preview=confirmation_metadata["pending_plan_preview"],
            pending_original_text=confirmation_metadata["pending_original_text"],
            pending_source=confirmation_metadata["pending_source"],
            pending_risk_tier=confirmation_metadata["pending_risk_tier"],
            pending_action=confirmation_metadata["pending_action"],
            pending_affected_resources=list(confirmation_metadata["pending_affected_resources"]),
            pending_rollback_hint=confirmation_metadata["pending_rollback_hint"],
            pending_timeout_seconds=confirmation_metadata["pending_timeout_seconds"],
            pending_timeout_behavior=confirmation_metadata["pending_timeout_behavior"],
            undo_available=self.last_undo_token is not None,
            last_undo_tool=self.last_undo_tool,
            completed_commands=len(self.metrics.completed_commands),
            p95_latency_ms=self.metrics.p95_total_duration_ms(),
        )

    def planner_cooldown_remaining_seconds(self) -> float | None:
        if self.planner_cooldown_until is None:
            return None

        remaining_seconds = self.planner_cooldown_until - monotonic()
        if remaining_seconds <= 0:
            self.planner_cooldown_until = None
            return None

        return remaining_seconds

    def planner_cooldown_active(self) -> bool:
        return self.planner_cooldown_remaining_seconds() is not None

    def set_pending_confirmation(self, plan: ActionPlan) -> None:
        self.pending_confirmation_plan = plan
        self.pending_confirmation_started_at = monotonic()

    def clear_pending_confirmation(self) -> ActionPlan | None:
        plan = self.pending_confirmation_plan if isinstance(self.pending_confirmation_plan, ActionPlan) else None
        self.pending_confirmation_plan = None
        self.pending_confirmation_started_at = None
        return plan

    def pending_confirmation_has_expired(self) -> bool:
        if self.pending_confirmation_plan is None or self.pending_confirmation_started_at is None:
            return False
        return (
            monotonic() - self.pending_confirmation_started_at
        ) >= self.config.runtime.confirmation_timeout_seconds

    def undo_last_action(self) -> str | None:
        if self.last_undo_token is None:
            return None

        message = self.executor.undo(self.last_undo_token)
        self.last_response = message
        self.last_command_status = "undone"
        self._append_audit_entry(
            transcript=self.last_transcript or "",
            status="undone",
            tool=None,
            response_text=message,
        )
        self.last_undo_token = None
        self.last_undo_tool = None
        return message

    def reset_planner_runtime(self) -> str:
        self.planner_consecutive_failures = 0
        self.planner_cooldown_until = None
        self._set_routing_outcome(
            source=None,
            reason="planner_runtime_reset",
            planner_error=None,
        )
        message = "Planner runtime state reset."
        self.last_response = message
        self.last_command_status = "success"
        return message

    def emit_wake_detected(self, phrase: str | None = None) -> WakeEvent:
        event = WakeEvent(phrase=phrase)
        self.event_bus.publish(event)
        self.state_machine.transition_to(RuntimeState.WAKE_DETECTED, "wake word detected")
        self.logger.info("wake_detected", extra={"phrase": phrase})
        return event

    def begin_manual_listening(self, *, source: str = "manual") -> None:
        if self.state_machine.current_state == RuntimeState.AWAITING_CONFIRMATION:
            return
        if self.state_machine.current_state != RuntimeState.IDLE:
            return

        self.state_machine.transition_to(RuntimeState.LISTENING, f"{source} capture started")
        self.logger.info("manual_listening_started", extra={"source": source})

    def cancel_manual_listening(self, *, source: str = "manual") -> None:
        if self.state_machine.current_state != RuntimeState.LISTENING:
            return

        self.state_machine.transition_to(RuntimeState.COOLDOWN, f"{source} capture cancelled")
        self.state_machine.transition_to(RuntimeState.IDLE, f"{source} capture cancelled")
        self.logger.info("manual_listening_cancelled", extra={"source": source})

    def emit_transcript(
        self,
        text: str,
        *,
        confidence: float = 1.0,
        is_final: bool = True,
    ) -> TranscriptEvent:
        if self.state_machine.current_state in {RuntimeState.IDLE, RuntimeState.WAKE_DETECTED}:
            self.state_machine.transition_to(RuntimeState.LISTENING, "capturing transcript")

        self.state_machine.transition_to(RuntimeState.TRANSCRIBING, "transcript received")
        event = TranscriptEvent(text=text, confidence=confidence, is_final=is_final)
        self.event_bus.publish(event)
        self.logger.info(
            "transcript_received",
            extra={
                "text": text,
                "confidence": confidence,
                "is_final": is_final,
            },
        )
        self.last_transcript = text

        if is_final:
            total_started_at = perf_counter()
            pending_plan = self.pending_confirmation_plan if isinstance(self.pending_confirmation_plan, ActionPlan) else None
            if pending_plan is not None:
                if self.pending_confirmation_has_expired():
                    expired_plan = self.clear_pending_confirmation()
                    self.logger.info(
                        "pending_confirmation_expired",
                        extra={"plan_id": getattr(expired_plan, "plan_id", None)},
                    )
                    if _normalize_confirmation_reply(text) is not None:
                        return self._handle_expired_confirmation_reply(
                            text,
                            total_started_at,
                            event,
                            expired_plan,
                        )
                else:
                    return self._handle_confirmation_reply(text, total_started_at, event)
            planning_started_at = perf_counter()
            self.state_machine.transition_to(RuntimeState.UNDERSTANDING, "planning transcript")
            plan = self.intent_matcher.match(text)
            if plan is None:
                route_decision = self.planner_routing_policy.decide(
                    transcript=text,
                    deterministic_matched=False,
                    transcript_confidence=confidence,
                    is_final=is_final,
                )
                if route_decision.route == "planner" and self.planner_cooldown_active():
                    self._set_routing_outcome(
                        source=None,
                        reason="planner_cooldown_active",
                        planner_error=self.last_planner_error,
                    )
                elif route_decision.route == "planner" and self.planner_client is not None:
                    try:
                        planner_payload = self.planner_client.plan(
                            text,
                            context_window=self.planner_context_window,
                        )
                        plan = parse_planner_payload(planner_payload, original_text=text)
                        self._record_planner_success(plan.source.value, route_decision.reason)
                    except (PlannerClientError, PlannerParseError, ValueError) as exc:
                        self._record_planner_failure(str(exc))
                        self.logger.warning(
                            "planner_failed",
                            extra={"text": text, "reason": str(exc)},
                        )
                elif route_decision.route == "planner":
                    self._set_routing_outcome(
                        source=None,
                        reason="planner_unavailable",
                        planner_error="planner runtime unavailable",
                    )
                else:
                    self._set_routing_outcome(source=None, reason=route_decision.reason)
            else:
                self._set_routing_outcome(source=plan.source.value, reason="deterministic_match")
            planning_duration_ms = (perf_counter() - planning_started_at) * 1000

            if plan is not None:
                planned_event = ActionPlanEvent(plan=plan)
                self.event_bus.publish(planned_event)
                self.logger.info(
                    "action_plan_generated",
                    extra={
                        "plan_id": plan.plan_id,
                        "source": plan.source.value,
                        "tool": plan.actions[0].tool.value,
                    },
                )
                validation_result = self.validator.validate(plan)
                self.event_bus.publish(PlanValidationEvent(result=validation_result))
                if not validation_result.valid or validation_result.normalized_plan is None:
                    response_started_at = perf_counter()
                    response_text, response_status = self.response_builder.validation_failed()
                    response_event = ResponseEvent(text=response_text, status=response_status)
                    self.event_bus.publish(response_event)
                    self.logger.info(
                        "response_generated",
                        extra={
                            "status": response_status,
                            "text": response_text,
                            "validation_errors": validation_result.errors,
                        },
                    )
                    self.last_response = response_text
                    self.last_command_status = response_status
                    self._append_planner_context(text, response_text)
                    self._append_audit_entry(
                        transcript=text,
                        status=response_status,
                        tool=plan.actions[0].tool.value if plan.actions else None,
                        response_text=response_text,
                    )
                    response_duration_ms = (perf_counter() - response_started_at) * 1000
                    self.metrics.record(
                        CommandMetrics(
                            transcript=text,
                            matched=True,
                            total_duration_ms=(perf_counter() - total_started_at) * 1000,
                            planning_duration_ms=planning_duration_ms,
                            execution_duration_ms=None,
                            response_duration_ms=response_duration_ms,
                        )
                    )
                    self.state_machine.transition_to(RuntimeState.RESPONDING, "validation failed")
                    return event

                plan = validation_result.normalized_plan
                policy_decision = self.policy.decide(plan)
                if policy_decision.action == "deny":
                    response_started_at = perf_counter()
                    response_text, response_status = self.response_builder.validation_failed()
                    response_event = ResponseEvent(text=response_text, status=response_status)
                    self.event_bus.publish(response_event)
                    self.logger.info(
                        "response_generated",
                        extra={"status": response_status, "text": response_text, "policy": policy_decision.reason},
                    )
                    self.last_response = response_text
                    self.last_command_status = response_status
                    self._append_planner_context(text, response_text)
                    self._append_audit_entry(
                        transcript=text,
                        status=response_status,
                        tool=plan.actions[0].tool.value if plan.actions else None,
                        response_text=response_text,
                    )
                    response_duration_ms = (perf_counter() - response_started_at) * 1000
                    self.metrics.record(
                        CommandMetrics(
                            transcript=text,
                            matched=True,
                            total_duration_ms=(perf_counter() - total_started_at) * 1000,
                            planning_duration_ms=planning_duration_ms,
                            execution_duration_ms=None,
                            response_duration_ms=response_duration_ms,
                        )
                    )
                    self.state_machine.transition_to(RuntimeState.RESPONDING, "policy denied")
                    return event

                if policy_decision.action == "require_confirmation":
                    self.set_pending_confirmation(plan)
                    response_started_at = perf_counter()
                    response_text, response_status = self.response_builder.confirmation_required()
                    response_event = ResponseEvent(
                        text=response_text,
                        status=response_status,
                        plan_id=plan.plan_id,
                    )
                    self.event_bus.publish(response_event)
                    self.logger.info(
                        "response_generated",
                        extra={"status": response_status, "text": response_text, "policy": policy_decision.reason},
                    )
                    self.last_response = response_text
                    self.last_command_status = response_status
                    self._append_planner_context(text, response_text)
                    self._append_audit_entry(
                        transcript=text,
                        status=response_status,
                        tool=plan.actions[0].tool.value if plan.actions else None,
                        response_text=response_text,
                    )
                    response_duration_ms = (perf_counter() - response_started_at) * 1000
                    self.metrics.record(
                        CommandMetrics(
                            transcript=text,
                            matched=True,
                            total_duration_ms=(perf_counter() - total_started_at) * 1000,
                            planning_duration_ms=planning_duration_ms,
                            execution_duration_ms=None,
                            response_duration_ms=response_duration_ms,
                        )
                    )
                    self.state_machine.transition_to(
                        RuntimeState.AWAITING_CONFIRMATION,
                        "policy requires confirmation",
                    )
                    return event

                self.clear_pending_confirmation()
                self.state_machine.transition_to(RuntimeState.EXECUTING, "executing typed plan")
                execution_started_at = perf_counter()
                result = self.executor.execute(plan)
                execution_duration_ms = (perf_counter() - execution_started_at) * 1000
                result_event = ActionResultEvent(result=result)
                self.event_bus.publish(result_event)
                self.last_undo_token = result.results[0].undo_token if result.results else None
                self.last_undo_tool = (
                    result.results[0].tool.value
                    if result.results and result.results[0].undo_token is not None
                    else None
                )
                self.logger.info(
                    "action_result_generated",
                    extra={
                        "plan_id": result.plan_id,
                        "status": result.status,
                        "tool": result.results[0].tool.value if result.results else None,
                    },
                )
                response_started_at = perf_counter()
                response_text, response_status = self.response_builder.from_action_result(result)
                response_event = ResponseEvent(
                    text=response_text,
                    status=response_status,
                    plan_id=result.plan_id,
                )
                self.event_bus.publish(response_event)
                self.logger.info(
                    "response_generated",
                    extra={"plan_id": result.plan_id, "status": response_status, "text": response_text},
                )
                self.last_response = response_text
                self.last_command_status = response_status
                self._append_planner_context(text, response_text)
                self._append_audit_entry(
                    transcript=text,
                    status=response_status,
                    tool=result.results[0].tool.value if result.results else None,
                    response_text=response_text,
                )
                response_duration_ms = (perf_counter() - response_started_at) * 1000
                self.metrics.record(
                    CommandMetrics(
                        transcript=text,
                        matched=True,
                        total_duration_ms=(perf_counter() - total_started_at) * 1000,
                        planning_duration_ms=planning_duration_ms,
                        execution_duration_ms=execution_duration_ms,
                        response_duration_ms=response_duration_ms,
                    )
                )
                self.state_machine.transition_to(RuntimeState.RESPONDING, "execution completed")
            else:
                response_started_at = perf_counter()
                response_text, response_status = self.response_builder.unmatched()
                response_event = ResponseEvent(text=response_text, status=response_status)
                self.event_bus.publish(response_event)
                self.logger.info(
                    "response_generated",
                    extra={"status": response_status, "text": response_text},
                )
                self.last_response = response_text
                self.last_command_status = response_status
                self._append_planner_context(text, response_text)
                self._append_audit_entry(
                    transcript=text,
                    status=response_status,
                    tool=None,
                    response_text=response_text,
                )
                response_duration_ms = (perf_counter() - response_started_at) * 1000
                self.metrics.record(
                    CommandMetrics(
                        transcript=text,
                        matched=False,
                        total_duration_ms=(perf_counter() - total_started_at) * 1000,
                        planning_duration_ms=planning_duration_ms,
                        execution_duration_ms=None,
                        response_duration_ms=response_duration_ms,
                    )
                )
                self.state_machine.transition_to(RuntimeState.RESPONDING, "no deterministic match")

        return event

    def _handle_confirmation_reply(
        self,
        transcript: str,
        total_started_at: float,
        event: TranscriptEvent,
    ) -> TranscriptEvent:
        self.state_machine.transition_to(
            RuntimeState.UNDERSTANDING,
            "processing confirmation reply",
        )
        reply = _normalize_confirmation_reply(transcript)
        plan = self.pending_confirmation_plan if isinstance(self.pending_confirmation_plan, ActionPlan) else None
        planning_duration_ms = (perf_counter() - total_started_at) * 1000

        if reply == "confirm" and plan is not None:
            self._set_routing_outcome(source=plan.source.value, reason="confirmation_reply_confirm")
            self.clear_pending_confirmation()
            self.state_machine.transition_to(RuntimeState.EXECUTING, "confirmation received")
            self._execute_plan(
                plan,
                transcript=transcript,
                total_started_at=total_started_at,
                planning_duration_ms=planning_duration_ms,
            )
            return event

        if reply == "cancel":
            self._set_routing_outcome(
                source=plan.source.value if plan is not None else None,
                reason="confirmation_reply_cancel",
            )
            self.clear_pending_confirmation()
            response_started_at = perf_counter()
            response_text, response_status = self.response_builder.confirmation_cancelled()
            response_event = ResponseEvent(
                text=response_text,
                status=response_status,
                plan_id=getattr(plan, "plan_id", None),
            )
            self.event_bus.publish(response_event)
            self.logger.info(
                "response_generated",
                extra={"status": response_status, "text": response_text},
            )
            self.last_response = response_text
            self.last_command_status = response_status
            self._append_planner_context(transcript, response_text)
            self._append_audit_entry(
                transcript=transcript,
                status=response_status,
                tool=plan.actions[0].tool.value if plan is not None and plan.actions else None,
                response_text=response_text,
            )
            response_duration_ms = (perf_counter() - response_started_at) * 1000
            self.metrics.record(
                CommandMetrics(
                    transcript=transcript,
                    matched=True,
                    total_duration_ms=(perf_counter() - total_started_at) * 1000,
                    planning_duration_ms=planning_duration_ms,
                    execution_duration_ms=None,
                    response_duration_ms=response_duration_ms,
                )
            )
            self.state_machine.transition_to(RuntimeState.RESPONDING, "confirmation cancelled")
            return event

        response_started_at = perf_counter()
        self._set_routing_outcome(
            source=plan.source.value if plan is not None else None,
            reason="confirmation_reply_unrecognized",
        )
        response_text, response_status = self.response_builder.confirmation_still_pending()
        response_event = ResponseEvent(
            text=response_text,
            status=response_status,
            plan_id=getattr(plan, "plan_id", None),
        )
        self.event_bus.publish(response_event)
        self.logger.info(
            "response_generated",
            extra={"status": response_status, "text": response_text},
        )
        self.last_response = response_text
        self.last_command_status = response_status
        self._append_planner_context(transcript, response_text)
        self._append_audit_entry(
            transcript=transcript,
            status=response_status,
            tool=plan.actions[0].tool.value if plan is not None and plan.actions else None,
            response_text=response_text,
        )
        response_duration_ms = (perf_counter() - response_started_at) * 1000
        self.metrics.record(
            CommandMetrics(
                transcript=transcript,
                matched=True,
                total_duration_ms=(perf_counter() - total_started_at) * 1000,
                planning_duration_ms=planning_duration_ms,
                execution_duration_ms=None,
                response_duration_ms=response_duration_ms,
            )
        )
        self.state_machine.transition_to(
            RuntimeState.AWAITING_CONFIRMATION,
            "confirmation reply not recognized",
        )
        return event

    def _handle_expired_confirmation_reply(
        self,
        transcript: str,
        total_started_at: float,
        event: TranscriptEvent,
        plan: ActionPlan | None,
    ) -> TranscriptEvent:
        self.state_machine.transition_to(
            RuntimeState.UNDERSTANDING,
            "pending confirmation expired",
        )
        self._set_routing_outcome(
            source=plan.source.value if plan is not None else None,
            reason="confirmation_reply_expired",
        )
        planning_duration_ms = (perf_counter() - total_started_at) * 1000
        response_started_at = perf_counter()
        response_text, response_status = self.response_builder.confirmation_expired()
        response_event = ResponseEvent(
            text=response_text,
            status=response_status,
            plan_id=getattr(plan, "plan_id", None),
        )
        self.event_bus.publish(response_event)
        self.logger.info(
            "response_generated",
            extra={"status": response_status, "text": response_text},
        )
        self.last_response = response_text
        self.last_command_status = response_status
        self._append_planner_context(transcript, response_text)
        self._append_audit_entry(
            transcript=transcript,
            status=response_status,
            tool=plan.actions[0].tool.value if plan is not None and plan.actions else None,
            response_text=response_text,
        )
        response_duration_ms = (perf_counter() - response_started_at) * 1000
        self.metrics.record(
            CommandMetrics(
                transcript=transcript,
                matched=True,
                total_duration_ms=(perf_counter() - total_started_at) * 1000,
                planning_duration_ms=planning_duration_ms,
                execution_duration_ms=None,
                response_duration_ms=response_duration_ms,
            )
        )
        self.state_machine.transition_to(RuntimeState.RESPONDING, "pending confirmation expired")
        return event

    def _execute_plan(
        self,
        plan: object,
        *,
        transcript: str,
        total_started_at: float,
        planning_duration_ms: float,
    ) -> None:
        execution_started_at = perf_counter()
        result = self.executor.execute(plan)
        execution_duration_ms = (perf_counter() - execution_started_at) * 1000
        result_event = ActionResultEvent(result=result)
        self.event_bus.publish(result_event)
        self.last_undo_token = result.results[0].undo_token if result.results else None
        self.last_undo_tool = (
            result.results[0].tool.value
            if result.results and result.results[0].undo_token is not None
            else None
        )
        self.logger.info(
            "action_result_generated",
            extra={
                "plan_id": result.plan_id,
                "status": result.status,
                "tool": result.results[0].tool.value if result.results else None,
            },
        )
        response_started_at = perf_counter()
        response_text, response_status = self.response_builder.from_action_result(result)
        response_event = ResponseEvent(
            text=response_text,
            status=response_status,
            plan_id=result.plan_id,
        )
        self.event_bus.publish(response_event)
        self.logger.info(
            "response_generated",
            extra={"plan_id": result.plan_id, "status": response_status, "text": response_text},
        )
        self.last_response = response_text
        self.last_command_status = response_status
        self._append_planner_context(transcript, response_text)
        self._append_audit_entry(
            transcript=transcript,
            status=response_status,
            tool=result.results[0].tool.value if result.results else None,
            response_text=response_text,
        )
        response_duration_ms = (perf_counter() - response_started_at) * 1000
        self.metrics.record(
            CommandMetrics(
                transcript=transcript,
                matched=True,
                total_duration_ms=(perf_counter() - total_started_at) * 1000,
                planning_duration_ms=planning_duration_ms,
                execution_duration_ms=execution_duration_ms,
                response_duration_ms=response_duration_ms,
            )
        )
        self.state_machine.transition_to(RuntimeState.RESPONDING, "execution completed")

    def _append_planner_context(self, transcript: str, response_text: str) -> None:
        self.planner_context_window.add("user", transcript)
        self.planner_context_window.add("assistant", response_text)

    def _record_planner_success(self, source: str, reason: str) -> None:
        self.planner_consecutive_failures = 0
        self.planner_cooldown_until = None
        self._set_routing_outcome(source=source, reason=reason, planner_error=None)

    def _record_planner_failure(self, planner_error: str) -> None:
        self.planner_consecutive_failures += 1
        if (
            self.config.planner.max_consecutive_failures > 0
            and self.planner_consecutive_failures >= self.config.planner.max_consecutive_failures
            and self.config.planner.failure_cooldown_seconds > 0
        ):
            self.planner_cooldown_until = monotonic() + self.config.planner.failure_cooldown_seconds
        self._set_routing_outcome(
            source=None,
            reason="planner_failed",
            planner_error=planner_error,
        )

    def _append_audit_entry(
        self,
        *,
        transcript: str,
        status: str,
        tool: str | None,
        response_text: str | None,
    ) -> None:
        self.audit_store.append(
            AuditEntry(
                transcript=transcript,
                status=status,
                tool=tool,
                response_text=response_text,
                plan_source=self.last_plan_source,
                routing_reason=self.last_routing_reason,
                planner_error=self.last_planner_error,
            )
        )

    def _set_routing_outcome(
        self,
        *,
        source: str | None,
        reason: str | None,
        planner_error: str | None = None,
    ) -> None:
        self.last_plan_source = source
        self.last_routing_reason = reason
        self.last_planner_error = planner_error


def _adapter_set_is_empty(adapters: AdapterSet) -> bool:
    return all(
        getattr(adapters, field_name) is None
        for field_name in (
            "apps",
            "windows",
            "time",
            "power",
            "audio",
            "clipboard",
            "text_input",
            "network",
            "notifications",
            "files",
        )
    )


def _normalize_confirmation_reply(text: str) -> str | None:
    normalized = " ".join(text.lower().split())
    if normalized in {"confirm", "yes", "yes please", "proceed", "do it"}:
        return "confirm"
    if normalized in {"cancel", "no", "stop", "never mind"}:
        return "cancel"
    return None
