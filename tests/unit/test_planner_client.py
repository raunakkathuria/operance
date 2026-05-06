import json


def test_planner_service_client_builds_llamacpp_chat_request() -> None:
    from operance.planner.client import PlannerServiceClient, PlannerServiceConfig

    client = PlannerServiceClient(PlannerServiceConfig(model="qwen-test"))

    request = client.build_request("open firefox")

    assert request["model"] == "qwen-test"
    assert request["temperature"] == 0.0
    assert request["messages"][-1] == {"role": "user", "content": "open firefox"}
    assert request["response_format"]["type"] == "json_schema"
    assert request["response_format"]["json_schema"]["name"] == "operance_action_plan"
    assert request["response_format"]["json_schema"]["schema"]["properties"]["actions"]["maxItems"] == 2


def test_planner_service_client_retries_transport_failure_once_and_succeeds(monkeypatch) -> None:
    from operance.planner.client import PlannerServiceClient, PlannerServiceConfig

    attempts = {"count": 0}

    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {"actions": [{"tool": "apps.launch", "args": {"app": "firefox"}}]}
                                )
                            }
                        }
                    ]
                }
            ).encode("utf-8")

    def fake_urlopen(request, timeout: float):  # type: ignore[no-untyped-def]
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise OSError("connection refused")
        return FakeResponse()

    monkeypatch.setattr("operance.planner.client.urlopen", fake_urlopen)

    client = PlannerServiceClient(PlannerServiceConfig(max_retries=1))

    payload = client.plan("open firefox")

    assert attempts["count"] == 2
    assert payload == {"actions": [{"tool": "apps.launch", "args": {"app": "firefox"}}]}


def test_planner_service_client_includes_recent_context_messages() -> None:
    from datetime import UTC, datetime

    from operance.planner.client import PlannerServiceClient
    from operance.planner.context import PlannerContextWindow

    window = PlannerContextWindow(ttl_seconds=300, max_entries=4)
    window.add("user", "open firefox", now=datetime(2026, 4, 14, 12, 0, tzinfo=UTC))
    window.add("assistant", "Planned action: launch firefox.", now=datetime(2026, 4, 14, 12, 0, 1, tzinfo=UTC))

    client = PlannerServiceClient()
    request = client.build_request("also notify me", context_window=window, now=datetime(2026, 4, 14, 12, 0, 2, tzinfo=UTC))

    assert request["messages"][1] == {"role": "user", "content": "open firefox"}
    assert request["messages"][2] == {"role": "assistant", "content": "Planned action: launch firefox."}
    assert request["messages"][-1] == {"role": "user", "content": "also notify me"}


def test_planner_service_client_build_messages_includes_recent_context_messages() -> None:
    from datetime import UTC, datetime

    from operance.planner.client import PlannerServiceClient
    from operance.planner.context import PlannerContextWindow

    window = PlannerContextWindow(ttl_seconds=300, max_entries=4)
    window.add("user", "open firefox", now=datetime(2026, 4, 14, 12, 0, tzinfo=UTC))
    window.add("assistant", "Planned action: launch firefox.", now=datetime(2026, 4, 14, 12, 0, 1, tzinfo=UTC))

    client = PlannerServiceClient()
    messages = client.build_messages("also notify me", context_window=window, now=datetime(2026, 4, 14, 12, 0, 2, tzinfo=UTC))

    assert messages[1] == {"role": "user", "content": "open firefox"}
    assert messages[2] == {"role": "assistant", "content": "Planned action: launch firefox."}
    assert messages[-1] == {"role": "user", "content": "also notify me"}


def test_planner_service_client_extracts_payload_from_openai_response() -> None:
    from operance.planner.client import PlannerServiceClient

    client = PlannerServiceClient()

    payload = client.extract_payload(
        {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "actions": [
                                    {"tool": "apps.launch", "args": {"app": "firefox"}},
                                ]
                            }
                        )
                    }
                }
            ]
        }
    )

    assert payload == {
        "actions": [
            {"tool": "apps.launch", "args": {"app": "firefox"}},
        ]
    }


