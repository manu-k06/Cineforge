import React, { createContext, useContext, useEffect, useState } from 'react'
import { isSupabaseConfigured, supabase } from '../services/supabase'

const AuthContext = createContext({
  user: null,
  profile: null,
  session: null,
  loading: true,
  isAuthModalOpen: false,
  openAuthModal: () => {},
  closeAuthModal: () => {},
  signIn: async () => {},
  signUp: async () => {},
  signOut: async () => {},
  updateProfile: async () => {},
})

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [profile, setProfile] = useState(null)
  const [session, setSession] = useState(null)
  const [loading, setLoading] = useState(true)
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false)

  const openAuthModal = () => setIsAuthModalOpen(true)
  const closeAuthModal = () => setIsAuthModalOpen(false)

  const fetchProfile = async (userId) => {
    if (!isSupabaseConfigured || !supabase || !userId) return null
    try {
      const { data, error } = await supabase
        .from('profiles')
        .select('*')
        .eq('id', userId)
        .maybeSingle()

      if (!error && data) {
        setProfile(data)
        if (data.avatar_id) {
          try {
            localStorage.setItem('cineforge_user_avatar', data.avatar_id)
          } catch {}
        }
        return data
      }
    } catch (e) {
      console.warn('[Cineforge Auth] Failed to fetch profile from Supabase:', e)
    }
    return null
  }

  useEffect(() => {
    if (!isSupabaseConfigured || !supabase) {
      setLoading(false)
      return
    }

    // 1. Check active session on mount
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session)
      const currentUser = session?.user ?? null
      setUser(currentUser)
      if (currentUser?.id) {
        fetchProfile(currentUser.id)
      }
      setLoading(false)
    })

    // 2. Listen for auth state changes (sign in, sign out, token refresh)
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session)
      const currentUser = session?.user ?? null
      setUser(currentUser)
      if (currentUser?.id) {
        fetchProfile(currentUser.id)
      } else {
        setProfile(null)
      }
      setLoading(false)
    })

    return () => {
      subscription.unsubscribe()
    }
  }, [])

  const signIn = async (email, password) => {
    if (!isSupabaseConfigured || !supabase) {
      throw new Error('Supabase is not configured. Please add VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY to your frontend environment.')
    }
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    })
    if (error) throw error
    if (data?.user?.id) {
      fetchProfile(data.user.id)
    }
    return data
  }

  const signUp = async (email, password, fullName) => {
    if (!isSupabaseConfigured || !supabase) {
      throw new Error('Supabase is not configured. Please add VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY to your frontend environment.')
    }
    const redirectUrl = typeof window !== 'undefined' ? window.location.origin : undefined
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        emailRedirectTo: redirectUrl,
        data: {
          full_name: fullName,
          avatar_id: localStorage.getItem('cineforge_user_avatar') || 'director',
        },
      },
    })
    if (error) throw error
    if (data?.user?.id) {
      fetchProfile(data.user.id)
    }
    return data
  }

  const updateProfile = async ({ fullName, avatarId, preferences }) => {
    // 1. Optimistic update
    setProfile((prev) => ({
      ...(prev || {}),
      ...(fullName ? { full_name: fullName } : {}),
      ...(avatarId ? { avatar_id: avatarId } : {}),
      ...(preferences ? { preferences: { ...(prev?.preferences || {}), ...preferences } } : {}),
    }))

    if (avatarId) {
      try {
        localStorage.setItem('cineforge_user_avatar', avatarId)
      } catch {}
    }

    if (!isSupabaseConfigured || !supabase || !user) return

    // 2. Persist to Supabase public.profiles table
    try {
      const payload = {
        id: user.id,
        updated_at: new Date().toISOString(),
        ...(fullName ? { full_name: fullName } : {}),
        ...(avatarId ? { avatar_id: avatarId } : {}),
        ...(preferences ? { preferences } : {}),
      }

      const { data, error } = await supabase
        .from('profiles')
        .upsert(payload)
        .select()
        .single()

      if (!error && data) {
        setProfile(data)
      }
    } catch (e) {
      console.warn('[Cineforge Auth] Failed to persist profile to Supabase:', e)
    }
  }

  const signOut = async () => {
    if (!isSupabaseConfigured || !supabase) {
      setUser(null)
      setProfile(null)
      setSession(null)
      return
    }
    const { error } = await supabase.auth.signOut()
    if (error) console.error('Sign out error:', error)
    setUser(null)
    setProfile(null)
    setSession(null)
  }

  const value = {
    user,
    profile,
    session,
    loading,
    isAuthModalOpen,
    openAuthModal,
    closeAuthModal,
    signIn,
    signUp,
    signOut,
    updateProfile,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
