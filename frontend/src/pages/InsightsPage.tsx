import React, { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { BottleneckBoard } from '../components/insights/BottleneckBoard'
import { ForecastPanel } from '../components/insights/ForecastPanel'
import { WhatIfPanel } from '../components/insights/WhatIfPanel'
import { AuthRole } from '../types/api'

type Tab = 'forecast' | 'bottlenecks' | 'whatif'

const TABS: { id: Tab; label: string }[] = [
  { id: 'forecast', label: 'Demand Forecast' },
  { id: 'bottlenecks', label: 'Bottlenecks' },
  { id: 'whatif', label: 'What-If Simulator' },
]

export const InsightsPage: React.FC = () => {
  const { user } = useAuth()
  const role: AuthRole = user?.role ?? 'coordinator'
  const [tab, setTab] = useState<Tab>('forecast')

  return (
    <div className="space-y-6" data-testid="insights-page">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Insights</h1>
        <p className="text-sm text-slate-500 mt-1">
          Predict next-term demand, find room-capacity bottlenecks, and test what-if scenarios
          with the CP-SAT solver.
        </p>
      </div>

      <div className="flex gap-2 border-b border-slate-200" role="tablist">
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            aria-selected={tab === t.id}
            onClick={() => setTab(t.id)}
            data-testid={`tab-${t.id}`}
            className={`px-4 py-2 text-sm font-semibold border-b-2 -mb-px transition-colors ${
              tab === t.id
                ? 'border-blue-600 text-blue-700'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'forecast' && <ForecastPanel />}
      {tab === 'bottlenecks' && <BottleneckBoard />}
      {tab === 'whatif' && <WhatIfPanel role={role} userName={user?.full_name ?? ''} />}
    </div>
  )
}

export default InsightsPage
