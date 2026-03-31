import apiClient from './client'

export const uploadBankStatement = async (file: File) => {
  const form = new FormData()
  form.append('file', file)
  const res = await apiClient.post('/bank-statements/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

export const getBankStatements = async (params: { skip?: number; limit?: number } = {}) => {
  const res = await apiClient.get('/bank-statements', { params })
  return res.data
}

export const getStatementTransactions = async (
  statementId: string,
  params: { match_status?: string; skip?: number; limit?: number } = {}
) => {
  const res = await apiClient.get(`/bank-statements/${statementId}/transactions`, { params })
  return res.data
}

export const getMatchSuggestions = async (statementId: string, transactionId: string) => {
  const res = await apiClient.get(
    `/bank-statements/${statementId}/transactions/${transactionId}/suggestions`
  )
  return res.data
}

export const matchTransaction = async (
  statementId: string,
  transactionId: string,
  action: 'match' | 'unmatch' | 'ignore',
  invoiceId?: string,
  notes?: string
) => {
  const res = await apiClient.patch(
    `/bank-statements/${statementId}/transactions/${transactionId}/match`,
    { action, invoice_id: invoiceId, notes }
  )
  return res.data
}

export const confirmPayment = async (
  statementId: string,
  transactionId: string
) => {
  const res = await apiClient.post(
    `/bank-statements/${statementId}/transactions/${transactionId}/confirm-payment`,
    {}
  )
  return res.data
}

export const deleteBankStatement = async (statementId: string) => {
  const res = await apiClient.delete(`/bank-statements/${statementId}`)
  return res.data
}
