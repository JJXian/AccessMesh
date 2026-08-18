import client from './client'
import type { AccessRequest, DemoUser, Resource } from '../types'

export async function listDemoUsers(): Promise<DemoUser[]> {
  const { data } = await client.get<DemoUser[]>('/demo/users')
  return data
}

export async function listResources(): Promise<Resource[]> {
  const { data } = await client.get<Resource[]>('/resources')
  return data
}

export async function listAccessRequests(): Promise<AccessRequest[]> {
  const { data } = await client.get<AccessRequest[]>('/access-requests')
  return data
}

export async function getAccessRequest(id: string): Promise<AccessRequest> {
  const { data } = await client.get<AccessRequest>(`/access-requests/${id}`)
  return data
}

export async function createAccessRequest(payload: {
  subject_external_id: string
  request_text: string
  client_request_id: string
}): Promise<AccessRequest> {
  const { data } = await client.post<AccessRequest>('/access-requests', payload)
  return data
}
