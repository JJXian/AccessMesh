import axios from 'axios'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api/v1',
  timeout: 10_000,
})

client.interceptors.request.use((config) => {
  config.headers['X-Demo-Subject-Id'] =
    localStorage.getItem('accessmesh.demoSubjectId') ?? 'user-requester'
  return config
})

export default client
