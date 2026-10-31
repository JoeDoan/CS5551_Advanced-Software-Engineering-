import { apiClient } from './apiClient'
import { InstructorSummary } from '../types/api'

export const DEFAULT_INSTRUCTORS: InstructorSummary[] = [
  {
    id: 1,
    full_name: 'Dr. Yugyung Lee',
    email: 'leeyu@umkc.edu',
    department: 'Computer Science',
    priority_score: 5,
  },
  {
    id: 2,
    full_name: 'Dr. Praveen Rao',
    email: 'raopr@umkc.edu',
    department: 'Computer Science',
    priority_score: 5,
  },
  {
    id: 3,
    full_name: 'Dr. Ghulam Rasool',
    email: 'rasoolg@umkc.edu',
    department: 'Electrical & Computer Eng',
    priority_score: 5,
  },
  {
    id: 4,
    full_name: 'Dr. Liana Sega',
    email: 'segal@umkc.edu',
    department: 'Mathematics',
    priority_score: 5,
  },
]

export const instructorService = {
  async getInstructors(): Promise<InstructorSummary[]> {
    try {
      const response = await apiClient.get<InstructorSummary[]>('/instructors')
      if (Array.isArray(response.data) && response.data.length > 0) {
        return response.data
      }
      return DEFAULT_INSTRUCTORS
    } catch {
      return DEFAULT_INSTRUCTORS
    }
  },
}

export default instructorService
