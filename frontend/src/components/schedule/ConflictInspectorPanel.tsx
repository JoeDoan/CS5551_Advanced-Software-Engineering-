import React, { useMemo, useState } from 'react'
import clsx from 'clsx'
import {
  ShieldCheck,
  AlertTriangle,
  GitCompare,
  ChevronDown,
  ChevronUp,
  Search,
} from 'lucide-react'
import { Card, CardHeader, CardTitle, CardContent, Badge, Button } from '../ui'
import { ScheduleEvent } from '../../types/api'
import { detectScheduleConflicts } from '../../utils/conflictDetector'

export interface ConflictInspectorPanelProps {
  events: ScheduleEvent[]
  onOpenComparison?: () => void
}

type ConflictSeverityFilter = 'ALL' | 'hard' | 'soft'

export const ConflictInspectorPanel: React.FC<ConflictInspectorPanelProps> = ({
  events,
  onOpenComparison,
}) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(false)
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [severityFilter, setSeverityFilter] = useState<ConflictSeverityFilter>('ALL')

  const conflicts = useMemo(() => detectScheduleConflicts(events), [events])
  const hardConflicts = useMemo(
    () => conflicts.filter((c) => c.severity === 'hard'),
    [conflicts]
  )
  const softWarnings = useMemo(
    () => conflicts.filter((c) => c.severity === 'soft'),
    [conflicts]
  )
  const isClean = hardConflicts.length === 0

  const filteredConflicts = useMemo(() => {
    const query = searchQuery.trim().toLowerCase()
    return conflicts.filter((item) => {
      if (severityFilter !== 'ALL' && item.severity !== severityFilter) {
        return false
      }
      if (!query) {
        return true
      }
      const normalizedType = item.type.replace(/_/g, ' ').toLowerCase()
      return (
        item.description.toLowerCase().includes(query) ||
        item.type.toLowerCase().includes(query) ||
        normalizedType.includes(query) ||
        item.courseCodes.some((code) => code.toLowerCase().includes(query)) ||
        (item.instructorName || '').toLowerCase().includes(query) ||
        (item.roomNumber || '').toLowerCase().includes(query) ||
        (item.timeSlotLabel || '').toLowerCase().includes(query)
      )
    })
  }, [conflicts, searchQuery, severityFilter])

  const severityOptions: Array<{ value: ConflictSeverityFilter; label: string }> = [
    { value: 'ALL', label: `ALL (${conflicts.length})` },
    { value: 'hard', label: `hard (${hardConflicts.length})` },
    { value: 'soft', label: `soft (${softWarnings.length})` },
  ]

  return (
    <Card data-testid="conflict-inspector-panel">
      <CardHeader
        className={clsx(
          'flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3 py-3.5 px-5',
          !isExpanded && 'border-b-0'
        )}
      >
        <div className="flex items-center space-x-3">
          <div
            className={clsx(
              'p-2 rounded-xl shrink-0',
              isClean ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-600'
            )}
          >
            {isClean ? (
              <ShieldCheck className="w-4 h-4" />
            ) : (
              <AlertTriangle className="w-4 h-4" />
            )}
          </div>
          <div>
            <CardTitle className="text-sm">Real-Time Constraint & Conflict Auditor</CardTitle>
            <p className="text-xs text-slate-500 mt-0.5">
              Audited {events.length} scheduled events for room, instructor, and teaching load constraints
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={isClean ? 'success' : 'danger'} dot>
            {isClean
              ? '0 Hard Conflicts Certified'
              : `${hardConflicts.length} Hard Conflict(s)`}
          </Badge>
          {softWarnings.length > 0 && (
            <Badge variant="warning">{softWarnings.length} Overload Warning(s)</Badge>
          )}
          <Button
            type="button"
            size="sm"
            variant="outline"
            leftIcon={
              isExpanded ? (
                <ChevronUp className="w-3.5 h-3.5" />
              ) : (
                <ChevronDown className="w-3.5 h-3.5" />
              )
            }
            onClick={() => setIsExpanded((prev) => !prev)}
            data-testid="toggle-conflict-auditor-btn"
          >
            {isExpanded ? 'Hide Constraints' : `View Constraints (${conflicts.length})`}
          </Button>
          {onOpenComparison && (
            <Button
              type="button"
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

      {isExpanded && (
        <CardContent className="p-5 pt-4 space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="relative flex-1">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                <Search className="w-3.5 h-3.5" />
              </div>
              <input
                type="text"
                aria-label="Search constraints"
                data-testid="conflict-search-input"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search conflicts by course, instructor, room, or rule type..."
                className="w-full pl-9 pr-3 py-1.5 text-xs rounded-xl border border-slate-200 bg-slate-50 text-slate-700 placeholder-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-colors"
              />
            </div>

            <div className="inline-flex items-center rounded-xl bg-slate-100 p-1 gap-1 self-start sm:self-auto">
              {severityOptions.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  data-testid={`conflict-severity-${opt.value}`}
                  onClick={() => setSeverityFilter(opt.value)}
                  className={clsx(
                    'px-2.5 py-1 rounded-lg text-xs font-semibold transition-colors',
                    severityFilter === opt.value
                      ? 'bg-white text-slate-900 shadow-sm'
                      : 'text-slate-600 hover:text-slate-900'
                  )}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {conflicts.length === 0 ? (
            <div className="rounded-xl border border-emerald-200 bg-emerald-50/60 px-4 py-3 text-xs text-emerald-800 font-medium">
              All room, instructor availability, and teaching load constraints are satisfied with zero violations.
            </div>
          ) : filteredConflicts.length === 0 ? (
            <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-xs text-slate-600">
              No constraints or warnings match your search filter.
            </div>
          ) : (
            <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
              {filteredConflicts.map((item) => (
                <div
                  key={item.id}
                  className={clsx(
                    'p-3 rounded-xl border text-xs flex items-start justify-between gap-3',
                    item.severity === 'hard'
                      ? 'bg-red-50/70 border-red-200 text-red-900'
                      : 'bg-amber-50/70 border-amber-200 text-amber-900'
                  )}
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
            </div>
          )}
        </CardContent>
      )}
    </Card>
  )
}

export default ConflictInspectorPanel
