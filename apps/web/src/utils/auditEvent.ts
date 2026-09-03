/** 审计事件类型与中文名称的统一映射。 */
export const auditEventOptions = [
  { value: 'ACCESS_REQUEST_CREATED', label: '申请已创建' },
  { value: 'ACCESS_PLAN_CREATED', label: '权限方案已生成' },
  { value: 'ACCESS_POLICY_EVALUATED', label: '策略评估完成' },
  { value: 'ACCESS_REQUEST_APPROVED', label: '审批已通过' },
  { value: 'ACCESS_REQUEST_REJECTED', label: '审批已拒绝' },
  { value: 'ACCESS_EXECUTION_STARTED', label: '授权执行开始' },
  { value: 'ACCESS_EXECUTION_COMPLETED', label: '授权执行完成' },
  { value: 'ACCESS_EXECUTION_FAILED', label: '授权执行失败' },
  { value: 'ACCESS_PERMISSION_REVOKED', label: '权限已回收' },
  { value: 'ACCESS_REQUEST_REVOKED', label: '申请权限已全部回收' },
  { value: 'ACCESS_REVOCATION_FAILED', label: '权限回收失败' },
] as const

/** 将事件类型转换为中文业务动作。 */
export function formatAuditEventType(eventType: string): string {
  return auditEventOptions.find((item) => item.value === eventType)?.label ?? eventType
}

/** 用颜色区分正常、等待和失败事件。 */
export function getAuditEventTagType(
  eventType: string,
): 'success' | 'warning' | 'danger' | 'primary' | 'info' {
  if (eventType.endsWith('COMPLETED') || eventType.endsWith('APPROVED')) {
    return 'success'
  }
  if (eventType.endsWith('FAILED') || eventType.endsWith('REJECTED')) {
    return 'danger'
  }
  if (eventType.includes('POLICY') || eventType.endsWith('STARTED')) {
    return 'warning'
  }
  return eventType.endsWith('CREATED') ? 'primary' : 'info'
}

/** 返回系统组件的中文名称；普通用户标识交由页面结合身份目录处理。 */
export function formatSystemActor(externalId: string): string | undefined {
  const systemActors: Record<string, string> = {
    'accessmesh-planner': '权限规划器',
    'accessmesh-expiry-scanner': '到期回收任务',
    opa: 'OPA 策略引擎',
  }
  return systemActors[externalId]
}
