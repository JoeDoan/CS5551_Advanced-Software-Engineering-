import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { Edit2, KeyRound, Power, Search, Trash2, UserPlus } from 'lucide-react'
import {
  Alert,
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Input,
  Modal,
  Select,
} from '../ui'
import { Toast } from '../common/Toast'
import { useAuth } from '../../context/AuthContext'
import { authService } from '../../services/authService'
import { AccountAdminItem, AuthRole } from '../../types/api'

const DEPARTMENT_OPTIONS = [
  { value: 'CS', label: 'CS (Computer Science)' },
  { value: 'ECE', label: 'ECE (Electrical & Computer Eng)' },
  { value: 'MATH', label: 'MATH (Mathematics)' },
  { value: 'CHEM', label: 'CHEM (Chemistry)' },
  { value: 'BIOL', label: 'BIOL (Biological Sciences)' },
]

const ROLE_FILTER_OPTIONS = [
  { value: 'ALL', label: 'All Roles' },
  { value: 'coordinator', label: 'Coordinators' },
  { value: 'instructor', label: 'Faculty Instructors' },
]

const MODAL_ROLE_OPTIONS = [
  {
    value: 'instructor',
    label: 'Faculty Instructor (Creates Teaching & Schedule Profile)',
  },
  {
    value: 'coordinator',
    label: 'Course Coordinator (Full Admin, CRUD & Solver Access)',
  },
]

type ModalState =
  | { status: 'closed' }
  | { status: 'create' }
  | { status: 'edit'; account: AccountAdminItem }

interface AccountFormState {
  role: AuthRole
  fullName: string
  email: string
  username: string
  usernameManuallyEdited: boolean
  department: string
  password: string
}

const INITIAL_FORM_STATE: AccountFormState = {
  role: 'instructor',
  fullName: '',
  email: '',
  username: '',
  usernameManuallyEdited: false,
  department: 'CS',
  password: '',
}

