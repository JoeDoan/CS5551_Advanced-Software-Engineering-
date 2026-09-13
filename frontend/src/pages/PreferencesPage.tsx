import { Clock, Info } from 'lucide-react'

export const PreferencesPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Instructor Preferences</h1>
        <p className="text-sm text-slate-500 mt-1">
          Specify teaching day patterns, time slot availability, and classroom layout needs.
        </p>
      </div>

      <div className="bg-blue-50/70 border border-blue-200 p-4 rounded-2xl flex items-start space-x-3 text-xs text-blue-800">
        <Info className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
        <div>
          <span className="font-bold">Sprint 0 Placeholder:</span> This form interface demonstrates
          Tina's component structure for Sprint 1. In Sprint 1, submitting this form will call{' '}
          <code className="bg-blue-100 px-1 py-0.5 rounded font-mono">POST /api/v1/preferences</code>.
        </div>
      </div>

      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-6">
        <h2 className="text-base font-bold text-slate-800">Teaching Availability Form</h2>

        <div className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Select Instructor</label>
            <select className="w-full sm:w-80 p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-medium text-slate-700 outline-none">
              <option>Dr. Yugyung Lee (Computer Science)</option>
              <option>Dr. Praveen Rao (Computer Science)</option>
              <option>Dr. Ghulam Rasool (Electrical & Computer Eng)</option>
              <option>Dr. Liana Sega (Mathematics)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-2">Preferred Days</label>
            <div className="flex flex-wrap gap-2">
              {['Monday (M)', 'Tuesday (T)', 'Wednesday (W)', 'Thursday (R)', 'Friday (F)'].map((day) => (
                <button
                  key={day}
                  type="button"
                  className="px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-medium text-slate-700 hover:bg-blue-50 hover:border-blue-300 transition-colors"
                >
                  {day}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-2">Preferred Time Slots</label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {['08:00 - 09:15', '09:30 - 10:45', '11:00 - 12:15', '13:00 - 14:15', '14:30 - 15:45', '16:00 - 17:15'].map((slot) => (
                <div key={slot} className="p-2.5 rounded-xl border border-slate-200 text-xs text-slate-600 bg-slate-50 flex items-center space-x-2">
                  <Clock className="w-3.5 h-3.5 text-slate-400" />
                  <span>{slot}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
