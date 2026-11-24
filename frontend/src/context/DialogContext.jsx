import React, { createContext, useContext, useState, useCallback } from 'react'
import ConfirmModal from '../components/ConfirmModal'
import ToastContainer from '../components/Toast'

const DialogContext = createContext(null)

export function DialogProvider({ children }) {
  const [confirmState, setConfirmState] = useState({
    isOpen: false,
    title: '',
    description: '',
    confirmText: 'Confirm',
    cancelText: 'Cancel',
    confirmVariant: 'danger',
    icon: undefined,
    isLoading: false,
    resolve: null,
  })

  const [toasts, setToasts] = useState([])

  /**
   * Shows a Cineforge confirmation dialog.
   * Returns a promise resolving to boolean (true if confirmed, false if cancelled).
   */
  const confirm = useCallback((options = {}) => {
    return new Promise((resolve) => {
      setConfirmState({
        isOpen: true,
        title: options.title || 'Confirm Action',
        description: options.description || 'Are you sure you want to proceed?',
        confirmText: options.confirmText || 'Confirm',
        cancelText: options.cancelText || 'Cancel',
        confirmVariant: options.confirmVariant || 'danger',
        icon: options.icon,
        isLoading: false,
        resolve,
      })
    })
  }, [])

  const handleConfirmAction = useCallback(() => {
    if (confirmState.resolve) {
      confirmState.resolve(true)
    }
    setConfirmState((prev) => ({ ...prev, isOpen: false }))
  }, [confirmState])

  const handleCancelAction = useCallback(() => {
    if (confirmState.resolve) {
      confirmState.resolve(false)
    }
    setConfirmState((prev) => ({ ...prev, isOpen: false }))
  }, [confirmState])

  /**
   * Triggers a Cineforge toast notification.
   */
  const showToast = useCallback((toast) => {
    const id = Date.now() + Math.random().toString(36).substring(2, 6)
    const newToast = {
      id,
      type: toast.type || 'info', // 'success' | 'error' | 'info'
      title: toast.title,
      message: toast.message || '',
      duration: toast.duration ?? 4500,
    }
    setToasts((prev) => [...prev, newToast])
    return id
  }, [])

  const dismissToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  return (
    <DialogContext.Provider value={{ confirm, showToast, dismissToast }}>
      {children}

      <ConfirmModal
        isOpen={confirmState.isOpen}
        title={confirmState.title}
        description={confirmState.description}
        confirmText={confirmState.confirmText}
        cancelText={confirmState.cancelText}
        confirmVariant={confirmState.confirmVariant}
        icon={confirmState.icon}
        isLoading={confirmState.isLoading}
        onConfirm={handleConfirmAction}
        onCancel={handleCancelAction}
      />

      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </DialogContext.Provider>
  )
}

export function useDialog() {
  const context = useContext(DialogContext)
  if (!context) {
    // Provide safe fallback functions in case called outside provider
    return {
      confirm: async ({ description }) => window.confirm(description || 'Are you sure?'),
      showToast: ({ message }) => console.log('[Cineforge Toast]', message),
      dismissToast: () => {},
    }
  }
  return context
}
