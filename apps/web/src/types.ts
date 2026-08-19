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
