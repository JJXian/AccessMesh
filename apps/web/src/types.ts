/** 后端演示身份的只读视图。 */
export interface DemoUser {
  id: string
  external_id: string
  username: string
  display_name: string
  role: 'requester' | 'approver' | 'auditor'
  subject_type: 'employee' | 'contractor' | 'service_account'
  department: string
  employment_status: string
}

/** 可申请权限的资源目录项。 */
export interface Resource {
  id: string
  external_id: string
  name: string
  resource_type: 'gitlab' | 'database' | 'cloud'
  environment: 'development' | 'test' | 'staging' | 'production'
  sensitivity: string
  owner_external_id: string
  allowed_permissions: string[]
  enabled: boolean
}

/** 权限申请及其当前工作流状态。 */
export interface AccessRequest {
  id: string
  requester_external_id: string
  subject_external_id: string
  raw_request: string
  client_request_id: string
  status: string
  trace_id: string
  created_at: string
  updated_at: string
}
/** 分页返回的权限申请记录。 */
export interface AccessRequestPage {
  items: AccessRequest[]
  total: number
  page: number
  page_size: number
}

/** 审批人可以作出的最终决定。 */
export type ApprovalDecision = 'APPROVED' | 'REJECTED'

/** 后端成功保存后返回的审批记录。 */
export interface Approval {
  id: string
  request_id: string
  approver_external_id: string
  decision: ApprovalDecision
  comment: string | null
  decided_at: string
}

/** 后端返回的已生效权限实例。 */
export interface PermissionInstance {
  id: string
  request_id: string
  subject_external_id: string
  resource_external_id: string
  resource_name: string
  permission: string
  status: 'ACTIVE' | 'REVOKED'
  granted_at: string
  expires_at: string
  revoked_at: string | null
}

/** 权限治理链路中不可修改的单条审计事件。 */
export interface AuditEvent {
  id: string
  request_id: string | null
  trace_id: string
  event_type: string
  actor_external_id: string
  payload: Record<string, unknown>
  created_at: string
}

/** 分页返回的审计事件。 */
export interface AuditEventPage {
  items: AuditEvent[]
  total: number
  page: number
  page_size: number
}

/** 申请详情中的候选授权方案和资源信息。 */
export interface ProposedGrantDetail {
  id: string
  resource_external_id: string
  resource_name: string
  resource_type: string
  environment: string
  sensitivity: string
  permission: string
  duration_days: number
  reason: string
  evidence_refs: string[]
  plan_version: number
  created_at: string
}

/** OPA 针对单条候选授权方案给出的决策。 */
export interface PolicyDecisionDetail {
  id: string
  proposed_grant_id: string
  allow: boolean
  risk_level: string
  violations: Record<string, unknown>[]
  required_approvals: string[]
  max_duration_days: number | null
  policy_version: string
  created_at: string
}

/** 调用资源适配器执行单项授权的结果。 */
export interface ExecutionTask {
  id: string
  proposed_grant_id: string
  status: string
  attempt_count: number
  result: Record<string, unknown>
  error_message: string | null
  created_at: string
  updated_at: string
}

/** 已授权权限从生效到回收的生命周期记录。 */
export interface PermissionLifecycle {
  id: string
  execution_task_id: string
  resource_external_id: string
  resource_name: string
  permission: string
  status: 'ACTIVE' | 'REVOKED'
  external_grant_id: string
  granted_at: string
  expires_at: string
  revoked_at: string | null
  revocation_reason: string | null
}

/** 一条权限申请从规划、审批、执行到审计的聚合详情。 */
export interface AccessRequestDetail {
  request: AccessRequest
  proposed_grants: ProposedGrantDetail[]
  policy_decisions: PolicyDecisionDetail[]
  approval: Approval | null
  execution_tasks: ExecutionTask[]
  permissions: PermissionLifecycle[]
  audit_events: AuditEvent[]
}
