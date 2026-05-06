import io
import json

from operance.config import LoggingSettings
from operance.logger import configure_logging


def test_json_logger_emits_structured_payload() -> None:
    stream = io.StringIO()
    logger = configure_logging(LoggingSettings(level="INFO", json=True), stream=stream)

    logger.info("daemon_started", extra={"component": "test", "attempt": 1})

    payload = json.loads(stream.getvalue())
    assert payload["message"] == "daemon_started"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "operance"
    assert payload["extra"] == {"attempt": 1, "component": "test"}
