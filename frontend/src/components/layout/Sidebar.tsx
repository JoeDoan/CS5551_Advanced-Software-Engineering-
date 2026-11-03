import React from 'react'
import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  CalendarDays,
  Sliders,
  ShieldCheck,
  BookOpen,
  Layers,
  Users,
  LineChart,
  Lightbulb,
} from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { AuthRole } from '../../types/api'

interface NavItem {
  to: string
  label: string
  icon: React.ComponentType<{ className?: string }>
  roles?: AuthRole[]
}

const navItems: NavItem[] = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/schedule', label: 'Master Schedule', icon: CalendarDays },
  { to: '/insights', label: 'Insights', icon: LineChart },
  { to: '/commercialization', label: 'Commercialization', icon: Lightbulb },
  { to: '/courses', label: 'Courses & Sections', icon: Layers, roles: ['coordinator'] },
  { to: '/users', label: 'User Accounts', icon: Users, roles: ['coordinator'] },
  { to: '/preferences', label: 'Instructor Prefs', icon: Sliders, roles: ['instructor'] },
  { to: '/admin', label: 'Administration', icon: ShieldCheck, roles: ['coordinator'] },
]

export const Sidebar: React.FC = () => {
  const { user } = useAuth()
  const activeRole: AuthRole = user?.role ?? 'coordinator'

  const visibleItems = navItems.filter(
    (item) => !item.roles || item.roles.includes(activeRole)
  )

  return (
    <aside className="w-64 bg-white border-r border-slate-200 flex flex-col justify-between p-4 min-h-[calc(100vh-4rem)]">
      <div className="space-y-1">
        <div className="px-3 py-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
          Navigation
        </div>
        {visibleItems.map((item) => {
          const Icon = item.icon
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `flex items-center space-x-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-blue-50 text-blue-700 font-semibold shadow-sm'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                }`
              }
            >
              <Icon className="w-4 h-4" />
              <span>{item.label}</span>
            </NavLink>
          )
        })}
      </div>

      <div className="p-4 rounded-xl bg-gradient-to-br from-slate-50 to-blue-50/50 border border-slate-200 text-xs text-slate-600 space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2 font-semibold text-slate-800">
            <BookOpen className="w-4 h-4 text-blue-600" />
            <span>CS 5551 Project</span>
          </div>
          <span
            className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase bg-blue-100 text-blue-800"
            data-testid="sidebar-role-badge"
          >
            {activeRole}
          </span>
        </div>
        <p className="text-slate-500 leading-relaxed">
          {activeRole === 'coordinator'
            ? 'Coordinator Access: Catalog CRUD, User Accounts, Section Assignment & OR-Tools Solver'
            : 'Faculty Access: Master Schedule, Teaching Preferences & Edit Requests'}
        </p>
      </div>
    </aside>
  )
}
