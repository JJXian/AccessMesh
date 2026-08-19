import client from './client'
import type { AccessRequest, DemoUser, Resource } from '../types'

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

/** 按当前演示身份获取可见的权限申请。 */
export async function listAccessRequests(): Promise<AccessRequest[]> {
  const { data } = await client.get<AccessRequest[]>('/access-requests')
  return data
}

/** 根据申请主键读取详情。 */
export async function getAccessRequest(id: string): Promise<AccessRequest> {
  const { data } = await client.get<AccessRequest>(`/access-requests/${id}`)
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
