import { apiClient, ApiError, getAuthToken, hasHttpStatus } from './apiClient'
import {
  AccountAdminItem,
  AccountCreatePayload,
  AccountFilterParams,
  AccountUpdatePayload,
  AuthUser,
  LoginRequest,
  LoginResponse,
  LogoutResponse,
  SessionVerifyResponse,
} from '../types/api'

export const DEMO_COORDINATOR_TOKEN = 'demo-coordinator-token'
export const DEMO_INSTRUCTOR_TOKEN = 'demo-instructor-token'

export interface DemoAccountItem {
  email: string
  username: string
  full_name: string
  role: 'coordinator' | 'instructor'
  department: string
  password: string
  linked_user_id: number | null
}

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

const INITIAL_MOCK_ACCOUNTS: AccountAdminItem[] = [
  {
    ...DEMO_COORDINATOR_USER,
    is_active: true,
  },
  {
    ...DEMO_INSTRUCTOR_USER,
    is_active: true,
  },
  {
    id: 102,
    email: 'raopr@umkc.edu',
    username: 'raopr',
    full_name: 'Dr. Praveen Rao',
    role: 'instructor',
    department: 'CS',
    linked_user_id: 2,
    is_active: true,
  },
]

let mockAccounts: AccountAdminItem[] = INITIAL_MOCK_ACCOUNTS.map((a) => ({ ...a }))

export const resetMockAccounts = (): void => {
  mockAccounts = INITIAL_MOCK_ACCOUNTS.map((a) => ({ ...a }))
}

const filterMockAccounts = (params?: AccountFilterParams): AccountAdminItem[] => {
  let result = mockAccounts.map((a) => ({ ...a }))
  if (params?.role) {
    result = result.filter((a) => a.role === params.role)
  }
  const q = params?.search?.trim().toLowerCase()
  if (q) {
    result = result.filter(
      (a) =>
        a.full_name.toLowerCase().includes(q) ||
        a.email.toLowerCase().includes(q) ||
        a.username.toLowerCase().includes(q) ||
        a.department.toLowerCase().includes(q)
    )
  }
  return result
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

  async getDemoAccounts(): Promise<DemoAccountItem[] | null> {
    try {
      const response = await apiClient.get<DemoAccountItem[]>('/auth/demo-accounts')
      return Array.isArray(response.data) ? response.data : null
    } catch {
      return null
    }
  },

  async getAccounts(params?: AccountFilterParams): Promise<AccountAdminItem[]> {
    try {
      const queryParams: Record<string, string> = {}
      if (params?.role) queryParams.role = params.role
      if (params?.search?.trim()) queryParams.search = params.search.trim()
      const response = await apiClient.get<AccountAdminItem[]>('/auth/accounts', {
        params: queryParams,
      })
      return response.data
    } catch (err) {
      if (hasHttpStatus(err)) {
        throw err
      }
      return filterMockAccounts(params)
    }
  },

  async createAccount(payload: AccountCreatePayload): Promise<AccountAdminItem> {
    try {
      const response = await apiClient.post<AccountAdminItem>('/auth/accounts', payload)
      return response.data
    } catch (err) {
      if (hasHttpStatus(err)) {
        throw err
      }
      const normalizedEmail = payload.email.trim().toLowerCase()
      const derivedUsername = (
        payload.username?.trim() ||
        normalizedEmail.split('@')[0] ||
        'user'
      ).toLowerCase()

      const duplicate = mockAccounts.find(
        (acc) =>
          acc.email.toLowerCase() === normalizedEmail ||
          acc.username.toLowerCase() === derivedUsername
      )
      if (duplicate) {
        throw new ApiError('An account with that email or username already exists.', 409)
      }

      const nextId =
        mockAccounts.length > 0 ? Math.max(...mockAccounts.map((a) => a.id)) + 1 : 100
      const maxLinkedUserId = mockAccounts.reduce(
        (max, a) => (a.linked_user_id && a.linked_user_id > max ? a.linked_user_id : max),
        2
      )
      const created: AccountAdminItem = {
        id: nextId,
        email: normalizedEmail,
        username: derivedUsername,
        full_name: payload.full_name.trim(),
        role: payload.role,
        department: payload.department,
        linked_user_id: payload.role === 'instructor' ? maxLinkedUserId + 1 : null,
        is_active: true,
      }
      mockAccounts = [...mockAccounts, created]
      return { ...created }
    }
  },

  async updateAccount(id: number, payload: AccountUpdatePayload): Promise<AccountAdminItem> {
    try {
      const response = await apiClient.patch<AccountAdminItem>(`/auth/accounts/${id}`, payload)
      return response.data
    } catch (err) {
      if (hasHttpStatus(err)) {
        throw err
      }
      const idx = mockAccounts.findIndex((a) => a.id === id)
      if (idx === -1) {
        throw new ApiError(`Account ${id} not found.`, 404)
      }
      const existing = mockAccounts[idx]
      const currentSession = resolveOfflineDemoToken(getAuthToken())
      if (
        currentSession &&
        currentSession.user.email.toLowerCase() === existing.email.toLowerCase() &&
        (payload.is_active === false || (payload.role && payload.role !== 'coordinator'))
      ) {
        throw new ApiError('Cannot disable or demote your own active coordinator account.', 400)
      }

      const nextRole = payload.role ?? existing.role
      let nextLinkedUserId = existing.linked_user_id
      if (nextRole === 'instructor' && nextLinkedUserId === null) {
        const maxLinkedUserId = mockAccounts.reduce(
          (max, a) => (a.linked_user_id && a.linked_user_id > max ? a.linked_user_id : max),
          2
        )
        nextLinkedUserId = maxLinkedUserId + 1
      } else if (nextRole === 'coordinator') {
        nextLinkedUserId = null
      }

      const updated: AccountAdminItem = {
        ...existing,
        full_name: payload.full_name !== undefined ? payload.full_name.trim() : existing.full_name,
        department: payload.department ?? existing.department,
        role: nextRole,
        linked_user_id: nextLinkedUserId,
        is_active: payload.is_active !== undefined ? payload.is_active : existing.is_active,
      }
      mockAccounts = mockAccounts.map((a) => (a.id === id ? updated : a))
      return { ...updated }
    }
  },

  async deleteAccount(id: number): Promise<void> {
    try {
      await apiClient.delete(`/auth/accounts/${id}`)
    } catch (err) {
      if (hasHttpStatus(err)) {
        throw err
      }
      const existing = mockAccounts.find((a) => a.id === id)
      const currentSession = resolveOfflineDemoToken(getAuthToken())
      if (
        existing &&
        currentSession &&
        currentSession.user.email.toLowerCase() === existing.email.toLowerCase()
      ) {
        throw new ApiError('Cannot delete your own active account.', 400)
      }
      mockAccounts = mockAccounts.filter((a) => a.id !== id)
    }
  },
}

export default authService

