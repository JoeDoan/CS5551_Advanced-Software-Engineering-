import React from 'react'
import { Link, Navigate, useLocation } from 'react-router-dom'
import { ShieldAlert, ShieldCheck, ArrowLeft } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { AuthRole } from '../../types/api'
import { Card, CardContent, Button, Badge } from '../ui'

export interface ProtectedRouteProps {
  allowedRoles?: AuthRole[]
  children: React.ReactNode
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ allowedRoles, children }) => {
  const { session } = useAuth()
  const location = useLocation()

  switch (session.status) {
    case 'checking':
      return (
        <div
          className="min-h-screen bg-slate-50 flex items-center justify-center p-6"
          data-testid="session-checking-gate"
        >
          <div className="bg-white border border-slate-200 rounded-2xl shadow-sm px-8 py-6 flex items-center space-x-4">
            <div className="p-3 rounded-xl bg-blue-50 text-blue-600 animate-pulse">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm font-bold text-slate-900">
                Verifying active security session...
              </p>
              <p className="text-xs text-slate-500 mt-0.5">
                Validating UMKC OptiSched bearer token and role permissions
              </p>
            </div>
          </div>
        </div>
      )

    case 'unauthenticated':
      return <Navigate to="/login" state={{ from: location.pathname }} replace />

    case 'authenticated': {
      if (allowedRoles && !allowedRoles.includes(session.user.role)) {
        return (
          <div className="py-12 max-w-xl mx-auto" data-testid="role-guard-403">
            <Card className="border-red-200">
              <CardContent className="p-8 text-center space-y-4">
                <div className="w-12 h-12 rounded-2xl bg-red-50 text-red-600 flex items-center justify-center mx-auto">
                  <ShieldAlert className="w-6 h-6" />
                </div>
                <Badge variant="danger">403 Access Restricted</Badge>
                <h2 className="text-xl font-bold text-slate-900">
                  Coordinator Role Required
                </h2>
                <p className="text-xs text-slate-600 leading-relaxed">
                  Signed in as <span className="font-semibold">{session.user.full_name}</span> (
                  <span className="uppercase font-semibold">{session.user.role}</span>). Catalog
                  modification, room inventory changes, and CP-SAT solver controls are restricted to
                  UMKC Course Coordinators.
                </p>
                <div className="pt-2">
                  <Link to="/schedule">
                    <Button
                      variant="primary"
                      size="sm"
                      leftIcon={<ArrowLeft className="w-4 h-4" />}
                      data-testid="return-to-schedule-btn"
                    >
                      Return to Master Schedule
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>
          </div>
        )
      }
      return <>{children}</>
    }

    default: {
      const _exhaustive: never = session
      return _exhaustive
    }
  }
}

export default ProtectedRoute
