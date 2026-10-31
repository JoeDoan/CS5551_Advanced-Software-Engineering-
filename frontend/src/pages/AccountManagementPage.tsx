import React from 'react'
import { AccountManager } from '../components/admin/AccountManager'
import { Alert } from '../components/ui'

export const AccountManagementPage: React.FC = () => {
  return (
    <div className="space-y-6" data-testid="account-management-page">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">User & Role Management</h1>
        <p className="text-sm text-slate-500 mt-1">
          Atomic Faculty profile provisioning, role assignment, password resets, and immediate session
          revocation for disabled or removed accounts.
        </p>
      </div>

      <Alert variant="info" title="Atomic Provisioning & Access Governance">
        Creating a <strong>Faculty Instructor</strong> account automatically provisions and links a
        corresponding Faculty teaching profile for semester preferences and section assignments.
        Disabling or deleting an account revokes active bearer sessions immediately.
      </Alert>

      <AccountManager />
    </div>
  )
}

export default AccountManagementPage
