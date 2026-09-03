"""最小权限规划器的单元测试。"""

from accessmesh.domain.enums import Environment, ResourceType
from accessmesh.domain.schemas import ParsedIntent, ResourceRead
from accessmesh.planning.basic_planner import BasicPlanner


def build_test_database_resource() -> ResourceRead:
    """构造一个测试数据库资源，供多个测试复用。"""

    return ResourceRead(
        id="11111111-1111-1111-1111-111111111111",
        external_id="database:payment-test",
        name="支付测试数据库",
        resource_type=ResourceType.DATABASE,
        environment=Environment.TEST,
        sensitivity="L2",
        owner_external_id="user-approver",
        allowed_permissions=["connect", "read_only", "read_write"],
        enabled=True,
    )


def test_planner_recommends_read_only_for_read_request() -> None:
    """只读需求应得到 read_only，而不是 read_write。"""

    planner = BasicPlanner()
    result = planner.create_plan(
        intent=ParsedIntent(
            task="排查支付接口异常",
            resource_hints=["支付测试数据库"],
            action_hints=["查询"],
            duration_days=3,
        ),
        resources=[build_test_database_resource()],
    )

    assert len(result.grants) == 1
    assert result.grants[0].resource_external_id == "database:payment-test"
    assert result.grants[0].permission == "read_only"
    assert result.grants[0].duration_days == 3
    assert result.assumptions == []


def test_planner_recommends_read_write_for_write_request() -> None:
    """写入需求可推荐资源允许的 read_write 权限。"""

    planner = BasicPlanner()
    result = planner.create_plan(
        intent=ParsedIntent(
            task="修复测试数据",
            resource_hints=["database:payment-test"],
            action_hints=["更新"],
            duration_days=1,
        ),
        resources=[build_test_database_resource()],
    )

    assert len(result.grants) == 1
    assert result.grants[0].permission == "read_write"


def test_planner_returns_empty_plan_when_resource_is_missing() -> None:
    """资源不存在时不能猜测授权目标，必须返回空方案。"""

    planner = BasicPlanner()
    result = planner.create_plan(
        intent=ParsedIntent(
            task="查看订单信息",
            resource_hints=["不存在的数据库"],
            action_hints=["查询"],
            duration_days=1,
        ),
        resources=[build_test_database_resource()],
    )

    assert result.grants == []
    assert result.assumptions == ["资源目录中未找到与申请匹配的目标资源。"]


def test_planner_uses_seven_days_when_duration_is_missing() -> None:
    """未提供时长时先使用可审计的默认建议，并记录假设。"""

    planner = BasicPlanner()
    result = planner.create_plan(
        intent=ParsedIntent(
            task="排查支付接口异常",
            resource_hints=["支付测试数据库"],
            action_hints=["查询"],
        ),
        resources=[build_test_database_resource()],
    )

    assert result.grants[0].duration_days == 7
    assert result.assumptions == ["申请未明确授权时长，暂按 7 天生成候选方案。"]