export const AccountManager: React.FC = () => {
  const { user: currentUser } = useAuth()
  const [accounts, setAccounts] = useState<AccountAdminItem[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [search, setSearch] = useState<string>('')
  const [roleFilter, setRoleFilter] = useState<string>('ALL')

  const [modalState, setModalState] = useState<ModalState>({ status: 'closed' })
  const [form, setForm] = useState<AccountFormState>(INITIAL_FORM_STATE)
  const [modalError, setModalError] = useState<string | null>(null)
  const [saving, setSaving] = useState<boolean>(false)
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  const loadAccounts = useCallback(async () => {
    setLoading(true)
    setLoadError(null)
    try {
      const data = await authService.getAccounts()
      setAccounts(data)
    } catch (err) {
      setLoadError((err as Error).message || 'Failed to load user accounts.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadAccounts()
  }, [loadAccounts])

  const editingAccount = modalState.status === 'edit' ? modalState.account : null
  const isModalOpen = modalState.status !== 'closed'

  const coordinatorCount = useMemo(
    () => accounts.filter((a) => a.role === 'coordinator').length,
    [accounts]
  )
  const instructorCount = useMemo(
    () => accounts.filter((a) => a.role === 'instructor').length,
    [accounts]
  )

  const filteredAccounts = useMemo(() => {
    const q = search.trim().toLowerCase()
    return accounts.filter((account) => {
      const matchesRole = roleFilter === 'ALL' || account.role === roleFilter
      const matchesSearch =
        !q ||
        account.full_name.toLowerCase().includes(q) ||
        account.email.toLowerCase().includes(q) ||
        account.username.toLowerCase().includes(q) ||
        account.department.toLowerCase().includes(q)
      return matchesRole && matchesSearch
    })
  }, [accounts, roleFilter, search])

  const openCreateModal = () => {
    setForm(INITIAL_FORM_STATE)
    setModalError(null)
    setModalState({ status: 'create' })
  }

  const openEditModal = (account: AccountAdminItem) => {
    setForm({
      role: account.role,
      fullName: account.full_name,
      email: account.email,
      username: account.username,
      usernameManuallyEdited: true,
      department: account.department || 'CS',
      password: '',
    })
    setModalError(null)
    setModalState({ status: 'edit', account })
  }

  const closeModal = () => {
    setModalState({ status: 'closed' })
    setModalError(null)
  }

  const handleEmailChange = (nextEmail: string) => {
    setForm((prev) => {
      if (modalState.status !== 'create' || prev.usernameManuallyEdited) {
        return { ...prev, email: nextEmail }
      }
      const derived = nextEmail.split('@')[0]?.trim().toLowerCase() ?? ''
      return {
        ...prev,
        email: nextEmail,
        username: derived,
      }
    })
  }

  const handleUsernameChange = (nextUsername: string) => {
    setForm((prev) => ({
      ...prev,
      username: nextUsername,
      usernameManuallyEdited: nextUsername.trim().length > 0,
    }))
  }

  const handleSaveAccount = async () => {
    setModalError(null)

    if (!form.fullName.trim()) {
      setModalError('Full name is required.')
      return
    }

    if (modalState.status === 'create') {
      const trimmedEmail = form.email.trim()
      if (!trimmedEmail || !trimmedEmail.includes('@')) {
        setModalError('A valid UMKC email address is required.')
        return
      }
      if (form.password.length < 6) {
        setModalError('Initial password must be at least 6 characters.')
        return
      }
    } else if (form.password.length > 0 && form.password.length < 6) {
      setModalError('Reset password must be at least 6 characters.')
      return
    }

    setSaving(true)
    try {
      if (editingAccount) {
        const updated = await authService.updateAccount(editingAccount.id, {
          full_name: form.fullName.trim(),
          department: form.department,
          role: form.role,
          ...(form.password ? { password: form.password } : {}),
        })
        setAccounts((prev) => prev.map((a) => (a.id === editingAccount.id ? updated : a)))
        setToast({
          type: 'success',
          message: `Updated account for ${updated.full_name}`,
        })
      } else {
        const created = await authService.createAccount({
          full_name: form.fullName.trim(),
          email: form.email.trim().toLowerCase(),
          username:
            form.username.trim().toLowerCase() ||
            form.email.trim().toLowerCase().split('@')[0],
          password: form.password,
          role: form.role,
          department: form.department,
        })
        setAccounts((prev) => [...prev, created])
        setToast({
          type: 'success',
          message: `Provisioned ${created.role} account for ${created.full_name}`,
        })
      }
      closeModal()
    } catch (err) {
      setModalError((err as Error).message || 'Failed to save user account.')
    } finally {
      setSaving(false)
    }
  }

  const handleToggleAccountStatus = async (account: AccountAdminItem) => {
    const nextActive = !account.is_active
    try {
      const updated = await authService.updateAccount(account.id, {
        is_active: nextActive,
      })
      setAccounts((prev) => prev.map((a) => (a.id === account.id ? updated : a)))
      setToast({
        type: 'success',
        message: `${updated.is_active ? 'Enabled' : 'Disabled'} account @${updated.username}`,
      })
    } catch (err) {
      setToast({
        type: 'error',
        message: (err as Error).message || 'Failed to update account status.',
      })
    }
  }

  const handleDeleteAccount = async (account: AccountAdminItem) => {
    try {
      await authService.deleteAccount(account.id)
      setAccounts((prev) => prev.filter((a) => a.id !== account.id))
      setToast({
        type: 'success',
        message: `Removed account ${account.email}`,
      })
    } catch (err) {
      setToast({
        type: 'error',
        message: (err as Error).message || 'Failed to delete account.',
      })
    }
  }

  return (
    <Card data-testid="account-manager">
      <CardHeader>
        <div className="flex flex-wrap items-center gap-2.5">
          <div>
            <CardTitle>Account Provisioning & Access Control</CardTitle>
            <p className="text-xs text-slate-500 mt-0.5">
              Provision faculty instructors and course coordinators, reset credentials, or revoke access
            </p>
          </div>
          <Badge variant="gold" data-testid="coordinator-count-badge">
            {coordinatorCount} {coordinatorCount === 1 ? 'Coordinator' : 'Coordinators'}
          </Badge>
          <Badge variant="info" data-testid="instructor-count-badge">
            {instructorCount} {instructorCount === 1 ? 'Instructor' : 'Instructors'}
          </Badge>
        </div>

        <Button
          size="sm"
          variant="primary"
          leftIcon={<UserPlus className="w-4 h-4" />}
          onClick={openCreateModal}
          data-testid="create-account-btn"
        >
          Create Account
        </Button>
      </CardHeader>

      <CardContent className="space-y-4">
        {loadError && (
          <Alert variant="danger" title="Account Directory Error" onClose={() => setLoadError(null)}>
            {loadError}
          </Alert>
        )}

        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1">
            <Input
              placeholder="Search name, email, username, or department..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              leftIcon={<Search className="w-4 h-4" />}
              data-testid="account-search-input"
            />
          </div>
          <div className="w-full sm:w-56">
            <Select
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
              options={ROLE_FILTER_OPTIONS}
              data-testid="account-role-filter"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500 uppercase">
                <th className="py-2.5 px-3">User</th>
                <th className="py-2.5 px-3">Email</th>
                <th className="py-2.5 px-3">Role</th>
                <th className="py-2.5 px-3">Dept</th>
                <th className="py-2.5 px-3">Faculty Profile</th>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan={7} className="py-6 text-center text-slate-500">
                    Loading user accounts...
                  </td>
                </tr>
              ) : filteredAccounts.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-6 text-center text-slate-500">
                    No user accounts match the current search or role filter.
                  </td>
                </tr>
              ) : (
                filteredAccounts.map((account) => {
                  const isSelf =
                    Boolean(currentUser?.email) &&
                    account.email.toLowerCase() === currentUser?.email.toLowerCase()

                  return (
                    <tr key={account.id} className="hover:bg-slate-50">
                      <td className="py-2.5 px-3">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-slate-800">{account.full_name}</span>
                          {isSelf && <Badge variant="info">You</Badge>}
                        </div>
                        <div className="text-[11px] text-slate-500 font-mono">@{account.username}</div>
                      </td>
                      <td className="py-2.5 px-3 text-slate-600">{account.email}</td>
                      <td className="py-2.5 px-3">
                        <Badge variant={account.role === 'coordinator' ? 'gold' : 'info'}>
                          {account.role.toUpperCase()}
                        </Badge>
                      </td>
                      <td className="py-2.5 px-3">
                        <Badge variant="neutral">{account.department}</Badge>
                      </td>
                      <td className="py-2.5 px-3 text-slate-600 font-medium">
                        {account.role === 'coordinator'
                          ? 'Admin Portal'
                          : `Faculty #${account.linked_user_id ?? account.id}`}
                      </td>
                      <td className="py-2.5 px-3">
                        {account.is_active ? (
                          <Badge variant="success" dot>
                            Active
                          </Badge>
                        ) : (
                          <Badge variant="danger">Disabled</Badge>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-right space-x-1 whitespace-nowrap">
                        <Button
                          size="sm"
                          variant="ghost"
                          leftIcon={
                            editingAccount?.id === account.id ? (
                              <KeyRound className="w-3.5 h-3.5" />
                            ) : (
                              <Edit2 className="w-3.5 h-3.5" />
                            )
                          }
                          onClick={() => openEditModal(account)}
                          data-testid={`edit-account-${account.id}`}
                        >
                          Edit / Reset Password
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={isSelf}
                          leftIcon={<Power className="w-3.5 h-3.5" />}
                          onClick={() => handleToggleAccountStatus(account)}
                          data-testid={`toggle-account-${account.id}`}
                        >
                          {account.is_active ? 'Disable' : 'Enable'}
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          disabled={isSelf}
                          onClick={() => handleDeleteAccount(account)}
                          aria-label={`Delete ${account.full_name}`}
                          data-testid={`delete-account-${account.id}`}
                        >
                          <Trash2 className="w-3.5 h-3.5 text-red-600" />
                        </Button>
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </CardContent>

      <Modal
        isOpen={isModalOpen}
        onClose={closeModal}
        title={editingAccount ? `Edit Account (@${editingAccount.username})` : 'Provision New Account'}
        description={
          editingAccount
            ? 'Update role, department, or issue a credential reset'
            : 'Creates an authenticated UMKC portal login and links a Faculty profile when applicable'
        }
        footer={
          <>
            <Button variant="secondary" size="sm" onClick={closeModal}>
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              isLoading={saving}
              onClick={handleSaveAccount}
              data-testid="save-account-btn"
            >
              {editingAccount ? 'Save Changes' : 'Create Account'}
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          {modalError && (
            <Alert variant="danger" title="Account Provisioning Error">
              {modalError}
            </Alert>
          )}

          <Select
            label="System Role"
            value={form.role}
            disabled={
              Boolean(editingAccount) &&
              Boolean(currentUser?.email) &&
              editingAccount?.email.toLowerCase() === currentUser?.email.toLowerCase()
            }
            onChange={(e) => setForm((prev) => ({ ...prev, role: e.target.value as AuthRole }))}
            options={MODAL_ROLE_OPTIONS}
            data-testid="modal-account-role"
          />

          <Input
            label="Full Name"
            value={form.fullName}
            onChange={(e) => setForm((prev) => ({ ...prev, fullName: e.target.value }))}
            placeholder="e.g. Dr. Jane Doe"
            data-testid="modal-account-fullname"
          />

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Input
              label="UMKC Email"
              type="email"
              value={form.email}
              disabled={Boolean(editingAccount)}
              onChange={(e) => handleEmailChange(e.target.value)}
              placeholder="e.g. jdoe@umkc.edu"
              data-testid="modal-account-email"
            />

            <Input
              label="Username"
              value={form.username}
              disabled={Boolean(editingAccount)}
              onChange={(e) => handleUsernameChange(e.target.value)}
              placeholder="e.g. jdoe"
              data-testid="modal-account-username"
            />
          </div>

          <Select
            label="Department"
            value={form.department}
            onChange={(e) => setForm((prev) => ({ ...prev, department: e.target.value }))}
            options={DEPARTMENT_OPTIONS}
            data-testid="modal-account-department"
          />

          <Input
            label={
              editingAccount
                ? 'Reset Password (leave blank to keep current)'
                : 'Initial Password (min 6 chars)'
            }
            type="password"
            value={form.password}
            onChange={(e) => setForm((prev) => ({ ...prev, password: e.target.value }))}
            placeholder={editingAccount ? 'Leave blank to keep current password' : 'Enter temporary password'}
            data-testid="modal-account-password"
          />
        </div>
      </Modal>

      {toast && <Toast type={toast.type} message={toast.message} onClose={() => setToast(null)} />}
    </Card>
  )
}

export default AccountManager
