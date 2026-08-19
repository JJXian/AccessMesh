import axios from 'axios'

// 所有业务接口共享相同的 API 前缀和超时，便于按部署环境统一覆盖。
const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api/v1',
  timeout: 10_000,
})

client.interceptors.request.use((config) => {
  // 演示环境用请求头模拟登录身份；生产接入时应替换为真实认证令牌。
  config.headers['X-Demo-Subject-Id'] =
    localStorage.getItem('accessmesh.demoSubjectId') ?? 'user-requester'
  return config
})

export default client
