import React from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { ProtectedRoute } from './components/auth/ProtectedRoute'
import { AppLayout } from './components/layout/AppLayout'
import { LoginPage } from './pages/LoginPage'
import { DashboardPage } from './pages/DashboardPage'
import { SchedulePage } from './pages/SchedulePage'
import { PreferencesPage } from './pages/PreferencesPage'
import { CatalogManagementPage } from './pages/CatalogManagementPage'
import { AccountManagementPage } from './pages/AccountManagementPage'
import { AdminPage } from './pages/AdminPage'
import { InsightsPage } from './pages/InsightsPage'
import { CommercializationPage } from './pages/CommercializationPage'

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="schedule" element={<SchedulePage />} />
        <Route path="insights" element={<InsightsPage />} />
        <Route path="commercialization" element={<CommercializationPage />} />
        <Route
          path="preferences"
          element={
            <ProtectedRoute allowedRoles={['instructor']}>
              <PreferencesPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="courses"
          element={
            <ProtectedRoute allowedRoles={['coordinator']}>
              <CatalogManagementPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="users"
          element={
            <ProtectedRoute allowedRoles={['coordinator']}>
              <AccountManagementPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="admin"
          element={
            <ProtectedRoute allowedRoles={['coordinator']}>
              <AdminPage />
            </ProtectedRoute>
          }
        />
      </Route>
    </Routes>
  )
}

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
