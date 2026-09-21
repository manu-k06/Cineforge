import React, { useState, useEffect } from 'react'
import { X, Mail, Lock, User, AlertCircle, CheckCircle2, Loader2, Sparkles } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

export default function AuthModal({ isOpen, onClose }) {
  const { signIn, signUp } = useAuth()
  const [activeTab, setActiveTab] = useState('signin') // 'signin' | 'signup'

  // Form fields
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  // UI state
  const [error, setError] = useState(null)
  const [successMsg, setSuccessMsg] = useState(null)
  const [loading, setLoading] = useState(false)

  // Reset form when modal opens or closes
  useEffect(() => {
    if (isOpen) {
      setError(null)
      setSuccessMsg(null)
    }
  }, [isOpen, activeTab])

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  if (!isOpen) return null

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setSuccessMsg(null)

    if (activeTab === 'signup') {
      if (!fullName.trim()) {
        setError('Please enter your full name.')
        return
      }
      if (password !== confirmPassword) {
        setError('Passwords do not match.')
        return
      }
      if (password.length < 6) {
        setError('Password must be at least 6 characters long.')
        return
      }

      setLoading(true)
      try {
        const data = await signUp(email.trim(), password, fullName.trim())
        if (data?.user && !data?.session) {
          setSuccessMsg('Account created! Please check your email inbox to confirm your account.')
        } else {
          setSuccessMsg('Welcome to Cineforge! You are now logged in.')
          setTimeout(() => {
            onClose()
          }, 1200)
        }
      } catch (err) {
        setError(err.message || 'Failed to create account. Please try again.')
      } finally {
        setLoading(false)
      }
    } else {
      // Sign In
      setLoading(true)
      try {
        await signIn(email.trim(), password)
        setSuccessMsg('Successfully signed in!')
        setTimeout(() => {
          onClose()
        }, 800)
      } catch (err) {
        setError(err.message || 'Invalid email or password.')
      } finally {
        setLoading(false)
      }
    }
  }

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: 'rgba(5, 7, 12, 0.85)',
        backdropFilter: 'blur(8px)',
        padding: '16px',
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '440px',
          backgroundColor: '#11131a',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          borderRadius: '16px',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.75), 0 0 30px rgba(229, 0, 0, 0.15)',
          overflow: 'hidden',
          animation: 'fadeIn 0.2s ease-out',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header with Title and Close Button */}
        <div
          style={{
            padding: '24px 28px 16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          }}
        >
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span
                style={{
                  fontSize: '18px',
                  fontWeight: '800',
                  letterSpacing: '1px',
                  color: '#ffffff',
                }}
              >
                CINE<span style={{ color: '#E50000' }}>FORGE</span>
              </span>
              <span
                style={{
                  fontSize: '11px',
                  backgroundColor: 'rgba(229, 0, 0, 0.15)',
                  color: '#ff4d4d',
                  padding: '2px 6px',
                  borderRadius: '4px',
                  fontWeight: '600',
                }}
              >
                AUTH
              </span>
            </div>
            <p style={{ margin: '4px 0 0', fontSize: '13px', color: '#8e95a5' }}>
              {activeTab === 'signin' ? 'Sign in to access your watch history' : 'Create an account for personalized streaming'}
            </p>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#8e95a5',
              cursor: 'pointer',
              padding: '6px',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'color 0.2s',
            }}
            aria-label="Close"
          >
            <X size={20} />
          </button>
        </div>

        {/* Tabs: Sign In / Create Account */}
        <div
          style={{
            display: 'flex',
            padding: '4px',
            margin: '20px 28px 0',
            backgroundColor: 'rgba(255, 255, 255, 0.04)',
            borderRadius: '10px',
            border: '1px solid rgba(255, 255, 255, 0.06)',
          }}
        >
          <button
            type="button"
            onClick={() => setActiveTab('signin')}
            style={{
              flex: 1,
              padding: '10px',
              border: 'none',
              borderRadius: '8px',
              fontSize: '13px',
              fontWeight: '600',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              backgroundColor: activeTab === 'signin' ? '#E50000' : 'transparent',
              color: activeTab === 'signin' ? '#ffffff' : '#8e95a5',
            }}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('signup')}
            style={{
              flex: 1,
              padding: '10px',
              border: 'none',
              borderRadius: '8px',
              fontSize: '13px',
              fontWeight: '600',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              backgroundColor: activeTab === 'signup' ? '#E50000' : 'transparent',
              color: activeTab === 'signup' ? '#ffffff' : '#8e95a5',
            }}
          >
            Create Account
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} style={{ padding: '24px 28px' }}>
          {error && (
            <div
              style={{
                marginBottom: '16px',
                padding: '12px 14px',
                backgroundColor: 'rgba(229, 0, 0, 0.12)',
                border: '1px solid rgba(229, 0, 0, 0.3)',
                borderRadius: '8px',
                display: 'flex',
                alignItems: 'flex-start',
                gap: '10px',
                color: '#ff6666',
                fontSize: '13px',
                lineHeight: '1.4',
              }}
            >
              <AlertCircle size={16} style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>{error}</div>
            </div>
          )}

          {successMsg && (
            <div
              style={{
                marginBottom: '16px',
                padding: '12px 14px',
                backgroundColor: 'rgba(16, 185, 129, 0.12)',
                border: '1px solid rgba(16, 185, 129, 0.3)',
                borderRadius: '8px',
                display: 'flex',
                alignItems: 'flex-start',
                gap: '10px',
                color: '#34d399',
                fontSize: '13px',
                lineHeight: '1.4',
              }}
            >
              <CheckCircle2 size={16} style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>{successMsg}</div>
            </div>
          )}

          {/* Full Name (Sign Up only) */}
          {activeTab === 'signup' && (
            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: '500', color: '#c5c9d3', marginBottom: '6px' }}>
                Full Name
              </label>
              <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                <User size={16} style={{ position: 'absolute', left: '12px', color: '#6b7280' }} />
                <input
                  type="text"
                  required
                  placeholder="e.g. Alex Miller"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '10px 12px 10px 38px',
                    backgroundColor: 'rgba(255, 255, 255, 0.05)',
                    border: '1px solid rgba(255, 255, 255, 0.12)',
                    borderRadius: '8px',
                    color: '#ffffff',
                    fontSize: '14px',
                    outline: 'none',
                    transition: 'border-color 0.2s',
                  }}
                />
              </div>
            </div>
          )}

          {/* Email */}
          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: '500', color: '#c5c9d3', marginBottom: '6px' }}>
              Email Address
            </label>
            <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
              <Mail size={16} style={{ position: 'absolute', left: '12px', color: '#6b7280' }} />
              <input
                type="email"
                required
                placeholder="name@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                style={{
                  width: '100%',
                  padding: '10px 12px 10px 38px',
                  backgroundColor: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                  borderRadius: '8px',
                  color: '#ffffff',
                  fontSize: '14px',
                  outline: 'none',
                }}
              />
            </div>
          </div>

          {/* Password */}
          <div style={{ marginBottom: activeTab === 'signup' ? '16px' : '24px' }}>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: '500', color: '#c5c9d3', marginBottom: '6px' }}>
              Password
            </label>
            <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
              <Lock size={16} style={{ position: 'absolute', left: '12px', color: '#6b7280' }} />
              <input
                type="password"
                required
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={{
                  width: '100%',
                  padding: '10px 12px 10px 38px',
                  backgroundColor: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                  borderRadius: '8px',
                  color: '#ffffff',
                  fontSize: '14px',
                  outline: 'none',
                }}
              />
            </div>
          </div>

          {/* Confirm Password (Sign Up only) */}
          {activeTab === 'signup' && (
            <div style={{ marginBottom: '24px' }}>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: '500', color: '#c5c9d3', marginBottom: '6px' }}>
                Confirm Password
              </label>
              <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                <Lock size={16} style={{ position: 'absolute', left: '12px', color: '#6b7280' }} />
                <input
                  type="password"
                  required
                  placeholder="••••••••"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '10px 12px 10px 38px',
                    backgroundColor: 'rgba(255, 255, 255, 0.05)',
                    border: '1px solid rgba(255, 255, 255, 0.12)',
                    borderRadius: '8px',
                    color: '#ffffff',
                    fontSize: '14px',
                    outline: 'none',
                  }}
                />
              </div>
            </div>
          )}

          {/* Submit Button */}
          <button
            type="submit"
            disabled={loading}
            style={{
              width: '100%',
              padding: '12px',
              backgroundColor: '#E50000',
              color: '#ffffff',
              border: 'none',
              borderRadius: '8px',
              fontSize: '14px',
              fontWeight: '600',
              cursor: loading ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              boxShadow: '0 4px 12px rgba(229, 0, 0, 0.35)',
              transition: 'background-color 0.2s, opacity 0.2s',
              opacity: loading ? 0.75 : 1,
            }}
          >
            {loading ? (
              <>
                <Loader2 size={18} className="animate-spin" />
                <span>{activeTab === 'signin' ? 'Signing In...' : 'Creating Account...'}</span>
              </>
            ) : (
              <span>{activeTab === 'signin' ? 'Sign In' : 'Create Free Account'}</span>
            )}
          </button>

          {/* Bottom Switcher */}
          <div style={{ marginTop: '18px', textAlign: 'center', fontSize: '13px', color: '#8e95a5' }}>
            {activeTab === 'signin' ? (
              <span>
                Don't have an account?{' '}
                <button
                  type="button"
                  onClick={() => setActiveTab('signup')}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: '#E50000',
                    fontWeight: '600',
                    cursor: 'pointer',
                    textDecoration: 'underline',
                  }}
                >
                  Create one now
                </button>
              </span>
            ) : (
              <span>
                Already have an account?{' '}
                <button
                  type="button"
                  onClick={() => setActiveTab('signin')}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: '#E50000',
                    fontWeight: '600',
                    cursor: 'pointer',
                    textDecoration: 'underline',
                  }}
                >
                  Sign in here
                </button>
              </span>
            )}
          </div>
        </form>
      </div>
    </div>
  )
}