def test_planner_service_client_rejects_missing_response_content() -> None:
    import pytest

    from operance.planner.client import PlannerClientError, PlannerServiceClient

    client = PlannerServiceClient()

    with pytest.raises(PlannerClientError, match="missing planner response content"):
        client.extract_payload({"choices": [{"message": {}}]})


def test_planner_service_client_posts_request_and_extracts_payload(monkeypatch) -> None:
    from operance.planner.client import PlannerServiceClient, PlannerServiceConfig

    seen: dict[str, object] = {}

    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {"actions": [{"tool": "apps.launch", "args": {"app": "firefox"}}]}
                                )
                            }
                        }
                    ]
                }
            ).encode("utf-8")

    def fake_urlopen(request, timeout: float):  # type: ignore[no-untyped-def]
        seen["url"] = request.full_url
        seen["content_type"] = request.get_header("Content-type")
        seen["payload"] = json.loads(request.data.decode("utf-8"))
        seen["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("operance.planner.client.urlopen", fake_urlopen)

    client = PlannerServiceClient(
        PlannerServiceConfig(
            endpoint="http://127.0.0.1:8081/v1/chat/completions",
            model="qwen-test",
            timeout_seconds=12.5,
        )
    )

    payload = client.plan("open firefox")

    assert seen["url"] == "http://127.0.0.1:8081/v1/chat/completions"
    assert seen["content_type"] == "application/json"
    assert seen["payload"]["model"] == "qwen-test"
    assert seen["payload"]["messages"][-1] == {"role": "user", "content": "open firefox"}
    assert seen["timeout"] == 12.5
    assert payload == {"actions": [{"tool": "apps.launch", "args": {"app": "firefox"}}]}


def test_planner_service_client_health_prefers_models_probe(monkeypatch) -> None:
    from operance.planner.client import PlannerServiceClient, PlannerServiceConfig

    seen_urls: list[str] = []

    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps({"data": [{"id": "qwen-test"}]}).encode("utf-8")

    def fake_urlopen(request, timeout: float):  # type: ignore[no-untyped-def]
        seen_urls.append(request.full_url)
        return FakeResponse()

    monkeypatch.setattr("operance.planner.client.urlopen", fake_urlopen)

    client = PlannerServiceClient(
        PlannerServiceConfig(endpoint="http://127.0.0.1:8081/v1/chat/completions", max_retries=0)
    )

    result = client.health()

    assert result == {
        "endpoint": "http://127.0.0.1:8081/v1/chat/completions",
        "model_ids": ["qwen-test"],
        "probe": "models",
        "probe_url": "http://127.0.0.1:8081/v1/models",
        "status": "ok",
    }
    assert seen_urls == ["http://127.0.0.1:8081/v1/models"]


def test_planner_service_client_health_falls_back_to_health_probe(monkeypatch) -> None:
    from operance.planner.client import PlannerServiceClient, PlannerServiceConfig

    seen_urls: list[str] = []

    class FakeResponse:
        def __init__(self, body: bytes) -> None:
            self._body = body

        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def read(self) -> bytes:
            return self._body

    def fake_urlopen(request, timeout: float):  # type: ignore[no-untyped-def]
        seen_urls.append(request.full_url)
        if request.full_url.endswith("/v1/models"):
            raise OSError("connection refused")
        return FakeResponse(b"ok\n")

    monkeypatch.setattr("operance.planner.client.urlopen", fake_urlopen)

    client = PlannerServiceClient(
        PlannerServiceConfig(endpoint="http://127.0.0.1:8081/v1/chat/completions", max_retries=0)
    )

    result = client.health()

    assert result == {
        "detail": "ok",
        "endpoint": "http://127.0.0.1:8081/v1/chat/completions",
        "probe": "health",
        "probe_url": "http://127.0.0.1:8081/health",
        "status": "ok",
    }
    assert seen_urls == [
        "http://127.0.0.1:8081/v1/models",
        "http://127.0.0.1:8081/health",
    ]
