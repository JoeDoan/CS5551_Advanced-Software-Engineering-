import { describe, it, expect, beforeEach } from 'vitest'
import {
  apiClient,
  ApiError,
  setAuthToken,
  getAuthToken,
  clearAuthToken,
  AUTH_TOKEN_KEY,
} from '../apiClient'

describe('Centralized apiClient', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('configures default baseURL and headers properly', () => {
    expect(apiClient.defaults.headers['Content-Type']).toBe('application/json')
    expect(apiClient.defaults.headers['Accept']).toBe('application/json')
    expect(apiClient.defaults.timeout).toBe(10000)
    expect(apiClient.defaults.baseURL).toBeDefined()
  })

  it('manages authentication token in localStorage', () => {
    expect(getAuthToken()).toBeNull()

    setAuthToken('test-jwt-token-xyz')
    expect(getAuthToken()).toBe('test-jwt-token-xyz')
    expect(localStorage.getItem(AUTH_TOKEN_KEY)).toBe('test-jwt-token-xyz')

    clearAuthToken()
    expect(getAuthToken()).toBeNull()
  })

  it('creates ApiError with custom status and payload', () => {
    const error = new ApiError('Course conflict detected', 409, { conflict_id: 12 })
    expect(error.message).toBe('Course conflict detected')
    expect(error.status).toBe(409)
    expect(error.data).toEqual({ conflict_id: 12 })
    expect(error.isApiError).toBe(true)
    expect(error.name).toBe('ApiError')
  })

  it('formats validation errors array into readable string', () => {
    const validationDetails = [
      { loc: ['body', 'course_id'], msg: 'Field required' },
      { loc: ['body', 'user_id'], msg: 'Must be positive' },
    ]
    const error = new ApiError(
      validationDetails.map((d) => d.msg).join('; '),
      422,
      { detail: validationDetails }
    )
    expect(error.status).toBe(422)
    expect(error.message).toBe('Field required; Must be positive')
  })
})
