import apiClient from './client'

export const getDashboard = async () => {
  const response = await apiClient.get('/dashboard')
  return response.data
}

export const getVatReport = async (year: number, month: number, type: string) => {
  const response = await apiClient.get('/reports/vat', { params: { year, month, type } })
  return response.data
}

export const getIncomeCosts = async (year: number) => {
  const response = await apiClient.get('/reports/income-costs', { params: { year } })
  return response.data
}

export const getAgingReport = async () => {
  const response = await apiClient.get('/reports/aging')
  return response.data
}

export const getTopContractors = async (year: number, limit = 10) => {
  const response = await apiClient.get('/reports/contractors', { params: { year, limit } })
  return response.data
}
