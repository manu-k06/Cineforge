import React, { useEffect } from 'react'
import { X, Check } from 'lucide-react'
import { SUPERHERO_AVATARS } from '../utils/avatars'

export default function AvatarPickerModal({ isOpen, onClose, currentAvatarId, onSelectAvatar }) {
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

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 10000,
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
          maxWidth: '560px',
          maxHeight: '90vh',
          backgroundColor: '#11131a',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          borderRadius: '18px',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.8), 0 0 35px rgba(229, 0, 0, 0.2)',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          animation: 'fadeIn 0.2s ease-out',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            padding: '20px 24px 16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          }}
        >
          <div>
            <h3
              style={{
                margin: 0,
                fontSize: '18px',
                fontWeight: '800',
                color: '#ffffff',
                letterSpacing: '-0.3px',
              }}
            >
              Choose Your Superhero Avatar
            </h3>
            <p style={{ margin: '4px 0 0', fontSize: '13px', color: '#8e95a5' }}>
              Select an emblem to personalize your Cineforge cinema persona
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

        {/* Avatar Grid */}
        <div
          style={{
            padding: '20px 24px',
            overflowY: 'auto',
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(76px, 1fr))',
            gap: '14px',
            maxHeight: '60vh',
          }}
        >
          {SUPERHERO_AVATARS.map((avatar) => {
            const isSelected = (currentAvatarId || 'spider_man') === avatar.id
            return (
              <button
                key={avatar.id}
                type="button"
                onClick={() => {
                  onSelectAvatar(avatar.id)
                  onClose()
                }}
                style={{
                  position: 'relative',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  background: isSelected ? 'rgba(255, 255, 255, 0.08)' : 'rgba(255, 255, 255, 0.02)',
                  border: isSelected
                    ? `2px solid ${avatar.color || '#E50000'}`
                    : '1px solid rgba(255, 255, 255, 0.08)',
                  borderRadius: '12px',
                  padding: '10px 6px 8px',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  boxShadow: isSelected ? `0 0 16px ${avatar.color}40` : 'none',
                }}
                title={avatar.name}
              >
                {/* Avatar Icon */}
                <div
                  style={{
                    width: '54px',
                    height: '54px',
                    borderRadius: '50%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    overflow: 'hidden',
                    backgroundColor: 'rgba(0, 0, 0, 0.2)',
                  }}
                >
                  <img
                    src={avatar.src}
                    alt={avatar.name}
                    style={{
                      width: '100%',
                      height: '100%',
                      objectFit: 'contain',
                      transition: 'transform 0.2s ease',
                    }}
                  />
                </div>

                {/* Name Label */}
                <span
                  style={{
                    marginTop: '6px',
                    fontSize: '11px',
                    fontWeight: isSelected ? '700' : '500',
                    color: isSelected ? '#ffffff' : '#9ca3af',
                    textAlign: 'center',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    width: '100%',
                    maxWidth: '70px',
                  }}
                >
                  {avatar.name}
                </span>

                {/* Selected Check Badge */}
                {isSelected && (
                  <div
                    style={{
                      position: 'absolute',
                      top: '4px',
                      right: '4px',
                      width: '18px',
                      height: '18px',
                      borderRadius: '50%',
                      backgroundColor: avatar.color || '#E50000',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: '#ffffff',
                      boxShadow: '0 2px 6px rgba(0,0,0,0.5)',
                    }}
                  >
                    <Check size={11} strokeWidth={3} />
                  </div>
                )}
              </button>
            )
          })}
        </div>

        {/* Footer */}
        <div
          style={{
            padding: '14px 24px',
            borderTop: '1px solid rgba(255, 255, 255, 0.08)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            backgroundColor: 'rgba(0, 0, 0, 0.2)',
          }}
        >
          <span style={{ fontSize: '12px', color: '#8e95a5' }}>
            24 Superhero Emblems Available
          </span>
          <button
            type="button"
            onClick={onClose}
            style={{
              padding: '8px 18px',
              backgroundColor: 'rgba(255, 255, 255, 0.08)',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              borderRadius: '8px',
              color: '#ffffff',
              fontSize: '13px',
              fontWeight: '600',
              cursor: 'pointer',
              transition: 'background-color 0.2s',
            }}
          >
            Done
          </button>
        </div>
      </div>
    </div>
  )
}
