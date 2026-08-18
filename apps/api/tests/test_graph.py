import pytest

from accessmesh.graph.workflow import build_access_request_graph


@pytest.mark.asyncio
async def test_scaffold_graph_reaches_ready_state() -> None:
    graph = build_access_request_graph()
    result = await graph.ainvoke({"raw_request": "申请测试库只读权限"})

    assert result["status"] == "SCAFFOLD_READY"
    assert result["parsed_intent"]["requires_llm_planning"] is True
