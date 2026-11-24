import React, { useEffect, useRef } from 'react'
import { AlertCircle, AlertTriangle, Loader2, X } from 'lucide-react'

/**
 * Cineforge Accessible Confirmation Modal
 * Replaces browser-native `confirm()` with a themed dialog matching Cineby aesthetics.
 */
export default function ConfirmModal({
  isOpen,
  title = 'Are you sure?',
  description = 'Please confirm this action to proceed.',
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  confirmVariant = 'danger', // 'danger' | 'primary'
  icon: Icon = AlertCircle,
  isLoading = false,
  onConfirm,
  onCancel,
}) {
  const cancelBtnRef = useRef(null)
  const confirmBtnRef = useRef(null)

  // Auto-focus the cancel button when opened for safe keyboard interaction
  useEffect(() => {
    if (isOpen) {
      const timer = setTimeout(() => {
        cancelBtnRef.current?.focus()
      }, 50)
      return () => clearTimeout(timer)
    }
  }, [isOpen])

  // Keyboard navigation: Escape cancels, Enter confirms
  useEffect(() => {
    if (!isOpen) return

    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && !isLoading) {
        e.preventDefault()
        onCancel?.()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, isLoading, onCancel])

  if (!isOpen) return null

  const isDanger = confirmVariant === 'danger'

  return (
    <div
      className="cineforge-dialog-backdrop"
      role="presentation"
      onClick={() => {
        if (!isLoading) onCancel?.()
      }}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 10001,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: 'rgba(4, 5, 8, 0.82)',
        backdropFilter: 'blur(10px)',
        padding: '16px',
        animation: 'fadeIn 0.15s ease-out',
      }}
    >
      <div
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        aria-describedby="confirm-dialog-desc"
        className="cineforge-dialog-card"
        onClick={(e) => e.stopPropagation()}
        style={{
          width: '100%',
          maxWidth: '440px',
          backgroundColor: '#0c0e14',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          borderRadius: '16px',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.85), 0 0 30px rgba(0, 0, 0, 0.5)',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          animation: 'scaleIn 0.18s cubic-bezier(0.16, 1, 0.3, 1)',
        }}
      >
        {/* Header & Icon */}
        <div
          style={{
            padding: '24px 24px 16px',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '16px',
          }}
        >
          <div
            style={{
              width: '42px',
              height: '42px',
              borderRadius: '12px',
              backgroundColor: isDanger ? 'rgba(239, 68, 68, 0.15)' : 'rgba(232, 67, 53, 0.15)',
              border: `1px solid ${isDanger ? 'rgba(239, 68, 68, 0.3)' : 'rgba(232, 67, 53, 0.3)'}`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: isDanger ? '#f87171' : '#e84335',
              flexShrink: 0,
            }}
          >
            <Icon size={22} />
          </div>

          <div style={{ flex: 1 }}>
            <h3
              id="confirm-dialog-title"
              style={{
                margin: 0,
                fontSize: '1.12rem',
                fontWeight: 700,
                color: '#f5f5f2',
                fontFamily: 'inherit',
                letterSpacing: '-0.02em',
              }}
            >
              {title}
            </h3>
            <p
              id="confirm-dialog-desc"
              style={{
                margin: '8px 0 0',
                fontSize: '0.88rem',
                color: '#a7abb5',
                lineHeight: 1.55,
              }}
            >
              {description}
            </p>
          </div>

          <button
            type="button"
            onClick={onCancel}
            disabled={isLoading}
            aria-label="Close dialog"
            style={{
              background: 'transparent',
              border: 'none',
              color: '#747883',
              cursor: isLoading ? 'not-allowed' : 'pointer',
              padding: '4px',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'color 0.15s',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = '#f5f5f2')}
            onMouseLeave={(e) => (e.currentTarget.style.color = '#747883')}
          >
            <X size={18} />
          </button>
        </div>

        {/* Footer Actions */}
        <div
          style={{
            padding: '16px 24px 20px',
            backgroundColor: 'rgba(255, 255, 255, 0.02)',
            borderTop: '1px solid rgba(255, 255, 255, 0.05)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'flex-end',
            gap: '12px',
          }}
        >
          <button
            ref={cancelBtnRef}
            type="button"
            onClick={onCancel}
            disabled={isLoading}
            style={{
              padding: '9px 18px',
              borderRadius: '9px',
              backgroundColor: 'transparent',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              color: '#d1d5db',
              fontSize: '0.88rem',
              fontWeight: 600,
              cursor: isLoading ? 'not-allowed' : 'pointer',
              transition: 'all 0.15s',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.06)'
              e.currentTarget.style.color = '#ffffff'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'transparent'
              e.currentTarget.style.color = '#d1d5db'
            }}
          >
            {cancelText}
          </button>

          <button
            ref={confirmBtnRef}
            type="button"
            onClick={onConfirm}
            disabled={isLoading}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              padding: '9px 20px',
              borderRadius: '9px',
              backgroundColor: isDanger ? '#dc2626' : '#e84335',
              border: 'none',
              color: '#ffffff',
              fontSize: '0.88rem',
              fontWeight: 600,
              cursor: isLoading ? 'not-allowed' : 'pointer',
              boxShadow: isDanger
                ? '0 4px 14px rgba(220, 38, 38, 0.4)'
                : '0 4px 14px rgba(232, 67, 53, 0.4)',
              transition: 'all 0.15s',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = isDanger ? '#ef4444' : '#ff5242'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = isDanger ? '#dc2626' : '#e84335'
            }}
          >
            {isLoading && <Loader2 size={15} className="spin" />}
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  )
}
