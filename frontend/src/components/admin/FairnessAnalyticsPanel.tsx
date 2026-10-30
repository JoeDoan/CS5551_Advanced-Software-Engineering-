import React, { useEffect, useState } from 'react'
import { Scale, Users, Award } from 'lucide-react'
import { Card, CardHeader, CardTitle, CardContent, Badge, Select } from '../ui'
import { analyticsService, FairnessReport } from '../../services/analyticsService'

export interface FairnessAnalyticsPanelProps {
  semesterId?: number
}

export const FairnessAnalyticsPanel: React.FC<FairnessAnalyticsPanelProps> = ({
  semesterId = 1,
}) => {
  const [report, setReport] = useState<FairnessReport | null>(null)
  const [deptFilter, setDeptFilter] = useState<string>('ALL')

  useEffect(() => {
    analyticsService.getFairnessReport(semesterId).then(setReport)
  }, [semesterId])

  if (!report) {
    return (
      <Card>
        <CardContent>
          <p className="text-xs text-slate-500 py-4">Loading faculty fairness analytics...</p>
        </CardContent>
      </Card>
    )
  }

  const filteredInstructors = report.instructors.filter((inst) =>
    deptFilter === 'ALL' ? true : inst.department.toUpperCase() === deptFilter.toUpperCase()
  )

  return (
    <Card data-testid="fairness-analytics-panel">
      <CardHeader>
        <div className="flex items-center space-x-3">
          <div className="p-2.5 rounded-xl bg-blue-50 text-blue-600">
            <Scale className="w-5 h-5" />
          </div>
          <div>
            <CardTitle>Faculty Priority & Fairness Analytics</CardTitle>
            <p className="text-xs text-slate-500 mt-0.5">
              Dynamic priority compensation and Gini equity index across {report.total_instructors} instructors
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <Badge variant="success" dot>
            Gini Index: {report.priority_gini_index.toFixed(4)}
          </Badge>
          <Badge variant="gold">
            Avg Satisfaction: {report.average_satisfaction_rate}%
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 bg-slate-50 p-3.5 rounded-xl border border-slate-200/80 text-xs">
          <div className="flex items-center space-x-2.5">
            <Users className="w-4 h-4 text-blue-600" />
            <div>
              <p className="text-slate-400">Scheduled Sections</p>
              <p className="font-bold text-slate-800">{report.total_scheduled_courses} Courses</p>
            </div>
          </div>
          <div className="flex items-center space-x-2.5">
            <Award className="w-4 h-4 text-amber-600" />
            <div>
              <p className="text-slate-400">Workload Gini Balance</p>
              <p className="font-bold text-slate-800">{report.workload_gini_index.toFixed(4)} (Balanced)</p>
            </div>
          </div>
          <div>
            <Select
              value={deptFilter}
              onChange={(e) => setDeptFilter(e.target.value)}
              options={[
                { value: 'ALL', label: 'All Departments' },
                { value: 'CS', label: 'Computer Science (CS)' },
                { value: 'ECE', label: 'ECE' },
                { value: 'MATH', label: 'Mathematics' },
                { value: 'CHEM', label: 'Chemistry' },
                { value: 'BIOL', label: 'Biology' },
              ]}
              data-testid="fairness-dept-filter"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500 uppercase">
                <th className="py-2 px-3">Instructor</th>
                <th className="py-2 px-3">Dept</th>
                <th className="py-2 px-3">Priority Score</th>
                <th className="py-2 px-3">Course Load</th>
                <th className="py-2 px-3">Pref Matches</th>
                <th className="py-2 px-3">Satisfaction</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredInstructors.map((inst) => (
                <tr key={inst.user_id} className="hover:bg-slate-50">
                  <td className="py-2.5 px-3 font-semibold text-slate-800">
                    {inst.instructor_name}
                  </td>
                  <td className="py-2.5 px-3">
                    <Badge variant="info">{inst.department}</Badge>
                  </td>
                  <td className="py-2.5 px-3 font-mono text-slate-700">
                    {inst.priority_score.toLocaleString()}
                  </td>
                  <td className="py-2.5 px-3 text-slate-600">
                    {inst.assigned_courses_count} courses
                  </td>
                  <td className="py-2.5 px-3 text-slate-600">
                    {inst.preferred_day_matches} day / {inst.preferred_room_matches} room
                  </td>
                  <td className="py-2.5 px-3">
                    <div className="flex items-center space-x-2">
                      <div className="w-20 bg-slate-200 h-2 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            inst.satisfaction_rate >= 90
                              ? 'bg-emerald-500'
                              : inst.satisfaction_rate >= 70
                                ? 'bg-amber-500'
                                : 'bg-red-500'
                          }`}
                          style={{ width: `${Math.min(100, inst.satisfaction_rate)}%` }}
                        />
                      </div>
                      <span className="font-semibold text-slate-700">
                        {inst.satisfaction_rate}%
                      </span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}

export default FairnessAnalyticsPanel
