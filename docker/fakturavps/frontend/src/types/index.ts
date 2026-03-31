export type UserRole = 'admin' | 'wlasciciel' | 'ksiegowy' | 'pracownik' | 'audytor'

export interface User {
  id: string
  email: string
  full_name: string
  role: UserRole
  is_active: boolean
  created_at: string
  last_login: string | null
}

export interface Company {
  id: string
  name: string
  nip: string
  regon: string | null
  address: string | null
  postal_code: string | null
  city: string | null
  bank_account: string | null
  vat_rate_default: number
  email: string | null
  phone: string | null
  is_active: boolean
}

export interface Contractor {
  id: string
  nip: string | null
  name: string
  regon: string | null
  address: string | null
  postal_code: string | null
  city: string | null
  email: string | null
  phone: string | null
  bank_account: string | null
  default_payment_days: number
  category: 'klient' | 'dostawca' | 'oba'
  status: 'aktywny' | 'nieaktywny' | 'ryzykowny'
  notes: string | null
  created_at: string
}

export type InvoiceType = 'sprzedaz' | 'zakup' | 'korekta' | 'zaliczkowa' | 'proforma' | 'paragon'
export type InvoiceStatus =
  | 'szkic'
  | 'oczekuje'
  | 'czesciowo_zaplacona'
  | 'zaplacona'
  | 'przeterminowana'
  | 'anulowana'
  | 'w_ksef'
  | 'zaakceptowana_ksef'
  | 'odrzucona_ksef'

export interface InvoiceItem {
  id: string
  invoice_id: string
  name: string
  quantity: number
  unit: string | null
  unit_price_net: number
  vat_rate: string
  net_amount: number
  vat_amount: number
  gross_amount: number
  position_order: number
}

export type CostType = 'towar' | 'usluga'

export interface SalesSummary {
  unpaid_total: number
  overdue_total: number
  overdue_count: number
  due_soon_total: number
  due_soon_count: number
  paid_this_month: number
  total_expected: number
}

export interface BankStatement {
  id: string
  filename: string
  bank_name: string | null
  account_number: string | null
  date_from: string | null
  date_to: string | null
  transaction_count: number
  matched_count: number
  uploaded_at: string
}

export interface BankTransaction {
  id: string
  transaction_date: string
  booking_date: string | null
  amount: number
  currency: string
  description: string | null
  counterparty_name: string | null
  counterparty_account: string | null
  reference: string | null
  match_status: 'unmatched' | 'matched' | 'ignored' | 'manual'
  match_confidence: number | null
  match_notes: string | null
  matched_invoice: {
    id: string
    number: string
    type: string
    status: string
    gross_amount: number
    contractor_name: string | null
  } | null
}

export interface MatchSuggestion {
  invoice_id: string
  invoice_number: string
  invoice_gross: number
  invoice_status: string
  invoice_type: string
  contractor_name: string | null
  contractor_nip: string | null
  confidence: number
}

export interface Invoice {
  id: string
  number: string
  type: InvoiceType
  status: InvoiceStatus
  contractor_id: string | null
  company_id: string | null
  issue_date: string
  sale_date: string | null
  due_date: string | null
  net_amount: number
  vat_amount: number
  gross_amount: number
  currency: string
  notes: string | null
  source: string
  ksef_reference_number: string | null
  ksef_number: string | null
  upo_xml: string | null
  cost_type: CostType | null
  attachment_path: string | null
  attachment_filename: string | null
  has_attachment?: boolean
  days_until_due?: number | null
  days_overdue?: number | null
  accounting_approved: boolean
  created_at: string
  updated_at: string
  contractor_name?: string
  contractor_nip?: string
}

export interface Payment {
  id: string
  invoice_id: string
  invoice_number?: string
  amount: number
  payment_date: string
  method: string
  notes: string | null
  created_at: string
}

export interface DashboardData {
  receivables_total: number
  payables_total: number
  overdue_count: number
  overdue_amount: number
  paid_this_month: number
  pending_this_week: Array<{
    id: string
    number: string
    due_date: string | null
    gross_amount: number
    status: string
  }>
  recent_invoices: Array<{
    id: string
    number: string
    type: string
    status: string
    issue_date: string
    gross_amount: number
  }>
  monthly_revenue: Array<{
    month: number
    revenue: number
    costs: number
  }>
  ksef_status: string
}

export interface VATRow {
  number: string
  issue_date: string
  contractor_name: string
  contractor_nip: string
  net_0: number
  net_5: number
  net_8: number
  net_23: number
  vat_5: number
  vat_8: number
  vat_23: number
  gross: number
}

export interface VATReport {
  rows: VATRow[]
  totals: Omit<VATRow, 'number' | 'issue_date' | 'contractor_name' | 'contractor_nip'>
  year: number
  month: number
  type: string
}

export interface AgingRow {
  contractor_id: string
  contractor_name: string
  type: string
  bucket_0_30: number
  bucket_31_60: number
  bucket_61_90: number
  bucket_90_plus: number
  total: number
}

export interface AgingReport {
  rows: AgingRow[]
  date: string
}

export interface MonthlyRow {
  month: number
  month_name: string
  income: number
  costs: number
  profit: number
}

export interface MonthlyReport {
  rows: MonthlyRow[]
  year: number
}

export interface ContractorRankRow {
  contractor_id: string
  contractor_name: string
  contractor_nip: string
  total_net: number
  total_gross: number
  invoice_count: number
}
