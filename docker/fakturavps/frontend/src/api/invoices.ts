import apiClient from './client'

export interface InvoiceFilters {
  status?: string
  type?: string
  contractor_id?: string
  date_from?: string
  date_to?: string
  source?: string
  search?: string
  skip?: number
  limit?: number
}

export const getInvoices = async (filters: InvoiceFilters = {}) => {
  const params = Object.fromEntries(Object.entries(filters).filter(([_, v]) => v !== undefined && v !== ''))
  const response = await apiClient.get('/invoices', { params })
  return response.data
}

export const getInvoice = async (id: string) => {
  const response = await apiClient.get(`/invoices/${id}`)
  return response.data
}

export const createInvoice = async (data: unknown) => {
  const response = await apiClient.post('/invoices', data)
  return response.data
}

export const updateInvoice = async (id: string, data: unknown) => {
  const response = await apiClient.put(`/invoices/${id}`, data)
  return response.data
}

export const deleteInvoice = async (id: string) => {
  const response = await apiClient.delete(`/invoices/${id}`)
  return response.data
}

export const sendToKsef = async (id: string) => {
  const response = await apiClient.post(`/invoices/${id}/send-ksef`)
  return response.data
}

export const addPayment = async (id: string, data: unknown) => {
  const response = await apiClient.post(`/invoices/${id}/payments`, data)
  return response.data
}

export const getInvoiceStats = async () => {
  const response = await apiClient.get('/invoices/stats')
  return response.data
}

export const updateInvoiceStatus = async (id: string, status: string, reason?: string) => {
  const response = await apiClient.patch(`/invoices/${id}/status`, { status, reason })
  return response.data
}

export const getInvoicePdfUrl = (id: string, includeCostType = true) =>
  `/api/v1/invoices/${id}/pdf?include_cost_type=${includeCostType}`

export const getInvoiceAttachmentUrl = (id: string) => `/api/v1/invoices/${id}/attachment`

export const uploadOcr = async (file: File) => {
  const form = new FormData()
  form.append('file', file)
  const response = await apiClient.post('/invoices/ocr-upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return response.data
}

export const updateInvoiceCostType = async (id: string, costType: string) => {
  const response = await apiClient.put(`/invoices/${id}`, { cost_type: costType })
  return response.data
}

export const getSalesSummary = async () => {
  const response = await apiClient.get('/invoices/summary')
  return response.data
}

export const quickPayInvoice = async (id: string, paid: boolean, paymentDate?: string) => {
  const response = await apiClient.patch(`/invoices/${id}/quick-pay`, { paid, payment_date: paymentDate })
  return response.data
}

export const setAccountingApproved = async (id: string, approved: boolean) => {
  const response = await apiClient.patch(`/invoices/${id}/accounting-approve`, { approved })
  return response.data
}
