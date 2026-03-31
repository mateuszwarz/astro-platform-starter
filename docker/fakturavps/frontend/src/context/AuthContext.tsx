import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { User } from '../types'
import { login as apiLogin, getMe, logout as apiLogout } from '../api/auth'
import { tokenStore } from '../api/client'

interface AuthContextType {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // Przy starcie spróbuj odtworzyć sesję z refresh tokenu (z sessionStorage)
  useEffect(() => {
    const refreshToken = tokenStore.getRefreshToken()
    if (refreshToken) {
      // Odśwież access token bez ujawniania go w localStorage
      import('axios').then(({ default: axios }) =>
        axios.post('/api/v1/auth/refresh', { refresh_token: refreshToken }, { timeout: 10000 })
      ).then((res) => {
        tokenStore.setAccessToken(res.data.access_token)
        return getMe()
      }).then(setUser).catch(() => {
        tokenStore.clear()
      }).finally(() => setIsLoading(false))
    } else {
      setIsLoading(false)
    }
  }, [])

  const login = async (email: string, password: string) => {
    const data = await apiLogin(email, password)
    // Przechowuj access token tylko w pamięci, refresh token w sessionStorage
    tokenStore.setAccessToken(data.access_token)
    tokenStore.setRefreshToken(data.refresh_token)
    const userData = await getMe()
    setUser(userData)
  }

  const logout = () => {
    apiLogout().catch(() => {})
    tokenStore.clear()
    setUser(null)
    window.location.href = '/login'
  }

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: !!user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within AuthProvider')
  return context
}
