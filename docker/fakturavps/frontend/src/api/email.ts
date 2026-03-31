import apiClient from './client'

export interface EmailSource {
  id: string
  name: string
  host: string
  port: number
  username: string
  use_ssl: boolean
  folder: string
  filter_senders: string[] | null
  processed_label: string | null
  is_active: boolean
  last_checked_at: string | null
  last_error: string | null
  created_at: string
}

export interface EmailSourceCreate {
  name: string
  host: string
  port: number
  username: string
  password: string
  use_ssl: boolean
  folder: string
  filter_senders: string[] | null
  processed_label: string | null
  is_active: boolean
}

export interface EmailMessage {
  id: string
  email_source_id: string
  message_id: string
  sender_email: string | null
  sender_name: string | null
  subject: string | null
  received_at: string | null
  attachment_count: number
  processed_at: string | null
  status: 'pending' | 'processed' | 'error' | 'duplicate' | 'skipped'
  error_message: string | null
  invoices_created: number
  invoices_duplicated: number
  created_at: string
}

export interface TestConnectionRequest {
  host: string
  port: number
  username: string
  password: string
  use_ssl: boolean
  folder: string
}

export interface TestConnectionResult {
  ok: boolean
  error: string | null
  folders: string[]
  unseen_count: number
}

export const emailApi = {
  listSources: async (): Promise<EmailSource[]> => {
    const r = await apiClient.get<EmailSource[]>('/email-sources')
    return r.data
  },

  getSource: async (id: string): Promise<EmailSource> => {
    const r = await apiClient.get<EmailSource>(`/email-sources/${id}`)
    return r.data
  },

  createSource: async (data: EmailSourceCreate): Promise<EmailSource> => {
    const r = await apiClient.post<EmailSource>('/email-sources', data)
    return r.data
  },

  updateSource: async (id: string, data: Partial<EmailSourceCreate>): Promise<EmailSource> => {
    const r = await apiClient.put<EmailSource>(`/email-sources/${id}`, data)
    return r.data
  },

  deleteSource: (id: string) =>
    apiClient.delete(`/email-sources/${id}`),

  testConnection: async (data: TestConnectionRequest): Promise<TestConnectionResult> => {
    const r = await apiClient.post<TestConnectionResult>('/email-sources/test-connection', data)
    return r.data
  },

  triggerFetch: async (id: string): Promise<{ task_id: string; message: string }> => {
    const r = await apiClient.post<{ task_id: string; message: string }>(`/email-sources/${id}/trigger`)
    return r.data
  },

  getSourceLog: async (id: string, params?: { skip?: number; limit?: number; status?: string }): Promise<EmailMessage[]> => {
    const r = await apiClient.get<EmailMessage[]>(`/email-sources/${id}/log`, { params })
    return r.data
  },

  getAllLog: async (params?: { skip?: number; limit?: number; status?: string }): Promise<EmailMessage[]> => {
    const r = await apiClient.get<EmailMessage[]>('/email-sources/log/all', { params })
    return r.data
  },
}
