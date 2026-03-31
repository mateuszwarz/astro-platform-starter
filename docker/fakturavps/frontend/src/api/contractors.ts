import apiClient from './client'

export const getContractors = async (params: Record<string, unknown> = {}) => {
  const cleanParams = Object.fromEntries(Object.entries(params).filter(([_, v]) => v !== undefined && v !== ''))
  const response = await apiClient.get('/contractors', { params: cleanParams })
  return response.data
}

export const getContractor = async (id: string) => {
  const response = await apiClient.get(`/contractors/${id}`)
  return response.data
}

export const createContractor = async (data: unknown) => {
  const response = await apiClient.post('/contractors', data)
  return response.data
}

export const updateContractor = async (id: string, data: unknown) => {
  const response = await apiClient.put(`/contractors/${id}`, data)
  return response.data
}

export const deleteContractor = async (id: string) => {
  const response = await apiClient.delete(`/contractors/${id}`)
  return response.data
}
