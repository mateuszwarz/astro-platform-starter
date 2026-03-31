import apiClient from './client'

export const getPayments = async (params: Record<string, unknown> = {}) => {
  const cleanParams = Object.fromEntries(Object.entries(params).filter(([_, v]) => v !== undefined && v !== ''))
  const response = await apiClient.get('/payments', { params: cleanParams })
  return response.data
}

export const createPayment = async (data: unknown) => {
  const response = await apiClient.post('/payments', data)
  return response.data
}

export const deletePayment = async (id: string) => {
  const response = await apiClient.delete(`/payments/${id}`)
  return response.data
}
