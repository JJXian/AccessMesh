import client from './client'
import type {
  AccessRequest,
  AccessRequestDetail,
  AccessRequestPage,
  Approval,
  ApprovalDecision,
  AuditEventPage,
  DemoUser,
  PermissionInstance,
  Resource,
} from '../types'

/** 获取身份切换器可选的演示用户。 */
export async function listDemoUsers(): Promise<DemoUser[]> {
  const { data } = await client.get<DemoUser[]>('/demo/users')
  return data
}

/** 获取当前启用的资源目录。 */
export async function listResources(): Promise<Resource[]> {
  const { data } = await client.get<Resource[]>('/resources')
  return data
}

/** 按页获取当前身份可见的权限申请。 */
export async function listAccessRequests(
  page = 1,
  pageSize = 10,
): Promise<AccessRequestPage> {
  const { data } = await client.get<AccessRequestPage>(
    '/access-requests',
    {
      params: {
        page,
        page_size: pageSize,
      },
    },
  )
  return data
}

/** 根据申请主键读取详情。 */
export async function getAccessRequest(id: string): Promise<AccessRequest> {
  const { data } = await client.get<AccessRequest>(`/access-requests/${id}`)
  return data
}

/** 获取申请从规划、审批、执行到审计的聚合详情。 */
export async function getAccessRequestDetail(
  id: string,
): Promise<AccessRequestDetail> {
  const { data } = await client.get<AccessRequestDetail>(
    `/access-requests/${id}/detail`,
  )
  return data
}

/** 提交自然语言权限申请。 */
export async function createAccessRequest(payload: {
  subject_external_id: string
  request_text: string
  client_request_id: string
}): Promise<AccessRequest> {
  const { data } = await client.post<AccessRequest>('/access-requests', payload)
  return data
}

/** 获取当前审批人可处理的待审批申请。 */
export async function listPendingApprovals(): Promise<AccessRequest[]> {
  const { data } = await client.get<AccessRequest[]>('/approvals/pending')
  return data
}

/** 对一条待审批申请作出通过或拒绝决定。 */
export async function createApproval(
  requestId: string,
  payload: {
    decision: ApprovalDecision
    comment?: string
  },
): Promise<Approval> {
  const { data } = await client.post<Approval>(
    `/approvals/${requestId}`,
    payload,
  )
  return data
}

/** 获取当前身份有权限查看的已生效权限。 */
export async function listActivePermissions(): Promise<PermissionInstance[]> {
  const { data } = await client.get<PermissionInstance[]>('/permissions')
  return data
}

/** 由审批人手工提前回收一条仍然有效的权限。 */
export async function revokePermission(
  permissionId: string,
  reason: string,
): Promise<PermissionInstance> {
  const { data } = await client.post<PermissionInstance>(
    `/permissions/${permissionId}/revoke`,
    { reason },
  )
  return data
}

/** 按页查询当前身份可见的审计事件。 */
export async function listAuditEvents(params: {
  page: number
  page_size: number
  request_id?: string
  subject_external_id?: string
  resource_external_id?: string
  event_type?: string
}): Promise<AuditEventPage> {
  const { data } = await client.get<AuditEventPage>('/audit-events', {
    params,
  })
  return data
}

/** 执行一条已经审批通过的权限申请。 */
export async function executeAccessRequest(
  requestId: string,
): Promise<AccessRequest> {
  const { data } = await client.post<AccessRequest>(
    `/access-requests/${requestId}/execute`,
  )
  return data
}
