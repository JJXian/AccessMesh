import httpx
import pytest

from accessmesh.config import Settings
from accessmesh.policy.client import OpaPolicyClient


@pytest.mark.asyncio
async def test_policy_client_parses_opa_decision() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "result": {
                    "allow": True,
                    "risk_level": "medium",
                    "violations": [],
                    "required_approvals": ["approver"],
                    "max_duration_days": 30,
                    "policy_version": "test",
                }
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        decision = await OpaPolicyClient(Settings(), client).evaluate({"subject": {}})

    assert decision.allow is True
    assert decision.required_approvals == ["approver"]
