import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getInvoices, updateInvoiceStatus, getSalesSummary, quickPayInvoice } from '../../api/invoices'
import { StatusBadge } from '../../components/StatusBadge'
import { InvoiceTypeLabel } from '../../components/InvoiceTypeLabel'
import { formatCurrency, formatDate } from '../../utils/format'
import { useAuth } from '../../context/AuthContext'
import { Plus, Search, Download, ChevronLeft, ChevronRight, CheckCircle2, Clock, AlertTriangle, TrendingUp, ShieldCheck, ShieldX } from 'lucide-react'

const STATUSES = ['szkic','oczekuje','czesciowo_zaplacona','zaplacona','przeterminowana','anulowana','w_ksef','zaakceptowana_ksef','odrzucona_ksef']
const TYPES = ['sprzedaz','zakup','korekta','zaliczkowa','proforma','paragon']
const STATUS_LABELS: Record<string, string> = {
  szkic: 'Szkic', oczekuje: 'Oczekuje', czesciowo_zaplacona: 'Częściowo zapłacona',
  zaplacona: 'Zapłacona', przeterminowana: 'Przeterminowana', anulowana: 'Anulowana',
  w_ksef: 'W KSeF', zaakceptowana_ksef: 'Zaakceptowana (KSeF)', odrzucona_ksef: 'Odrzucona (KSeF)',
}
const TYPE_LABELS: Record<string, string> = {
  sprzedaz: 'Sprzedaż', zakup: 'Zakup', korekta: 'Korekta',
  zaliczkowa: 'Zaliczkowa', proforma: 'Pro Forma', paragon: 'Paragon',
}
const COST_TYPE_LABELS: Record<string, string> = { towar: 'Towar', usluga: 'Usługa' }
const COST_TYPE_COLORS: Record<string, string> = {
  towar: 'bg-amber-100 text-amber-700',
  usluga: 'bg-indigo-100 text-indigo-700',
}

// Dozwolone przejścia statusów (musi być zgodne z backendem)
const STATUS_TRANSITIONS: Record<string, string[]> = {
  szkic:               ['oczekuje', 'anulowana'],
  oczekuje:            ['czesciowo_zaplacona', 'zaplacona', 'przeterminowana', 'anulowana', 'szkic'],
  czesciowo_zaplacona: ['zaplacona', 'przeterminowana', 'anulowana'],
  przeterminowana:     ['oczekuje', 'czesciowo_zaplacona', 'zaplacona', 'anulowana'],
  zaplacona:           ['anulowana'],
  anulowana:           [],
  w_ksef:              ['zaakceptowana_ksef', 'odrzucona_ksef'],
  zaakceptowana_ksef:  [],
  odrzucona_ksef:      ['oczekuje'],
}

const PAGE_SIZE = 50

