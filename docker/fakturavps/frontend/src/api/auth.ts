import apiClient from './client'
import { User } from '../types'

export const login = async (email: string, password: string) => {
  const response = await apiClient.post('/auth/login', { email, password })
  return response.data
}

export const logout = async () => {
  await apiClient.post('/auth/logout')
}

export const getMe = async (): Promise<User> => {
  const response = await apiClient.get('/auth/me')
  return response.data
}

export const refreshToken = async (refresh_token: string) => {
  const response = await apiClient.post('/auth/refresh', { refresh_token })
  return response.data
}
