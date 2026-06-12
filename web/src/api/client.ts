import axios from 'axios'

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

apiClient.interceptors.response.use(
  (response) => {
    // Backend wraps all responses in {code, msg, data}
    const body = response.data
    if (body && typeof body === 'object' && 'code' in body && 'data' in body) {
      response.data = body.data
    }
    return response
  },
  (error) => {
    const message =
      error.response?.data?.detail?.[0]?.msg ??
      error.response?.data?.message ??
      error.message ??
      '请求失败'
    return Promise.reject(new Error(message))
  },
)
