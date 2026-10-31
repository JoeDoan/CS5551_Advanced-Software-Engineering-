import React, { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useInRouterContext } from 'react-router-dom'
import { Calendar, Bell, User, CheckCircle2, LogOut, ShieldCheck, ArrowRight } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { editRequestService } from '../../services/editRequestService'
import { EditRequest } from '../../types/api'

export const Navbar: React.FC = () => {
  const { user, logout, isStandaloneFallback } = useAuth()
  const inRouter = useInRouterContext()

  const [notifications, setNotifications] = useState<EditRequest[]>([])
  const [isNotificationsOpen, setIsNotificationsOpen] = useState<boolean>(false)
  const popoverRef = useRef<HTMLDivElement | null>(null)

  const displayName = user?.full_name ?? 'Course Coordinator'
  const displayEmail = user?.email ?? 'coordinator@umkc.edu'
  const displayRole = (user?.role ?? 'coordinator').toUpperCase()

  useEffect(() => {
    let active = true
    editRequestService
      .getEditRequests()
      .then((list) => {
        if (active && Array.isArray(list)) {
          setNotifications(list)
        }
      })
      .catch(() => {})

    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    if (!isNotificationsOpen) return
    const handleOutsideClick = (event: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(event.target as Node)) {
        setIsNotificationsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleOutsideClick)
    return () => {
      document.removeEventListener('mousedown', handleOutsideClick)
    }
  }, [isNotificationsOpen])

  const handleToggleNotifications = () => {
    const nextOpen = !isNotificationsOpen
    setIsNotificationsOpen(nextOpen)
    if (nextOpen) {
      editRequestService
        .getEditRequests()
        .then((list) => {
          if (Array.isArray(list)) {
            setNotifications(list)
          }
        })
        .catch(() => {})
    }
  }

  const pendingCount = useMemo(
    () => notifications.filter((item) => item.status === 'pending').length,
    [notifications]
  )

  const topItems = useMemo(() => {
    return [...notifications]
      .sort((a, b) => {
        if (a.status === 'pending' && b.status !== 'pending') return -1
        if (a.status !== 'pending' && b.status === 'pending') return 1
        return b.id - a.id
      })
      .slice(0, 4)
  }, [notifications])

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

        <div className="relative" ref={popoverRef}>
          <button
            type="button"
            aria-label="Notifications"
            aria-expanded={isNotificationsOpen}
            data-testid="notifications-bell-btn"
            onClick={handleToggleNotifications}
            className="relative p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <Bell className="w-5 h-5" />
            {pendingCount > 0 && (
              <span
                data-testid="notifications-pending-badge"
                className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 rounded-full bg-amber-500 text-white text-[10px] font-bold flex items-center justify-center shadow-sm"
              >
                {pendingCount}
              </span>
            )}
          </button>

          {isNotificationsOpen && (
            <div
              data-testid="notifications-popover"
              className="absolute right-0 mt-2 w-80 sm:w-96 rounded-2xl bg-white border border-slate-200 shadow-xl z-50 overflow-hidden"
            >
              <div className="px-4 py-3 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
                <span className="text-xs font-bold text-slate-900">
                  Schedule Edit Notifications
                </span>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800">
                  {pendingCount} Pending
                </span>
              </div>

              <div className="max-h-72 overflow-y-auto divide-y divide-slate-100">
                {topItems.length === 0 ? (
                  <p className="px-4 py-5 text-xs text-slate-500 text-center">
                    No recent schedule edit requests.
                  </p>
                ) : (
                  topItems.map((item) => {
                    const title = item.course_code
                      ? `${item.course_code}${item.course_name ? ` — ${item.course_name}` : ''}`
                      : `Schedule #${item.schedule_id}`
                    return (
                      <div key={item.id} className="px-4 py-3 space-y-1 hover:bg-slate-50/80">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-xs font-semibold text-slate-800 truncate">
                            {title}
                          </span>
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase shrink-0 ${
                              item.status === 'approved'
                                ? 'bg-emerald-100 text-emerald-800'
                                : item.status === 'rejected'
                                  ? 'bg-red-100 text-red-800'
                                  : 'bg-amber-100 text-amber-800'
                            }`}
                          >
                            {item.status}
                          </span>
                        </div>
                        {item.requester_name && (
                          <div className="text-[11px] font-medium text-slate-500">
                            {item.requester_name}
                          </div>
                        )}
                        <p className="text-xs text-slate-600 line-clamp-2">
                          {item.requested_changes}
                        </p>
                      </div>
                    )
                  })
                )}
              </div>

              <div className="px-4 py-2.5 bg-slate-50 border-t border-slate-200">
                {inRouter ? (
                  <Link
                    to="/"
                    onClick={() => setIsNotificationsOpen(false)}
                    className="inline-flex items-center space-x-1 text-xs font-semibold text-blue-700 hover:text-blue-800"
                  >
                    <span>View Full Request Queue</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                ) : (
                  <a
                    href="/"
                    className="inline-flex items-center space-x-1 text-xs font-semibold text-blue-700 hover:text-blue-800"
                  >
                    <span>View Full Request Queue</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </a>
                )}
              </div>
            </div>
          )}
        </div>

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
