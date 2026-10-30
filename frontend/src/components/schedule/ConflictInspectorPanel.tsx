import React from 'react'
import { ShieldCheck, AlertTriangle, GitCompare } from 'lucide-react'
import { Card, CardHeader, CardTitle, CardContent, Badge, Button } from '../ui'
import { ScheduleEvent } from '../../types/api'
import { detectScheduleConflicts } from '../../utils/conflictDetector'

export interface ConflictInspectorPanelProps {
  events: ScheduleEvent[]
  onOpenComparison?: () => void
}

export const ConflictInspectorPanel: React.FC<ConflictInspectorPanelProps> = ({
  events,
  onOpenComparison,
}) => {
  const conflicts = detectScheduleConflicts(events)
  const hardConflicts = conflicts.filter((c) => c.severity === 'hard')
  const softWarnings = conflicts.filter((c) => c.severity === 'soft')
  const isClean = hardConflicts.length === 0

  return (
    <Card data-testid="conflict-inspector-panel">
      <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center space-x-3">
          <div
            className={`p-2.5 rounded-xl ${
              isClean ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-600'
            }`}
          >
            {isClean ? (
              <ShieldCheck className="w-5 h-5" />
            ) : (
              <AlertTriangle className="w-5 h-5" />
            )}
          </div>
          <div>
            <CardTitle>Real-Time Constraint & Conflict Auditor</CardTitle>
            <p className="text-xs text-slate-500 mt-0.5">
              Audited {events.length} scheduled events for room, instructor, and teaching load constraints
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <Badge variant={isClean ? 'success' : 'danger'} dot>
            {isClean
              ? '0 Hard Conflicts Certified'
              : `${hardConflicts.length} Hard Conflict(s)`}
          </Badge>
          {softWarnings.length > 0 && (
            <Badge variant="warning">{softWarnings.length} Overload Warning(s)</Badge>
          )}
          {onOpenComparison && (
            <Button
              size="sm"
              variant="secondary"
              leftIcon={<GitCompare className="w-4 h-4" />}
              onClick={onOpenComparison}
              data-testid="open-semester-comparison-btn"
            >
              Compare Semesters
            </Button>
          )}
        </div>
      </CardHeader>

      {conflicts.length > 0 && (
        <CardContent className="space-y-2.5">
          {conflicts.map((item) => (
            <div
              key={item.id}
              className={`p-3 rounded-xl border text-xs flex items-start justify-between gap-3 ${
                item.severity === 'hard'
                  ? 'bg-red-50/70 border-red-200 text-red-900'
                  : 'bg-amber-50/70 border-amber-200 text-amber-900'
              }`}
              data-testid={`conflict-item-${item.type}`}
            >
              <div>
                <span className="font-bold uppercase tracking-wide mr-2">
                  [{item.type.replace(/_/g, ' ')}]
                </span>
                <span>{item.description}</span>
              </div>
              <Badge variant={item.severity === 'hard' ? 'danger' : 'warning'}>
                {item.severity.toUpperCase()}
              </Badge>
            </div>
          ))}
        </CardContent>
      )}
    </Card>
  )
}

export default ConflictInspectorPanel