export default function InvoiceList() {
  const { user } = useAuth()
  const isKsiegowy = user?.role === 'ksiegowy'
  const [searchParams, setSearchParams] = useSearchParams()
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState(searchParams.get('status') || '')
  const [type, setType] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [page, setPage] = useState(0)
  const [changingId, setChangingId] = useState<string | null>(null)

  const qc = useQueryClient()

  const { data: summaryData } = useQuery({
    queryKey: ['invoices-summary'],
    queryFn: getSalesSummary,
    staleTime: 30000,
  })

  const { data, isLoading } = useQuery({
    queryKey: ['invoices', search, status, type, dateFrom, dateTo, page],
    queryFn: () => getInvoices({
      search: search || undefined,
      status: status || undefined,
      type: type || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
      skip: page * PAGE_SIZE,
      limit: PAGE_SIZE,
    }),
  })

  const total = data?.total || 0
  const items = data?.items || []
  const totalPages = Math.ceil(total / PAGE_SIZE)

  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      updateInvoiceStatus(id, status),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['invoices'] })
      qc.invalidateQueries({ queryKey: ['invoices-summary'] })
      setChangingId(null)
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      alert(msg || 'Błąd zmiany statusu')
      setChangingId(null)
    },
  })

  const quickPayMut = useMutation({
    mutationFn: ({ id, paid }: { id: string; paid: boolean }) => quickPayInvoice(id, paid),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['invoices'] })
      qc.invalidateQueries({ queryKey: ['invoices-summary'] })
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      alert(msg || 'Błąd zmiany statusu płatności')
    },
  })

  const exportCSV = () => {
    const headers = ['Numer', 'Data wystawienia', 'Termin płatności', 'Kontrahent', 'NIP', 'Netto', 'VAT', 'Brutto', 'Status', 'Typ']
    const rows = items.map((inv: Record<string, unknown>) => [
      inv.number, inv.issue_date, inv.due_date, inv.contractor_name, inv.contractor_nip,
      inv.net_amount, inv.vat_amount, inv.gross_amount, inv.status, inv.type
    ])
    const csv = [headers, ...rows].map(r => r.join(';')).join('\n')
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a'); a.href = url; a.download = 'faktury.csv'; a.click()
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Faktury</h1>
        <div className="flex items-center gap-3">
          <button onClick={exportCSV} className="btn-secondary">
            <Download size={16} />
            Eksport CSV
          </button>
          {!isKsiegowy && (
            <Link to="/faktury/nowa" className="btn-primary">
              <Plus size={16} />
              Nowa faktura
            </Link>
          )}
        </div>
      </div>

      {/* Sales summary cards – shown when viewing sales invoices */}
      {(type === '' || type === 'sprzedaz') && summaryData && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="card flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-100 flex items-center justify-center shrink-0">
              <TrendingUp size={18} className="text-blue-600" />
            </div>
            <div>
              <p className="text-xs text-gray-400">Do wpłynięcia łącznie</p>
              <p className="font-bold text-gray-900">{formatCurrency(summaryData.total_expected)}</p>
            </div>
          </div>
          <div className="card flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-yellow-100 flex items-center justify-center shrink-0">
              <Clock size={18} className="text-yellow-600" />
            </div>
            <div>
              <p className="text-xs text-gray-400">Nieopłacone (oczekują)</p>
              <p className="font-bold text-gray-900">{formatCurrency(summaryData.unpaid_total)}</p>
            </div>
          </div>
          <div className="card flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-red-100 flex items-center justify-center shrink-0">
              <AlertTriangle size={18} className="text-red-500" />
            </div>
            <div>
              <p className="text-xs text-gray-400">Przeterminowane ({summaryData.overdue_count})</p>
              <p className="font-bold text-red-600">{formatCurrency(summaryData.overdue_total)}</p>
            </div>
          </div>
          <div className="card flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-green-100 flex items-center justify-center shrink-0">
              <CheckCircle2 size={18} className="text-green-600" />
            </div>
            <div>
              <p className="text-xs text-gray-400">Zapłacone w tym miesiącu</p>
              <p className="font-bold text-green-700">{formatCurrency(summaryData.paid_this_month)}</p>
            </div>
          </div>
        </div>
      )}

      {/* Quick filter tabs: Sprzedażowe / Kosztowe */}
      <div className="flex gap-2">
        {[
          { label: 'Wszystkie', value: '' },
          { label: 'Sprzedażowe', value: 'sprzedaz' },
          { label: 'Kosztowe (zakup)', value: 'zakup' },
        ].map(tab => (
          <button
            key={tab.value}
            onClick={() => { setType(tab.value); setPage(0) }}
            className={`px-4 py-1.5 rounded-full text-sm font-medium border transition-colors ${
              type === tab.value
                ? 'bg-blue-600 text-white border-blue-600'
                : 'bg-white text-gray-600 border-gray-300 hover:border-blue-400'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="card">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          <div className="relative">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Szukaj numer, NIP, nazwa..."
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(0) }}
              className="input-field pl-9"
            />
          </div>
          <select
            value={status}
            onChange={(e) => { setStatus(e.target.value); setPage(0) }}
            className="input-field"
          >
            <option value="">Wszystkie statusy</option>
            {STATUSES.map(s => <option key={s} value={s}>{STATUS_LABELS[s]}</option>)}
          </select>
          <select
            value={type}
            onChange={(e) => { setType(e.target.value); setPage(0) }}
            className="input-field"
          >
            <option value="">Wszystkie typy</option>
            {TYPES.map(t => <option key={t} value={t}>{TYPE_LABELS[t]}</option>)}
          </select>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => { setDateFrom(e.target.value); setPage(0) }}
            className="input-field"
            placeholder="Data od"
          />
          <input
            type="date"
            value={dateTo}
            onChange={(e) => { setDateTo(e.target.value); setPage(0) }}
            className="input-field"
            placeholder="Data do"
          />
        </div>
      </div>

      <div className="card p-0 overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center h-48">
            <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="table-header">Numer</th>
                    <th className="table-header">Kontrahent</th>
                    <th className="table-header">Data wystawienia</th>
                    <th className="table-header">Termin / dni</th>
                    <th className="table-header text-right">Netto</th>
                    <th className="table-header text-right">VAT</th>
                    <th className="table-header text-right">Brutto</th>
                    <th className="table-header">Typ</th>
                    <th className="table-header">Rodzaj kosztu</th>
                    <th className="table-header">Księgowanie</th>
                    <th className="table-header">Status</th>
                    {!isKsiegowy && <th className="table-header">Opłacona</th>}
                  </tr>
                </thead>
                <tbody>
                  {items.length === 0 ? (
                    <tr>
                      <td colSpan={isKsiegowy ? 11 : 12} className="text-center py-12 text-gray-400">
                        Brak faktur spełniających kryteria filtrowania
                      </td>
                    </tr>
                  ) : (
                    items.map((inv: Record<string, unknown>) => (
                      <tr key={inv.id as string} className="border-b border-gray-50 hover:bg-blue-50/30 transition-colors cursor-pointer">
                        <td className="table-cell">
                          <Link to={`/faktury/${inv.id}`} className="text-blue-600 hover:underline font-semibold">
                            {inv.number as string}
                          </Link>
                        </td>
                        <td className="table-cell">
                          <p className="font-medium text-gray-900">{(inv.contractor_name as string) || '-'}</p>
                          <p className="text-xs text-gray-400">{(inv.contractor_nip as string) || ''}</p>
                        </td>
                        <td className="table-cell text-gray-500">{formatDate(inv.issue_date as string)}</td>
                        <td className="table-cell">
                          <p className="text-sm text-gray-500">{formatDate(inv.due_date as string)}</p>
                          {inv.days_overdue != null && (inv.days_overdue as number) > 0 ? (
                            <p className="text-xs font-semibold text-red-600">
                              {inv.days_overdue as number} dni po terminie
                            </p>
                          ) : inv.days_until_due != null ? (
                            (inv.days_until_due as number) === 0 ? (
                              <p className="text-xs font-semibold text-orange-500">Dziś!</p>
                            ) : (inv.days_until_due as number) <= 7 ? (
                              <p className="text-xs font-semibold text-orange-400">
                                {inv.days_until_due as number} dni
                              </p>
                            ) : (
                              <p className="text-xs text-gray-400">
                                {inv.days_until_due as number} dni
                              </p>
                            )
                          ) : null}
                        </td>
                        <td className="table-cell text-right">{formatCurrency(inv.net_amount as number)}</td>
                        <td className="table-cell text-right">{formatCurrency(inv.vat_amount as number)}</td>
                        <td className="table-cell text-right font-semibold">{formatCurrency(inv.gross_amount as number)}</td>
                        <td className="table-cell text-gray-500"><InvoiceTypeLabel type={inv.type as string} /></td>
                        <td className="table-cell">
                          {(inv.type as string) === 'zakup' && inv.cost_type ? (
                            <span className={`inline-block text-xs font-medium px-2 py-0.5 rounded-full ${COST_TYPE_COLORS[inv.cost_type as string] || 'bg-gray-100 text-gray-500'}`}>
                              {COST_TYPE_LABELS[inv.cost_type as string] || inv.cost_type as string}
                            </span>
                          ) : (
                            <span className="text-gray-300 text-xs">—</span>
                          )}
                        </td>
                        {/* Accounting approved badge */}
                        <td className="table-cell" onClick={(e) => e.stopPropagation()}>
                          {(inv.accounting_approved as boolean) ? (
                            <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700">
                              <ShieldCheck size={11} /> Zatwierdzona
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">
                              <ShieldX size={11} /> Brak
                            </span>
                          )}
                        </td>
                        <td className="table-cell" onClick={(e) => e.stopPropagation()}>
                          {!isKsiegowy && changingId === (inv.id as string) ? (
                            <select
                              autoFocus
                              defaultValue=""
                              disabled={statusMutation.isPending}
                              className="text-xs border border-blue-400 rounded-lg px-2 py-1 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                              onChange={(e) => {
                                if (e.target.value) {
                                  statusMutation.mutate({ id: inv.id as string, status: e.target.value })
                                } else {
                                  setChangingId(null)
                                }
                              }}
                              onBlur={() => { if (!statusMutation.isPending) setChangingId(null) }}
                            >
                              <option value="">— anuluj —</option>
                              {(STATUS_TRANSITIONS[inv.status as string] ?? []).map((s) => (
                                <option key={s} value={s}>{STATUS_LABELS[s] ?? s}</option>
                              ))}
                            </select>
                          ) : (
                            <button
                              title={
                                isKsiegowy ? undefined
                                : (STATUS_TRANSITIONS[inv.status as string] ?? []).length > 0
                                  ? 'Kliknij aby zmienić status'
                                  : 'Status nie może być zmieniony'
                              }
                              onClick={() => {
                                if (!isKsiegowy && (STATUS_TRANSITIONS[inv.status as string] ?? []).length > 0) {
                                  setChangingId(inv.id as string)
                                }
                              }}
                              className={
                                !isKsiegowy && (STATUS_TRANSITIONS[inv.status as string] ?? []).length > 0
                                  ? 'cursor-pointer hover:opacity-80 transition-opacity'
                                  : 'cursor-default'
                              }
                            >
                              <StatusBadge status={inv.status as string} />
                            </button>
                          )}
                        </td>
                        {/* Quick pay toggle – only for sprzedaz invoices, hidden for ksiegowy */}
                        {!isKsiegowy && (
                          <td className="table-cell" onClick={(e) => e.stopPropagation()}>
                            {(inv.type as string) === 'sprzedaz' ? (() => {
                              const isPaid = (inv.status as string) === 'zaplacona'
                              const canToggle = !['anulowana', 'w_ksef', 'zaakceptowana_ksef'].includes(inv.status as string)
                              return canToggle ? (
                                <button
                                  title={isPaid ? 'Kliknij aby cofnąć opłacenie' : 'Oznacz jako opłacona'}
                                  onClick={() => quickPayMut.mutate({ id: inv.id as string, paid: !isPaid })}
                                  disabled={quickPayMut.isPending}
                                  className={`flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-lg border transition-colors ${
                                    isPaid
                                      ? 'bg-green-50 text-green-700 border-green-200 hover:bg-red-50 hover:text-red-600 hover:border-red-200'
                                      : 'bg-gray-50 text-gray-500 border-gray-200 hover:bg-green-50 hover:text-green-700 hover:border-green-200'
                                  }`}
                                >
                                  <CheckCircle2 size={13} />
                                  {isPaid ? 'Zapłacona' : 'Opłać'}
                                </button>
                              ) : (
                                <span className="text-gray-300 text-xs">—</span>
                              )
                            })() : (
                              <span className="text-gray-300 text-xs">—</span>
                            )}
                          </td>
                        )}
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200">
              <p className="text-sm text-gray-500">
                Wyświetlono {items.length} z {total} faktur
              </p>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage(p => Math.max(0, p - 1))}
                  disabled={page === 0}
                  className="btn-secondary py-1.5 px-2 disabled:opacity-30"
                >
                  <ChevronLeft size={16} />
                </button>
                <span className="text-sm text-gray-700">
                  Strona {page + 1} z {Math.max(1, totalPages)}
                </span>
                <button
                  onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                  disabled={page >= totalPages - 1}
                  className="btn-secondary py-1.5 px-2 disabled:opacity-30"
                >
                  <ChevronRight size={16} />
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
