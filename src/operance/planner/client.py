"""Offline service-client contracts for local planner requests."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Mapping
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

from .context import PlannerContextWindow
from .prompt import build_planner_messages
from .schema import build_planner_payload_schema


@dataclass(slots=True, frozen=True)
class PlannerServiceConfig:
    endpoint: str = "http://127.0.0.1:8080/v1/chat/completions"
    model: str = "qwen2.5-7b-instruct"
    temperature: float = 0.0
    timeout_seconds: float = 30.0
    max_retries: int = 1


@dataclass(slots=True)
class PlannerClientError(ValueError):
    message: str

    def __str__(self) -> str:
        return self.message


@dataclass(slots=True)
class PlannerServiceClient:
    config: PlannerServiceConfig = PlannerServiceConfig()

    def build_messages(
        self,
        transcript: str,
        *,
        context_window: PlannerContextWindow | None = None,
        now: datetime | None = None,
    ) -> list[dict[str, str]]:
        messages = build_planner_messages(transcript)
        if context_window is not None:
            messages = [
                messages[0],
                *context_window.active_messages(now=now),
                messages[-1],
            ]
        return messages

    def plan(
        self,
        transcript: str,
        *,
        context_window: PlannerContextWindow | None = None,
        now: datetime | None = None,
    ) -> dict[str, object]:
        request_payload = self.build_request(transcript, context_window=context_window, now=now)
        body = json.dumps(request_payload).encode("utf-8")
        request = Request(
            self.config.endpoint,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        raw_response = self._read_response_bytes(request, error_label="planner request")

        try:
            parsed_response = json.loads(raw_response.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PlannerClientError("planner response was not valid JSON") from exc

        if not isinstance(parsed_response, dict):
            raise PlannerClientError("planner response must decode to a JSON object")

        return self.extract_payload(parsed_response)

    def health(self) -> dict[str, object]:
        errors: list[dict[str, str]] = []

        for probe_name, probe_url in (
            ("models", self._models_probe_url()),
            ("health", self._health_probe_url()),
        ):
            request = Request(probe_url, headers={"Accept": "application/json"}, method="GET")
            try:
                raw_response = self._read_response_bytes(
                    request,
                    error_label=f"planner {probe_name} probe",
                )
            except PlannerClientError as exc:
                errors.append({"probe": probe_name, "probe_url": probe_url, "message": str(exc)})
                continue

            if probe_name == "models":
                try:
                    parsed_response = json.loads(raw_response.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    errors.append(
                        {
                            "probe": probe_name,
                            "probe_url": probe_url,
                            "message": "planner models probe was not valid JSON",
                        }
                    )
                    continue

                model_ids = _extract_model_ids(parsed_response)
                if model_ids:
                    return {
                        "status": "ok",
                        "endpoint": self.config.endpoint,
                        "probe": probe_name,
                        "probe_url": probe_url,
                        "model_ids": model_ids,
                    }

                errors.append(
                    {
                        "probe": probe_name,
                        "probe_url": probe_url,
                        "message": "planner models probe did not expose model ids",
                    }
                )
                continue

            detail = raw_response.decode("utf-8", errors="replace").strip() or "ok"
            return {
                "status": "ok",
                "endpoint": self.config.endpoint,
                "probe": probe_name,
                "probe_url": probe_url,
                "detail": detail,
            }

        return {
            "status": "failed",
            "endpoint": self.config.endpoint,
            "errors": errors,
        }

    def build_request(
        self,
        transcript: str,
        *,
        context_window: PlannerContextWindow | None = None,
        now: datetime | None = None,
    ) -> dict[str, object]:
        return {
            "model": self.config.model,
            "temperature": self.config.temperature,
            "messages": self.build_messages(transcript, context_window=context_window, now=now),
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "operance_action_plan",
                    "schema": build_planner_payload_schema(),
                },
            },
        }

    def extract_payload(self, response: Mapping[str, object]) -> dict[str, object]:
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices:
            raise PlannerClientError("missing planner response content")

        first_choice = choices[0]
        if not isinstance(first_choice, Mapping):
            raise PlannerClientError("missing planner response content")

        message = first_choice.get("message")
        if not isinstance(message, Mapping):
            raise PlannerClientError("missing planner response content")

        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise PlannerClientError("missing planner response content")

        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise PlannerClientError("planner response must decode to a JSON object")
        return parsed

    def _read_response_bytes(self, request: Request, *, error_label: str) -> bytes:
        last_error: OSError | None = None
        for _ in range(self.config.max_retries + 1):
            try:
                with urlopen(request, timeout=self.config.timeout_seconds) as response:
                    return response.read()
            except OSError as exc:
                last_error = exc

        if last_error is not None:
            raise PlannerClientError(f"{error_label} failed: {last_error}") from last_error

        raise PlannerClientError(f"{error_label} failed")

    def _models_probe_url(self) -> str:
        split = urlsplit(self.config.endpoint)
        base_path = _planner_base_path(split.path)
        probe_path = f"{base_path}/v1/models" if base_path else "/v1/models"
        return urlunsplit(split._replace(path=probe_path, query="", fragment=""))

    def _health_probe_url(self) -> str:
        split = urlsplit(self.config.endpoint)
        base_path = _planner_base_path(split.path)
        probe_path = f"{base_path}/health" if base_path else "/health"
        return urlunsplit(split._replace(path=probe_path, query="", fragment=""))


def _planner_base_path(endpoint_path: str) -> str:
    normalized = endpoint_path.rstrip("/")
    for suffix in ("/v1/chat/completions", "/chat/completions"):
        if normalized.endswith(suffix):
            return normalized[: -len(suffix)]
    return ""


def _extract_model_ids(payload: object) -> list[str]:
    if not isinstance(payload, Mapping):
        return []

    data = payload.get("data")
    if not isinstance(data, list):
        return []

    model_ids = [
        str(item["id"])
        for item in data
        if isinstance(item, Mapping) and isinstance(item.get("id"), str)
    ]
    return model_ids
