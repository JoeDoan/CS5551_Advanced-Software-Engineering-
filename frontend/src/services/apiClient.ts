import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'
import { ApiErrorResponse } from '../types/api'

export const AUTH_TOKEN_KEY = 'optisched_auth_token'

export class ApiError extends Error {
  status?: number
  data?: unknown
  isApiError = true

  constructor(message: string, status?: number, data?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.data = data
  }
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || '/api/v1'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
})

// Helper methods for token management across Trust Boundary
export const getAuthToken = (): string | null => {
  try {
    return localStorage.getItem(AUTH_TOKEN_KEY) || localStorage.getItem('token')
  } catch {
    return null
  }
}

export const setAuthToken = (token: string): void => {
  try {
    localStorage.setItem(AUTH_TOKEN_KEY, token)
  } catch {
    // ignore in environments without localStorage
  }
}

export const clearAuthToken = (): void => {
  try {
    localStorage.removeItem(AUTH_TOKEN_KEY)
    localStorage.removeItem('token')
  } catch {
    // ignore in environments without localStorage
  }
}

// Request Interceptor: Attach JWT Bearer token if present
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = getAuthToken()
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(new ApiError(error?.message || 'Request configuration error'))
  }
)

// Response Interceptor: Format errors and handle global status codes
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiErrorResponse>) => {
    const status = error.response?.status
    const errorData = error.response?.data
    let message = error.message

    if (errorData && typeof errorData === 'object') {
      if (typeof errorData.message === 'string') {
        message = errorData.message
      } else if (typeof errorData.detail === 'string') {
        message = errorData.detail
      } else if (Array.isArray(errorData.detail) && errorData.detail.length > 0) {
        message = errorData.detail.map((d) => d.msg || 'Validation error').join('; ')
      }
    } else if (status === 401) {
      message = 'Unauthorized session. Please authenticate.'
    } else if (status === 403) {
      message = 'Forbidden: insufficient role permissions.'
    } else if (status === 404) {
      message = 'Requested resource was not found.'
    } else if (status && status >= 500) {
      message = 'Internal server error occurred.'
    } else if (error.code === 'ECONNABORTED') {
      message = 'Request timed out.'
    } else if (!error.response) {
      message = 'Network error: could not reach backend server.'
    }

    const apiError = new ApiError(message, status, errorData)
    return Promise.reject(apiError)
  }
)

export default apiClient
