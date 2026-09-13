import React from 'react'
import { NavLink } from 'react-router-dom'
import { LayoutDashboard, CalendarDays, Sliders, ShieldCheck, BookOpen } from 'lucide-react'

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/schedule', label: 'Master Schedule', icon: CalendarDays },
  { to: '/preferences', label: 'Instructor Prefs', icon: Sliders },
  { to: '/admin', label: 'Administration', icon: ShieldCheck },
]

export const Sidebar: React.FC = () => {
  return (
    <aside className="w-64 bg-white border-r border-slate-200 flex flex-col justify-between p-4 min-h-[calc(100vh-4rem)]">
      <div className="space-y-1">
        <div className="px-3 py-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
          Navigation
        </div>
        {navItems.map((item) => {
          const Icon = item.icon
          return (
            <NavLink
              key={item.to}
              to={item.to}
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
        <div className="flex items-center space-x-2 font-semibold text-slate-800">
          <BookOpen className="w-4 h-4 text-blue-600" />
          <span>CS 5551 Project</span>
        </div>
        <p className="text-slate-500 leading-relaxed">
          UMKC School of Science & Engineering 6-Term Scheduling Solver
        </p>
      </div>
    </aside>
  )
}
