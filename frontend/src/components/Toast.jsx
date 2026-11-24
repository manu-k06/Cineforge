import React, { useEffect } from 'react'
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react'

/**
 * Cineforge Toast Notification Item
 */
export function ToastItem({ toast, onDismiss }) {
  useEffect(() => {
    if (toast.duration !== 0) {
      const timer = setTimeout(() => {
        onDismiss(toast.id)
      }, toast.duration || 4500)
      return () => clearTimeout(timer)
    }
  }, [toast, onDismiss])

  const isError = toast.type === 'error'
  const isSuccess = toast.type === 'success'

  const iconColor = isError ? '#f87171' : isSuccess ? '#4ade80' : '#38bdf8'
  const borderColor = isError
    ? 'rgba(239, 68, 68, 0.35)'
    : isSuccess
    ? 'rgba(34, 197, 94, 0.35)'
    : 'rgba(56, 189, 248, 0.35)'
  const glowColor = isError
    ? 'rgba(239, 68, 68, 0.15)'
    : isSuccess
    ? 'rgba(34, 197, 94, 0.15)'
    : 'rgba(56, 189, 248, 0.15)'

  return (
    <div
      role="status"
      aria-live="polite"
      className="cineforge-toast-item"
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: '12px',
        padding: '14px 18px',
        backgroundColor: '#0d0f17',
        border: `1px solid ${borderColor}`,
        borderRadius: '12px',
        boxShadow: `0 10px 25px rgba(0, 0, 0, 0.6), 0 0 20px ${glowColor}`,
        maxWidth: '380px',
        minWidth: '280px',
        color: '#f5f5f2',
        pointerEvents: 'auto',
        animation: 'slideUpFade 0.22s cubic-bezier(0.16, 1, 0.3, 1)',
      }}
    >
      <div style={{ flexShrink: 0, marginTop: '2px', color: iconColor }}>
        {isError ? (
          <AlertCircle size={18} />
        ) : isSuccess ? (
          <CheckCircle2 size={18} />
        ) : (
          <Info size={18} />
        )}
      </div>

      <div style={{ flex: 1, minWidth: 0 }}>
        {toast.title && (
          <div
            style={{
              fontSize: '0.88rem',
              fontWeight: 600,
              color: '#ffffff',
              marginBottom: '2px',
            }}
          >
            {toast.title}
          </div>
        )}
        <div
          style={{
            fontSize: '0.82rem',
            color: '#a7abb5',
            lineHeight: 1.45,
            wordBreak: 'break-word',
          }}
        >
          {toast.message}
        </div>
      </div>

      <button
        type="button"
        onClick={() => onDismiss(toast.id)}
        aria-label="Dismiss notification"
        style={{
          background: 'none',
          border: 'none',
          color: '#6b7280',
          cursor: 'pointer',
          padding: '2px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
          borderRadius: '6px',
        }}
      >
        <X size={15} />
      </button>
    </div>
  )
}

/**
 * Cineforge Toast Notification Container
 * Renders stacked notifications in the viewport.
 */
export default function ToastContainer({ toasts = [], onDismiss }) {
  if (!toasts || toasts.length === 0) return null

  return (
    <div
      style={{
        position: 'fixed',
        bottom: '24px',
        right: '24px',
        zIndex: 10005,
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
        pointerEvents: 'none',
      }}
    >
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onDismiss={onDismiss} />
      ))}
    </div>
  )
}
