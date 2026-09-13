import React from 'react'
import { Calendar, Bell, User, CheckCircle2 } from 'lucide-react'

export const Navbar: React.FC = () => {
  return (
    <header className="h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between sticky top-0 z-30 shadow-sm">
      <div className="flex items-center space-x-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
          <Calendar className="w-5 h-5" />
        </div>
        <div>
          <span className="text-xl font-bold bg-gradient-to-r from-blue-700 to-indigo-700 bg-clip-text text-transparent">
            OptiSched
          </span>
          <span className="ml-2 text-xs font-semibold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
            Sprint 0
          </span>
        </div>
      </div>

      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-2 text-xs font-medium text-emerald-700 bg-emerald-50 px-3 py-1.5 rounded-lg border border-emerald-200">
          <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          <span>Solver: Ready (UMKC 6-Term)</span>
        </div>

        <button className="p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors">
          <Bell className="w-5 h-5" />
        </button>

        <div className="flex items-center space-x-3 pl-2 border-l border-slate-200">
          <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center text-slate-700 font-semibold text-sm">
            <User className="w-4 h-4" />
          </div>
          <div className="hidden md:block text-left text-xs">
            <div className="font-semibold text-slate-800">Course Coordinator</div>
            <div className="text-slate-500">coordinator@umkc.edu</div>
          </div>
        </div>
      </div>
    </header>
  )
}
