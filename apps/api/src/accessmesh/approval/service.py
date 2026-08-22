"""权限申请人工审批的核心业务逻辑。"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from accessmesh.db.models import AccessRequest, Approval, AuditEvent
from accessmesh.domain.enums import ApprovalDecision, RequestStatus
from accessmesh.domain.schemas import ApprovalCreate


class ApprovalNotFoundError(LookupError):
    """尝试审批不存在的申请时抛出的异常。"""


class ApprovalConflictError(ValueError):
    """申请状态不允许审批或已经审批过时抛出的异常。"""


class ApprovalValidationError(ValueError):
    """审批内容不满足业务规则时抛出的异常。"""


async def decide_approval(
    session: AsyncSession,
    request_id: UUID,
    approver_external_id: str,
    payload: ApprovalCreate,
) -> Approval:
    """对待审批申请作出通过或拒绝决定。

    本函数只 flush、不 commit。
    这样 API 路由可以将审批记录、申请状态和审计事件作为一个事务统一提交。
    """

    request = await session.get(AccessRequest, request_id)
    if request is None:
        raise ApprovalNotFoundError("待审批申请不存在。")

    # 只能处理真正进入人工审批队列的申请。
    if request.status != RequestStatus.PENDING_APPROVAL:
        raise ApprovalConflictError(f"当前申请状态为 {request.status}，不能执行审批。")

    existing_approval_id = await session.scalar(
        select(Approval.id).where(Approval.request_id == request_id)
    )
    if existing_approval_id is not None:
        raise ApprovalConflictError("该申请已经完成审批，不能重复操作。")

    normalized_comment = payload.comment.strip() if payload.comment else None

    # 拒绝权限申请必须留下理由，否则申请人无法补充或修改申请。
    if payload.decision == ApprovalDecision.REJECTED and not normalized_comment:
        raise ApprovalValidationError("拒绝申请时必须填写审批意见。")

    approval = Approval(
        request_id=request.id,
        approver_external_id=approver_external_id,
        decision=payload.decision,
        comment=normalized_comment,
    )
    session.add(approval)

    # 审批记录是“人做了什么动作”，申请状态是“流程现在走到哪里”。
    request.status = (
        RequestStatus.APPROVED
        if payload.decision == ApprovalDecision.APPROVED
        else RequestStatus.REJECTED
    )

    session.add(
        AuditEvent(
            request_id=request.id,
            trace_id=request.trace_id,
            event_type="ACCESS_REQUEST_APPROVED"
            if payload.decision == ApprovalDecision.APPROVED
            else "ACCESS_REQUEST_REJECTED",
            actor_external_id=approver_external_id,
            payload={
                "decision": payload.decision,
                "comment": normalized_comment,
            },
        )
    )

    # 这里执行 SQL、生成 approval.id，并提前暴露唯一约束等错误。
    # 但不 commit，调用方仍能决定整个事务何时提交。
    await session.flush()

    return approval
