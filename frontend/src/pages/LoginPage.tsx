import React, { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { Calendar, Lock, Mail, ShieldCheck, UserCheck, ArrowRight } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { Alert, Badge, Button, Card, CardContent, Input } from '../components/ui'

export const LoginPage: React.FC = () => {
  const { session, login, clearAuthError } = useAuth()
  const navigate = useNavigate()

  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (session.status === 'checking') {
    return (
      <div
        className="min-h-screen bg-slate-50 flex items-center justify-center p-6"
        data-testid="login-session-checking"
      >
        <div className="bg-white border border-slate-200 rounded-2xl shadow-sm px-8 py-6 flex items-center space-x-4">
          <div className="p-3 rounded-xl bg-blue-50 text-blue-600 animate-pulse">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <span className="text-sm font-bold text-slate-900">
            Verifying active security session...
          </span>
        </div>
      </div>
    )
  }

  if (session.status === 'authenticated') {
    return <Navigate to="/" replace />
  }

  const executeSignIn = async (idValue: string, pwValue: string) => {
    if (!idValue.trim() || !pwValue.trim()) {
      setErrorMessage('Please enter both your UMKC email or username and password.')
      return
    }
    setErrorMessage(null)
    clearAuthError()
    setSubmitting(true)
    try {
      await login({ identifier: idValue.trim(), password: pwValue })
      navigate('/', { replace: true })
    } catch (err) {
      setErrorMessage((err as Error).message || 'Authentication failed. Check your credentials.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    await executeSignIn(identifier, password)
  }

  const handleQuickDemo = async (demoId: string, demoPassword: string) => {
    setIdentifier(demoId)
    setPassword(demoPassword)
    await executeSignIn(demoId, demoPassword)
  }

  const activeAlert = errorMessage || session.reason

  return (
    <div
      className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900 flex items-center justify-center p-6"
      data-testid="login-page"
    >
      <div className="w-full max-w-md space-y-6">
        <div className="text-center space-y-2">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-blue-600 to-amber-500 flex items-center justify-center text-white shadow-lg mx-auto">
            <Calendar className="w-7 h-7" />
          </div>
          <div className="flex items-center justify-center space-x-2">
            <h1 className="text-2xl font-extrabold text-white tracking-tight">UMKC OptiSched</h1>
            <Badge variant="gold">SSO Gate</Badge>
          </div>
          <p className="text-xs text-blue-200">
            School of Science & Engineering Academic Scheduling Portal
          </p>
        </div>

        <Card className="shadow-2xl border-slate-200/90">
          <CardContent className="p-7 space-y-5">
            <div>
              <h2 className="text-lg font-bold text-slate-900">Sign in to your account</h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Authenticate to access schedules, preferences, and role-authorized tools.
              </p>
            </div>

            {activeAlert && (
              <Alert
                variant="danger"
                title="Authentication Notice"
                onClose={() => {
                  setErrorMessage(null)
                  clearAuthError()
                }}
              >
                {activeAlert}
              </Alert>
            )}

            <form onSubmit={handleFormSubmit} className="space-y-4">
              <Input
                label="Email or Username"
                placeholder="coordinator@umkc.edu"
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                leftIcon={<Mail className="w-4 h-4" />}
                autoComplete="username"
                data-testid="login-identifier-input"
              />
              <Input
                label="Password"
                type="password"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                leftIcon={<Lock className="w-4 h-4" />}
                autoComplete="current-password"
                data-testid="login-password-input"
              />
              <Button
                type="submit"
                variant="primary"
                className="w-full"
                isLoading={submitting}
                rightIcon={<ArrowRight className="w-4 h-4" />}
                data-testid="login-submit-button"
              >
                Sign In
              </Button>
            </form>

            <div className="pt-3 border-t border-slate-200 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  Quick Demo Role Access
                </span>
                <Badge variant="info">1-Click</Badge>
              </div>

              <div className="space-y-2.5">
                <button
                  type="button"
                  disabled={submitting}
                  onClick={() => handleQuickDemo('coordinator@umkc.edu', 'coordinator123')}
                  data-testid="demo-login-coordinator"
                  className="w-full text-left p-3 rounded-xl border border-blue-200 bg-blue-50/70 hover:bg-blue-100/80 transition-colors flex items-start space-x-3"
                >
                  <div className="p-2 rounded-lg bg-blue-600 text-white shrink-0 mt-0.5">
                    <ShieldCheck className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-bold text-slate-900">
                      Sign in as Course Coordinator
                    </div>
                    <div className="text-[11px] text-slate-600 mt-0.5">
                      coordinator@umkc.edu · Full Course, Room & Section CRUD, Solver execution, Edit
                      Request approvals
                    </div>
                  </div>
                </button>

                <button
                  type="button"
                  disabled={submitting}
                  onClick={() => handleQuickDemo('leeyu@umkc.edu', 'faculty123')}
                  data-testid="demo-login-instructor"
                  className="w-full text-left p-3 rounded-xl border border-slate-200 bg-slate-50 hover:bg-slate-100 transition-colors flex items-start space-x-3"
                >
                  <div className="p-2 rounded-lg bg-slate-700 text-white shrink-0 mt-0.5">
                    <UserCheck className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-bold text-slate-900">
                      Sign in as Faculty Instructor
                    </div>
                    <div className="text-[11px] text-slate-600 mt-0.5">
                      leeyu@umkc.edu (Dr. Yugyung Lee) · View Master Schedule, submit own Preferences
                      & schedule Edit Requests
                    </div>
                  </div>
                </button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default LoginPage
