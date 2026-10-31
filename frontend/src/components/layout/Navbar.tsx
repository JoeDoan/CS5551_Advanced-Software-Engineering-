import React from 'react'
import { Calendar, Bell, User, CheckCircle2, LogOut, ShieldCheck } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'

export const Navbar: React.FC = () => {
  const { user, logout, isStandaloneFallback } = useAuth()

  const displayName = user?.full_name ?? 'Course Coordinator'
  const displayEmail = user?.email ?? 'coordinator@umkc.edu'
  const displayRole = (user?.role ?? 'coordinator').toUpperCase()

  return (
    <header className="h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between sticky top-0 z-30 shadow-sm">
      <div className="flex items-center space-x-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
          <Calendar className="w-5 h-5" />
        </div>
        <div className="flex items-center">
          <span className="text-xl font-bold bg-gradient-to-r from-blue-700 to-indigo-700 bg-clip-text text-transparent">
            UMKC Scheduler
          </span>
          {isStandaloneFallback ? (
            <span className="ml-2 text-xs font-semibold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
              Sprint 0
            </span>
          ) : (
            <span
              className="ml-2 inline-flex items-center space-x-1 text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200"
              data-testid="session-active-badge"
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Session Active</span>
            </span>
          )}
        </div>
      </div>

      <div className="flex items-center space-x-4">
        <div className="hidden sm:flex items-center space-x-2 text-xs font-medium text-emerald-700 bg-emerald-50 px-3 py-1.5 rounded-lg border border-emerald-200">
          <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          <span>Solver: Ready (UMKC 6-Term)</span>
        </div>

        <button
          type="button"
          aria-label="Notifications"
          className="p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
        >
          <Bell className="w-5 h-5" />
        </button>

        <div className="flex items-center space-x-3 pl-3 border-l border-slate-200">
          <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-semibold text-sm">
            <User className="w-4 h-4" />
          </div>
          <div className="hidden md:block text-left text-xs">
            <div className="flex items-center space-x-1.5">
              <span className="font-semibold text-slate-800">{displayName}</span>
              <span
                className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                  displayRole === 'COORDINATOR'
                    ? 'bg-amber-100 text-amber-900'
                    : 'bg-blue-100 text-blue-800'
                }`}
                data-testid="navbar-role-badge"
              >
                {displayRole}
              </span>
            </div>
            <div className="text-slate-500">{displayEmail}</div>
          </div>

          {!isStandaloneFallback && (
            <button
              type="button"
              onClick={() => logout()}
              data-testid="logout-button"
              className="inline-flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold text-slate-600 hover:text-red-700 hover:bg-red-50 border border-slate-200 hover:border-red-200 transition-colors"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>Sign Out</span>
            </button>
          )}
        </div>
      </div>
    </header>
  )
}
