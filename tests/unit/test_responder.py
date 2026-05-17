from operance.models.actions import ActionResult, ActionResultItem, ToolName
from operance.responder import ResponseBuilder


def test_response_builder_joins_multiple_success_messages() -> None:
    result = ActionResult(
        plan_id="plan-1",
        status="success",
        results=[
            ActionResultItem(tool=ToolName.APPS_LAUNCH, status="success", message="Launched firefox"),
            ActionResultItem(tool=ToolName.APPS_LAUNCH, status="success", message="Opened http://localhost:3000"),
        ],
    )

    response, status = ResponseBuilder().from_action_result(result)

    assert status == "success"
    assert response == "Launched firefox. Opened http://localhost:3000"
