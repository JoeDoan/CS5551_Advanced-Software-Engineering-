import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import {
  clearAuthToken,
  getAuthToken,
  setAuthToken,
  UNAUTHORIZED_EVENT,
} from '../services/apiClient'
import { authService, DEMO_COORDINATOR_USER } from '../services/authService'
import { AuthUser, LoginRequest } from '../types/api'

export type SessionState =
  | { status: 'checking' }
  | { status: 'unauthenticated'; reason?: string }
  | { status: 'authenticated'; user: AuthUser; sessionId: string; expiresAt: string }

export interface AuthContextValue {
  session: SessionState
  user: AuthUser | null
  login: (payload: LoginRequest) => Promise<AuthUser>
  logout: () => Promise<void>
  clearAuthError: () => void
  isStandaloneFallback: boolean
}

const FALLBACK_AUTH_CONTEXT: AuthContextValue = {
  session: {
    status: 'authenticated',
    user: DEMO_COORDINATOR_USER,
    sessionId: 'standalone-fallback',
    expiresAt: '',
  },
  user: DEMO_COORDINATOR_USER,
  login: async () => DEMO_COORDINATOR_USER,
  logout: async () => {},
  clearAuthError: () => {},
  isStandaloneFallback: true,
}

const AuthContext = createContext<AuthContextValue | null>(null)

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [session, setSession] = useState<SessionState>(() =>
    getAuthToken() ? { status: 'checking' } : { status: 'unauthenticated' }
  )

  useEffect(() => {
    const handleUnauthorized = () => {
      clearAuthToken()
      setSession({
        status: 'unauthenticated',
        reason: 'Your session expired. Please sign in again.',
      })
    }

    window.addEventListener(UNAUTHORIZED_EVENT, handleUnauthorized)
    return () => {
      window.removeEventListener(UNAUTHORIZED_EVENT, handleUnauthorized)
    }
  }, [])

  useEffect(() => {
    const token = getAuthToken()
    if (!token) {
      setSession((prev) =>
        prev.status === 'unauthenticated' ? prev : { status: 'unauthenticated' }
      )
      return
    }

    let active = true
    setSession({ status: 'checking' })

    authService
      .verifySession()
      .then((res) => {
        if (!active) return
        setSession({
          status: 'authenticated',
          user: res.user,
          sessionId: res.session_id,
          expiresAt: res.expires_at,
        })
      })
      .catch(() => {
        if (!active) return
        clearAuthToken()
        setSession({
          status: 'unauthenticated',
          reason: 'Your session expired. Please sign in again.',
        })
      })

    return () => {
      active = false
    }
  }, [])

  const login = useCallback(async (payload: LoginRequest): Promise<AuthUser> => {
    const res = await authService.login(payload)
    setAuthToken(res.access_token)
    setSession({
      status: 'authenticated',
      user: res.user,
      sessionId: res.session_id,
      expiresAt: res.expires_at,
    })
    return res.user
  }, [])

  const logout = useCallback(async (): Promise<void> => {
    try {
      await authService.logout()
    } finally {
      clearAuthToken()
      setSession({ status: 'unauthenticated' })
    }
  }, [])

  const clearAuthError = useCallback(() => {
    setSession((prev) =>
      prev.status === 'unauthenticated' && prev.reason
        ? { status: 'unauthenticated' }
        : prev
    )
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      session,
      user: session.status === 'authenticated' ? session.user : null,
      login,
      logout,
      clearAuthError,
      isStandaloneFallback: false,
    }),
    [session, login, logout, clearAuthError]
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export const useAuth = (): AuthContextValue => {
  const ctx = useContext(AuthContext)
  return ctx ?? FALLBACK_AUTH_CONTEXT
}

export default AuthContext
