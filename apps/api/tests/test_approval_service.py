"""人工审批业务服务测试。"""

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from accessmesh.approval.service import (
    ApprovalConflictError,
    ApprovalValidationError,
    decide_approval,
)
from accessmesh.db.models import AccessRequest
from accessmesh.domain.enums import ApprovalDecision, RequestStatus
from accessmesh.domain.schemas import ApprovalCreate


def build_pending_request() -> AccessRequest:
    """构造一条可供审批的申请记录。"""

    return AccessRequest(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        requester_external_id="user-requester",
        subject_external_id="user-requester",
        raw_request="申请支付测试数据库查询权限，有效期 3 天。",
        client_request_id="test-request-001",
        status=RequestStatus.PENDING_APPROVAL,
        trace_id="trace-test-001",
    )


@pytest.mark.asyncio
async def test_approve_pending_request_updates_status_and_records_audit() -> None:
    """通过审批应创建审批记录、更新申请状态并写入审计事件。"""

    request = build_pending_request()

    session = MagicMock()
    session.get = AsyncMock(return_value=request)
    session.scalar = AsyncMock(return_value=None)
    session.flush = AsyncMock()

    approval = await decide_approval(
        session=session,
        request_id=request.id,
        approver_external_id="user-approver",
        payload=ApprovalCreate(
            decision=ApprovalDecision.APPROVED,
            comment="同意用于支付问题排查。",
        ),
    )

    assert approval.request_id == request.id
    assert approval.approver_external_id == "user-approver"
    assert approval.decision == ApprovalDecision.APPROVED
    assert approval.comment == "同意用于支付问题排查。"
    assert request.status == RequestStatus.APPROVED
    assert session.add.call_count == 2
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_rejection_requires_comment() -> None:
    """拒绝申请时必须填写审批意见。"""

    request = build_pending_request()

    session = MagicMock()
    session.get = AsyncMock(return_value=request)
    session.scalar = AsyncMock(return_value=None)
    session.flush = AsyncMock()

    with pytest.raises(
        ApprovalValidationError,
        match="拒绝申请时必须填写审批意见。",
    ):
        await decide_approval(
            session=session,
            request_id=request.id,
            approver_external_id="user-approver",
            payload=ApprovalCreate(
                decision=ApprovalDecision.REJECTED,
                comment="   ",
            ),
        )

    assert request.status == RequestStatus.PENDING_APPROVAL
    session.add.assert_not_called()
    session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_cannot_approve_request_that_is_not_pending() -> None:
    """非待审批状态的申请必须拒绝再次审批。"""

    request = build_pending_request()
    request.status = RequestStatus.APPROVED

    session = MagicMock()
    session.get = AsyncMock(return_value=request)

    with pytest.raises(
        ApprovalConflictError,
        match="当前申请状态为 APPROVED，不能执行审批。",
    ):
        await decide_approval(
            session=session,
            request_id=request.id,
            approver_external_id="user-approver",
            payload=ApprovalCreate(
                decision=ApprovalDecision.APPROVED,
            ),
        )

    session.scalar.assert_not_called()
    session.add.assert_not_called()
