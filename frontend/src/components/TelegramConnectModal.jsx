import React, { useState, useEffect, useRef } from 'react'
import {
  X,
  QrCode,
  Phone,
  ShieldCheck,
  RefreshCw,
  LogOut,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Lock,
  Bot,
} from 'lucide-react'
import {
  getTelegramAuthStatus,
  startTelegramQr,
  checkTelegramQr,
  requestTelegramPhoneCode,
  submitTelegramCode,
  submitTelegramPassword,
  disconnectTelegram,
} from '../services/api'
import { useDialog } from '../context/DialogContext'

export default function TelegramConnectModal({ isOpen, onClose, onStatusChange }) {
  const { confirm, showToast } = useDialog()
  const [activeTab, setActiveTab] = useState('qr') // 'qr' | 'phone'
  const [authStatus, setAuthStatus] = useState(null)
  const [isLoadingStatus, setIsLoadingStatus] = useState(true)

  // QR state
  const [qrData, setQrData] = useState(null)
  const [isQrLoading, setIsQrLoading] = useState(false)
  const [qrError, setQrError] = useState(null)

  // Phone & Code state
  const [phoneNumber, setPhoneNumber] = useState('')
  const [verificationCode, setVerificationCode] = useState('')
  const [twoFaPassword, setTwoFaPassword] = useState('')
  const [passwordHint, setPasswordHint] = useState(null)
  const [phoneStep, setPhoneStep] = useState('phone') // 'phone' | 'code' | 'password'
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [phoneError, setPhoneError] = useState(null)

  const pollIntervalRef = useRef(null)

  // Load initial status whenever modal opens
  useEffect(() => {
    if (!isOpen) {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current)
      return
    }

    const fetchStatus = async () => {
      setIsLoadingStatus(true)
      try {
        const res = await getTelegramAuthStatus()
        setAuthStatus(res)
        if (onStatusChange) onStatusChange(res)

        // If disconnected and on QR tab, trigger QR code start
        if (!res.connected && activeTab === 'qr') {
          loadQr()
        }
      } catch (err) {
        console.warn('Failed to load status:', err)
      } finally {
        setIsLoadingStatus(false)
      }
    }

    fetchStatus()

    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current)
    }
  }, [isOpen])

  // ESC key to close
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  // Start QR login
  const loadQr = async () => {
    setIsQrLoading(true)
    setQrError(null)
    if (pollIntervalRef.current) clearInterval(pollIntervalRef.current)

    try {
      const data = await startTelegramQr()
      setQrData(data)

      // Start polling checkTelegramQr every 2.5 seconds
      pollIntervalRef.current = setInterval(async () => {
        try {
          const checkRes = await checkTelegramQr()
          if (checkRes.status === 'connected') {
            clearInterval(pollIntervalRef.current)
            const updated = await getTelegramAuthStatus()
            setAuthStatus(updated)
            if (onStatusChange) onStatusChange(updated)
          } else if (checkRes.status === 'expired') {
            clearInterval(pollIntervalRef.current)
            setQrError('QR code has expired. Please refresh.')
          }
        } catch {
          // Ignore transient network errors during poll
        }
      }, 2500)
    } catch (err) {
      setQrError(err.message || 'Failed to generate QR code')
    } finally {
      setIsQrLoading(false)
    }
  }

  // Switch tabs
  const handleTabChange = (tab) => {
    setActiveTab(tab)
    setPhoneError(null)
    setQrError(null)
    if (tab === 'qr' && !authStatus?.connected && !qrData) {
      loadQr()
    } else if (tab !== 'qr') {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current)
    }
  }

  // Phone flow: Send Code
  const handleRequestPhoneCode = async (e) => {
    e.preventDefault()
    if (!phoneNumber.trim()) return

    setIsSubmitting(true)
    setPhoneError(null)
    try {
      const res = await requestTelegramPhoneCode(phoneNumber.trim())
      if (res.status === 'code_pending') {
        setPhoneStep('code')
      } else {
        setPhoneError(res.message || 'Failed to send code')
      }
    } catch (err) {
      setPhoneError(err.message || 'Error sending code')
    } finally {
      setIsSubmitting(false)
    }
  }

  // Phone flow: Submit Verification Code
  const handleSubmitCode = async (e) => {
    e.preventDefault()
    if (!verificationCode.trim()) return

    setIsSubmitting(true)
    setPhoneError(null)
    try {
      const res = await submitTelegramCode(verificationCode.trim())
      if (res.status === 'connected') {
        const updated = await getTelegramAuthStatus()
        setAuthStatus(updated)
        if (onStatusChange) onStatusChange(updated)
      } else if (res.status === 'password_pending') {
        setPasswordHint(res.hint || null)
        setPhoneStep('password')
      } else {
        setPhoneError(res.message || 'Invalid code')
      }
    } catch (err) {
      setPhoneError(err.message || 'Verification failed')
    } finally {
      setIsSubmitting(false)
    }
  }

  // Phone flow: Submit 2FA Password
  const handleSubmitPassword = async (e) => {
    e.preventDefault()
    if (!twoFaPassword.trim()) return

    setIsSubmitting(true)
    setPhoneError(null)
    try {
      const res = await submitTelegramPassword(twoFaPassword.trim())
      if (res.status === 'connected') {
        const updated = await getTelegramAuthStatus()
        setAuthStatus(updated)
        if (onStatusChange) onStatusChange(updated)
      } else {
        setPhoneError(res.message || 'Incorrect password')
      }
    } catch (err) {
      setPhoneError(err.message || '2FA verification failed')
    } finally {
      setIsSubmitting(false)
    }
  }

  // Disconnect Flow
  const handleDisconnect = async () => {
    const shouldDisconnect = await confirm({
      title: 'Disconnect Telegram Account',
      description:
        'Are you sure you want to disconnect your Telegram account from Cineforge? You will need to scan a new QR code or sign in with your phone to reconnect.',
      confirmText: 'Disconnect',
      cancelText: 'Cancel',
      confirmVariant: 'danger',
      icon: LogOut,
    })

    if (!shouldDisconnect) {
      return
    }

    setIsSubmitting(true)
    try {
      await disconnectTelegram()
      setAuthStatus({ connected: false, status: 'disconnected', user: null })
      setQrData(null)
      setPhoneStep('phone')
      setPhoneNumber('')
      setVerificationCode('')
      setTwoFaPassword('')
      if (onStatusChange) onStatusChange({ connected: false, status: 'disconnected', user: null })
      showToast({
        type: 'success',
        title: 'Disconnected',
        message: 'Your Telegram account has been disconnected and the local session was removed.',
      })
    } catch (err) {
      console.error('[Cineforge Telegram Disconnect Error]', err)
      showToast({
        type: 'error',
        title: 'Disconnect Failed',
        message: 'Unable to disconnect from Telegram. Please check your connection and try again.',
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!isOpen) return null

  const isConnected = authStatus?.connected
  const user = authStatus?.user

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 10000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: 'rgba(4, 5, 8, 0.85)',
        backdropFilter: 'blur(10px)',
        padding: '16px',
      }}
      onClick={onClose}
    >
      <div
        className="telegram-modal-card"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="telegram-modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '10px',
                backgroundColor: 'rgba(0, 136, 204, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#29b6f6',
              }}
            >
              <ShieldCheck size={20} />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: '1.12rem', fontWeight: 700, color: '#f3f4f6', letterSpacing: '-0.01em' }}>
                Telegram Account
              </h3>
              <p style={{ margin: '2px 0 0', fontSize: '0.8rem', color: '#9ca3af' }}>
                Secure local connection for Cineforge Desktop
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: '#9ca3af',
              cursor: 'pointer',
              padding: '6px',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'color 0.15s',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = '#f3f4f6')}
            onMouseLeave={(e) => (e.currentTarget.style.color = '#9ca3af')}
            title="Close (Esc)"
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Body */}
        <div className="telegram-modal-body">
          {isLoadingStatus ? (
            <div style={{ textAlign: 'center', padding: '40px 0', color: '#9ca3af' }}>
              <Loader2 size={32} className="spin" style={{ margin: '0 auto 12px' }} />
              <p>Checking Telegram connection status...</p>
            </div>
          ) : isConnected ? (
            /* Connected View */
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '16px',
                  padding: '16px',
                  backgroundColor: 'rgba(34, 197, 94, 0.1)',
                  border: '1px solid rgba(34, 197, 94, 0.25)',
                  borderRadius: '12px',
                }}
              >
                <div
                  style={{
                    width: '48px',
                    height: '48px',
                    borderRadius: '50%',
                    backgroundColor: '#16a34a',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#fff',
                    fontWeight: 'bold',
                    fontSize: '1.2rem',
                  }}
                >
                  {user?.first_name ? user.first_name[0].toUpperCase() : 'T'}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <strong style={{ fontSize: '1.05rem', color: '#f9fafb' }}>
                      {user?.first_name} {user?.last_name || ''}
                    </strong>
                    <span
                      style={{
                        fontSize: '0.75rem',
                        padding: '2px 8px',
                        borderRadius: '9999px',
                        backgroundColor: '#15803d',
                        color: '#dcfce7',
                        fontWeight: 500,
                      }}
                    >
                      Connected
                    </span>
                  </div>
                  {user?.username && (
                    <div style={{ fontSize: '0.85rem', color: '#29b6f6', marginTop: '2px' }}>
                      @{user.username}
                    </div>
                  )}
                  {user?.phone && (
                    <div style={{ fontSize: '0.8rem', color: '#9ca3af', marginTop: '2px' }}>
                      {user.phone}
                    </div>
                  )}
                </div>
              </div>

              <div
                style={{
                  padding: '14px',
                  backgroundColor: 'rgba(255, 255, 255, 0.04)',
                  borderRadius: '10px',
                  fontSize: '0.82rem',
                  color: '#9ca3af',
                  lineHeight: 1.5,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#e5e7eb', marginBottom: '6px' }}>
                  <Lock size={15} style={{ color: '#22c55e' }} />
                  <strong>Windows DPAPI Protected</strong>
                </div>
                Your Telegram session is encrypted directly on your PC with Windows DPAPI. Your session token is never uploaded to cloud servers or Supabase.
              </div>

              {/* Personal Streamer Bot Status */}
              <div
                style={{
                  padding: '14px',
                  backgroundColor: 'rgba(41, 182, 246, 0.08)',
                  border: '1px solid rgba(41, 182, 246, 0.2)',
                  borderRadius: '10px',
                  fontSize: '0.82rem',
                  color: '#9ca3af',
                  lineHeight: 1.5,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#e5e7eb' }}>
                    <Bot size={15} style={{ color: '#29b6f6' }} />
                    <strong>Personal Streamer Bot</strong>
                  </div>
                  <span style={{ fontSize: '0.72rem', color: '#38bdf8', backgroundColor: 'rgba(56, 189, 248, 0.15)', padding: '2px 8px', borderRadius: '4px', fontWeight: 600 }}>
                    Private & Local
                  </span>
                </div>
                {authStatus?.personal_bot ? (
                  <div style={{ color: '#f3f4f6', fontWeight: 600, fontSize: '0.9rem' }}>
                    @{authStatus.personal_bot.bot_username}
                  </div>
                ) : (
                  <div>
                    Automatically provisioned for your account. Streams directly to your local PC without public channels.
                  </div>
                )}
              </div>

              <button
                type="button"
                onClick={handleDisconnect}
                disabled={isSubmitting}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px',
                  padding: '12px 18px',
                  backgroundColor: 'rgba(239, 68, 68, 0.15)',
                  border: '1px solid rgba(239, 68, 68, 0.3)',
                  color: '#f87171',
                  borderRadius: '10px',
                  cursor: isSubmitting ? 'not-allowed' : 'pointer',
                  fontWeight: 600,
                  fontSize: '0.9rem',
                  transition: 'all 0.2s',
                }}
              >
                {isSubmitting ? (
                  <Loader2 size={16} className="spin" />
                ) : (
                  <LogOut size={16} />
                )}
                Disconnect Telegram Account
              </button>
            </div>
          ) : (
            /* Disconnected / Connect Flow */
            <div>
              {/* Managed Streamer Bot Notice / Disclosure */}
              <div
                style={{
                  padding: '12px 14px',
                  backgroundColor: 'rgba(0, 136, 204, 0.08)',
                  border: '1px solid rgba(0, 136, 204, 0.22)',
                  borderRadius: '10px',
                  fontSize: '0.8rem',
                  color: '#cbd5e1',
                  lineHeight: 1.45,
                  marginBottom: '16px',
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '10px',
                }}
              >
                <Bot size={18} style={{ color: '#38bdf8', flexShrink: 0, marginTop: '2px' }} />
                <div>
                  <strong style={{ color: '#f8fafc', display: 'block', marginBottom: '2px' }}>
                    Personal Streamer Bot Included
                  </strong>
                  Cineforge will create one personal streamer bot for your Telegram account to deliver local streams privately without cloud proxies or shared bots.
                </div>
              </div>

              {/* Tab Selector */}
              <div
                style={{
                  display: 'flex',
                  gap: '8px',
                  backgroundColor: 'rgba(255, 255, 255, 0.05)',
                  padding: '4px',
                  borderRadius: '10px',
                  marginBottom: '20px',
                }}
              >
                <button
                  type="button"
                  onClick={() => handleTabChange('qr')}
                  style={{
                    flex: 1,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px',
                    padding: '8px 14px',
                    borderRadius: '8px',
                    border: 'none',
                    fontSize: '0.88rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    backgroundColor: activeTab === 'qr' ? 'rgba(0, 136, 204, 0.25)' : 'transparent',
                    color: activeTab === 'qr' ? '#38bdf8' : '#9ca3af',
                    transition: 'all 0.15s',
                  }}
                >
                  <QrCode size={16} />
                  QR Code (Fast)
                </button>
                <button
                  type="button"
                  onClick={() => handleTabChange('phone')}
                  style={{
                    flex: 1,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px',
                    padding: '8px 14px',
                    borderRadius: '8px',
                    border: 'none',
                    fontSize: '0.88rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    backgroundColor: activeTab === 'phone' ? 'rgba(0, 136, 204, 0.25)' : 'transparent',
                    color: activeTab === 'phone' ? '#38bdf8' : '#9ca3af',
                    transition: 'all 0.15s',
                  }}
                >
                  <Phone size={16} />
                  Phone & Code
                </button>
              </div>

              {/* QR Code Tab Content */}
              {activeTab === 'qr' && (
                <div style={{ textAlign: 'center', width: '100%' }}>
                  {isQrLoading ? (
                    <div style={{ padding: '48px 0', color: '#9ca3af' }}>
                      <Loader2 size={34} className="spin" style={{ margin: '0 auto 14px', color: '#38bdf8' }} />
                      <p style={{ margin: 0, fontSize: '0.9rem', color: '#cbd5e1' }}>Generating secure login QR code...</p>
                    </div>
                  ) : qrError ? (
                    <div style={{ padding: '32px 16px' }}>
                      <AlertCircle size={34} style={{ color: '#ef4444', margin: '0 auto 12px' }} />
                      <p style={{ color: '#f87171', fontSize: '0.9rem', marginBottom: '16px', lineHeight: 1.5 }}>
                        {qrError}
                      </p>
                      <button
                        type="button"
                        onClick={loadQr}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '6px',
                          padding: '9px 18px',
                          borderRadius: '8px',
                          backgroundColor: '#0284c7',
                          color: '#fff',
                          border: 'none',
                          cursor: 'pointer',
                          fontWeight: 600,
                          fontSize: '0.88rem',
                          boxShadow: '0 4px 12px rgba(2, 132, 199, 0.35)',
                        }}
                      >
                        <RefreshCw size={14} />
                        Retry QR Code
                      </button>
                    </div>
                  ) : qrData ? (
                    <div className="telegram-qr-card-container">
                      {/* High-contrast centered QR Code Card */}
                      <div
                        className="telegram-qr-card"
                        dangerouslySetInnerHTML={{ __html: qrData.qr_svg }}
                      />

                      {/* Instructions */}
                      <div className="telegram-qr-instructions">
                        <h4>How to connect:</h4>
                        <ol className="telegram-qr-steps">
                          <li>
                            <span className="telegram-step-badge">1</span>
                            <span>Open <strong>Telegram</strong> on your phone</span>
                          </li>
                          <li>
                            <span className="telegram-step-badge">2</span>
                            <span>Go to <strong>Settings → Devices → Link Desktop Device</strong></span>
                          </li>
                          <li>
                            <span className="telegram-step-badge">3</span>
                            <span>Point your camera at this QR code to confirm</span>
                          </li>
                        </ol>
                      </div>

                      {/* Status Bar & Refresh Action */}
                      <div className="telegram-qr-status-bar">
                        <div className="telegram-status-pill">
                          <span className="telegram-pulse-dot" />
                          <span>Waiting for approval on your phone...</span>
                        </div>
                        <button
                          type="button"
                          className="telegram-qr-refresh-btn"
                          onClick={loadQr}
                          disabled={isQrLoading}
                          title="Refresh QR Code"
                        >
                          <RefreshCw size={12} className={isQrLoading ? 'spin' : ''} />
                          <span>Refresh</span>
                        </button>
                      </div>
                    </div>
                  ) : null}
                </div>
              )}

              {/* Phone & Code Tab Content */}
              {activeTab === 'phone' && (
                <div>
                  {phoneError && (
                    <div
                      style={{
                        padding: '10px 14px',
                        backgroundColor: 'rgba(239, 68, 68, 0.15)',
                        border: '1px solid rgba(239, 68, 68, 0.3)',
                        borderRadius: '8px',
                        color: '#f87171',
                        fontSize: '0.85rem',
                        marginBottom: '16px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                      }}
                    >
                      <AlertCircle size={16} />
                      {phoneError}
                    </div>
                  )}

                  {phoneStep === 'phone' && (
                    <form onSubmit={handleRequestPhoneCode} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                      <div>
                        <label style={{ display: 'block', fontSize: '0.82rem', color: '#9ca3af', marginBottom: '6px' }}>
                          Phone Number (with international country code)
                        </label>
                        <input
                          type="tel"
                          placeholder="+1 234 567 8900"
                          value={phoneNumber}
                          onChange={(e) => setPhoneNumber(e.target.value)}
                          required
                          style={{
                            width: '100%',
                            boxSizing: 'border-box',
                            padding: '10px 14px',
                            backgroundColor: 'rgba(255, 255, 255, 0.05)',
                            border: '1px solid rgba(255, 255, 255, 0.12)',
                            borderRadius: '8px',
                            color: '#f9fafb',
                            fontSize: '0.95rem',
                          }}
                        />
                      </div>

                      <button
                        type="submit"
                        disabled={isSubmitting || !phoneNumber.trim()}
                        style={{
                          padding: '10px 16px',
                          borderRadius: '8px',
                          backgroundColor: '#0284c7',
                          color: '#fff',
                          border: 'none',
                          cursor: isSubmitting ? 'not-allowed' : 'pointer',
                          fontWeight: 600,
                          fontSize: '0.9rem',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          gap: '8px',
                        }}
                      >
                        {isSubmitting ? <Loader2 size={16} className="spin" /> : null}
                        Send Verification Code
                      </button>
                    </form>
                  )}

                  {phoneStep === 'code' && (
                    <form onSubmit={handleSubmitCode} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                      <div>
                        <label style={{ display: 'block', fontSize: '0.82rem', color: '#9ca3af', marginBottom: '6px' }}>
                          Enter Verification Code sent to your Telegram app:
                        </label>
                        <input
                          type="text"
                          placeholder="12345"
                          value={verificationCode}
                          onChange={(e) => setVerificationCode(e.target.value)}
                          required
                          style={{
                            width: '100%',
                            boxSizing: 'border-box',
                            padding: '10px 14px',
                            backgroundColor: 'rgba(255, 255, 255, 0.05)',
                            border: '1px solid rgba(255, 255, 255, 0.12)',
                            borderRadius: '8px',
                            color: '#f9fafb',
                            fontSize: '0.95rem',
                            letterSpacing: '2px',
                          }}
                        />
                      </div>

                      <div style={{ display: 'flex', gap: '10px' }}>
                        <button
                          type="button"
                          onClick={() => setPhoneStep('phone')}
                          style={{
                            flex: 1,
                            padding: '10px',
                            borderRadius: '8px',
                            backgroundColor: 'rgba(255, 255, 255, 0.08)',
                            color: '#e5e7eb',
                            border: 'none',
                            cursor: 'pointer',
                            fontWeight: 500,
                          }}
                        >
                          Back
                        </button>
                        <button
                          type="submit"
                          disabled={isSubmitting || !verificationCode.trim()}
                          style={{
                            flex: 2,
                            padding: '10px',
                            borderRadius: '8px',
                            backgroundColor: '#0284c7',
                            color: '#fff',
                            border: 'none',
                            cursor: isSubmitting ? 'not-allowed' : 'pointer',
                            fontWeight: 600,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '8px',
                          }}
                        >
                          {isSubmitting ? <Loader2 size={16} className="spin" /> : null}
                          Verify Code
                        </button>
                      </div>
                    </form>
                  )}

                  {phoneStep === 'password' && (
                    <form onSubmit={handleSubmitPassword} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                      <div
                        style={{
                          padding: '10px',
                          backgroundColor: 'rgba(56, 189, 248, 0.1)',
                          border: '1px solid rgba(56, 189, 248, 0.25)',
                          borderRadius: '8px',
                          fontSize: '0.85rem',
                          color: '#38bdf8',
                        }}
                      >
                        <strong>Two-Step Verification Enabled</strong>
                        {passwordHint && (
                          <div style={{ marginTop: '4px', fontSize: '0.8rem', color: '#9ca3af' }}>
                            Password Hint: <em>{passwordHint}</em>
                          </div>
                        )}
                      </div>

                      <div>
                        <label style={{ display: 'block', fontSize: '0.82rem', color: '#9ca3af', marginBottom: '6px' }}>
                          Two-Step Cloud Password:
                        </label>
                        <input
                          type="password"
                          placeholder="Your 2FA password"
                          value={twoFaPassword}
                          onChange={(e) => setTwoFaPassword(e.target.value)}
                          required
                          style={{
                            width: '100%',
                            boxSizing: 'border-box',
                            padding: '10px 14px',
                            backgroundColor: 'rgba(255, 255, 255, 0.05)',
                            border: '1px solid rgba(255, 255, 255, 0.12)',
                            borderRadius: '8px',
                            color: '#f9fafb',
                            fontSize: '0.95rem',
                          }}
                        />
                      </div>

                      <button
                        type="submit"
                        disabled={isSubmitting || !twoFaPassword.trim()}
                        style={{
                          padding: '10px',
                          borderRadius: '8px',
                          backgroundColor: '#0284c7',
                          color: '#fff',
                          border: 'none',
                          cursor: isSubmitting ? 'not-allowed' : 'pointer',
                          fontWeight: 600,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          gap: '8px',
                        }}
                      >
                        {isSubmitting ? <Loader2 size={16} className="spin" /> : null}
                        Confirm Password
                      </button>
                    </form>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
