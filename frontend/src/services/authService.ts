import { apiClient, ApiError, getAuthToken, hasHttpStatus } from './apiClient'
import {
  AuthUser,
  LoginRequest,
  LoginResponse,
  LogoutResponse,
  SessionVerifyResponse,
} from '../types/api'

export const DEMO_COORDINATOR_TOKEN = 'demo-coordinator-token'
export const DEMO_INSTRUCTOR_TOKEN = 'demo-instructor-token'

export const DEMO_COORDINATOR_USER: AuthUser = {
  id: 100,
  email: 'coordinator@umkc.edu',
  username: 'coordinator',
  full_name: 'Course Coordinator',
  role: 'coordinator',
  department: 'CS',
  linked_user_id: null,
}

export const DEMO_INSTRUCTOR_USER: AuthUser = {
  id: 101,
  email: 'leeyu@umkc.edu',
  username: 'leeyu',
  full_name: 'Dr. Yugyung Lee',
  role: 'instructor',
  department: 'CS',
  linked_user_id: 1,
}

const buildOfflineExpiry = (): string =>
  new Date(Date.now() + 8 * 60 * 60 * 1000).toISOString()

const resolveOfflineDemoToken = (token: string | null): SessionVerifyResponse | null => {
  if (token === DEMO_COORDINATOR_TOKEN) {
    return {
      session_id: 'offline-coordinator-session',
      expires_at: buildOfflineExpiry(),
      user: DEMO_COORDINATOR_USER,
    }
  }
  if (token === DEMO_INSTRUCTOR_TOKEN) {
    return {
      session_id: 'offline-instructor-session',
      expires_at: buildOfflineExpiry(),
      user: DEMO_INSTRUCTOR_USER,
    }
  }
  return null
}

export const authService = {
  async login(payload: LoginRequest): Promise<LoginResponse> {
    try {
      const response = await apiClient.post<LoginResponse>('/auth/login', payload)
      return response.data
    } catch (err) {
      if (hasHttpStatus(err)) {
        throw err
      }
      const id = payload.identifier.trim().toLowerCase()
      if ((id === 'coordinator@umkc.edu' || id === 'coordinator') && payload.password === 'coordinator123') {
        return {
          access_token: DEMO_COORDINATOR_TOKEN,
          token_type: 'bearer',
          session_id: 'offline-coordinator-session',
          expires_at: buildOfflineExpiry(),
          user: DEMO_COORDINATOR_USER,
        }
      }
      if ((id === 'leeyu@umkc.edu' || id === 'leeyu') && payload.password === 'faculty123') {
        return {
          access_token: DEMO_INSTRUCTOR_TOKEN,
          token_type: 'bearer',
          session_id: 'offline-instructor-session',
          expires_at: buildOfflineExpiry(),
          user: DEMO_INSTRUCTOR_USER,
        }
      }
      throw new ApiError('Invalid email/username or password.', 401)
    }
  },

  async verifySession(): Promise<SessionVerifyResponse> {
    try {
      const response = await apiClient.get<SessionVerifyResponse>('/auth/me')
      return response.data
    } catch (err) {
      if (hasHttpStatus(err)) {
        throw err
      }
      const offline = resolveOfflineDemoToken(getAuthToken())
      if (offline) {
        return offline
      }
      throw new ApiError('Your session expired. Please sign in again.', 401)
    }
  },

  async logout(): Promise<LogoutResponse> {
    try {
      const response = await apiClient.post<LogoutResponse>('/auth/logout')
      return response.data
    } catch {
      return { status: 'logged_out', revoked_session_id: 'local-session' }
    }
  },
}

export default authService
