import React from 'react'
import { CalendarDays, Users, School, Sparkles, ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Card, CardHeader, CardTitle, CardContent, Badge, Button } from '../components/ui'

export const DashboardPage: React.FC = () => {
  const stats = [
    { label: 'Total Faculty', value: '20', sub: 'CS, ECE, Math, Biology, Chem', icon: Users, color: 'text-blue-600', bg: 'bg-blue-50' },
    { label: 'Active Courses', value: '40', sub: 'Undergrad & Graduate Courses', icon: CalendarDays, color: 'text-indigo-600', bg: 'bg-indigo-50' },
    { label: 'Classrooms & Labs', value: '12', sub: 'RH, FH, MN, SCB Buildings', icon: School, color: 'text-emerald-600', bg: 'bg-emerald-50' },
    { label: 'Semesters Covered', value: '6 Terms', sub: 'Fall 2024 – Spring 2027', icon: Sparkles, color: 'text-amber-600', bg: 'bg-amber-50' },
  ]

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Coordinator Dashboard</h1>
        <p className="text-sm text-slate-500 mt-1">
          OptiSched constraint satisfaction engine overview and sprint planning status.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        {stats.map((s, idx) => {
          const Icon = s.icon
          return (
            <Card key={idx} hoverable className="p-5 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">{s.label}</span>
                <div className={`p-2 rounded-xl ${s.bg} ${s.color}`}>
                  <Icon className="w-5 h-5" />
                </div>
              </div>
              <div className="text-2xl font-extrabold text-slate-800">{s.value}</div>
              <div className="text-xs text-slate-500">{s.sub}</div>
            </Card>
          )
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card hoverable className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Sprint 0 Status & Architecture</CardTitle>
            <Badge variant="success" dot>
              Scaffolding Complete
            </Badge>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-slate-600 leading-relaxed">
              The Google OR-Tools CP-SAT core solver is modularized and verified against 25/25 automated test cases spanning 6 consecutive academic terms. The FastAPI backend and React frontend are scaffolded with formal OpenAPI contracts.
            </p>
            <div className="pt-2 flex items-center space-x-3">
              <Link to="/schedule">
                <Button variant="primary" size="sm" rightIcon={<ArrowRight className="w-4 h-4" />}>
                  View Master Schedule
                </Button>
              </Link>
              <Link to="/preferences">
                <Button variant="secondary" size="sm">
                  Preference Setup
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>

        <Card hoverable>
          <CardHeader>
            <CardTitle>Team Ownership</CardTitle>
            <Badge variant="gold">Sprint 0</Badge>
          </CardHeader>
          <CardContent>
            <ul className="space-y-3 text-xs">
              <li className="flex justify-between pb-2 border-b border-slate-100">
                <span className="font-semibold text-slate-700">Joe (Coordinator)</span>
                <span className="text-slate-500">OR-Tools Engine</span>
              </li>
              <li className="flex justify-between pb-2 border-b border-slate-100">
                <span className="font-semibold text-slate-700">Tony (Backend)</span>
                <span className="text-slate-500">FastAPI & SQLModel</span>
              </li>
              <li className="flex justify-between pb-2 border-b border-slate-100">
                <span className="font-semibold text-slate-700">Tina (Frontend)</span>
                <span className="text-slate-500">Shell & Forms</span>
              </li>
              <li className="flex justify-between">
                <span className="font-semibold text-slate-700">Sal (Frontend)</span>
                <span className="text-slate-500">Matrix & API Client</span>
              </li>
            </ul>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default DashboardPage
