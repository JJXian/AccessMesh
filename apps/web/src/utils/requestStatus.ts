/** Element Plus 标签允许使用的颜色类型。 */
type TagType = 'success' | 'warning' | 'danger' | 'info' | 'primary'

/** 页面展示状态时需要的中文标签和颜色。 */
interface RequestStatusMeta {
  label: string
  type: TagType
}

/** 将后端状态码转换为面向用户的中文状态标签。 */
const REQUEST_STATUS_META: Record<string, RequestStatusMeta> = {
  SUBMITTED: { label: '已提交', type: 'info' },
  PARSING_REQUEST: { label: '正在解析', type: 'primary' },
  NEED_CLARIFICATION: { label: '待补充信息', type: 'warning' },
  COLLECTING_CONTEXT: { label: '收集上下文', type: 'primary' },
  PLANNING: { label: '正在规划', type: 'primary' },
  POLICY_DENIED: { label: '策略拒绝', type: 'danger' },
  PENDING_APPROVAL: { label: '等待审批', type: 'warning' },
  APPROVED: { label: '审批通过', type: 'success' },
  REJECTED: { label: '审批拒绝', type: 'danger' },
  EXECUTING: { label: '正在执行', type: 'primary' },
  COMPENSATING: { label: '正在补偿', type: 'warning' },
  VERIFYING: { label: '正在验证', type: 'primary' },
  ACTIVE: { label: '权限已生效', type: 'success' },
  REVOKED: { label: '权限已回收', type: 'info' },
  FAILED: { label: '执行失败', type: 'danger' },
}

/** 获取状态展示信息；未知状态保留原始值，避免页面空白。 */
export function getRequestStatusMeta(
  status: string,
): RequestStatusMeta {
  return REQUEST_STATUS_META[status] ?? {
    label: status,
    type: 'info',
  }
}