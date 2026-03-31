import { useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getInvoice, deleteInvoice, sendToKsef, addPayment, getInvoicePdfUrl, getInvoiceAttachmentUrl, updateInvoiceCostType, setAccountingApproved } from '../../api/invoices'
import { StatusBadge } from '../../components/StatusBadge'
import { InvoiceTypeLabel } from '../../components/InvoiceTypeLabel'
import { formatCurrency, formatDate } from '../../utils/format'
import { useAuth } from '../../context/AuthContext'
import {
  ArrowLeft, Edit, Trash2, Send, FileDown, Plus, CheckCircle, AlertCircle, X, Paperclip, ChevronDown,
  ShieldCheck, ShieldX
} from 'lucide-react'

const COST_TYPE_LABELS: Record<string, string> = { towar: 'Towar', usluga: 'Usługa' }
const COST_TYPE_COLORS: Record<string, string> = {
  towar: 'bg-amber-100 text-amber-700 border-amber-200',
  usluga: 'bg-indigo-100 text-indigo-700 border-indigo-200',
}

interface AddPaymentModalProps {
  invoiceId: string
  onClose: () => void
  onSuccess: () => void
}

const AddPaymentModal = ({ invoiceId, onClose, onSuccess }: AddPaymentModalProps) => {
  const [amount, setAmount] = useState('')
  const [date, setDate] = useState(new Date().toISOString().split('T')[0])
  const [method, setMethod] = useState('przelew')
  const [notes, setNotes] = useState('')
  const [error, setError] = useState('')

  const mutation = useMutation({
    mutationFn: () => addPayment(invoiceId, { invoice_id: invoiceId, amount: parseFloat(amount), payment_date: date, method, notes }),
    onSuccess: () => { onSuccess(); onClose() },
    onError: (e: unknown) => setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Błąd'),
  })

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-md">
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-lg font-semibold">Dodaj płatność</h2>
          <button onClick={onClose}><X size={20} className="text-gray-400 hover:text-gray-600" /></button>
        </div>
        <div className="p-6 space-y-4">
          {error && <div className="p-3 bg-red-50 text-red-700 text-sm rounded-lg">{error}</div>}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Kwota (PLN)</label>
            <input type="number" step="0.01" value={amount} onChange={e => setAmount(e.target.value)} className="input-field" placeholder="0.00" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Data płatności</label>
            <input type="date" value={date} onChange={e => setDate(e.target.value)} className="input-field" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Metoda płatności</label>
            <select value={method} onChange={e => setMethod(e.target.value)} className="input-field">
              <option value="przelew">Przelew bankowy</option>
              <option value="gotowka">Gotówka</option>
              <option value="karta">Karta płatnicza</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Notatki</label>
            <input type="text" value={notes} onChange={e => setNotes(e.target.value)} className="input-field" placeholder="Opcjonalne..." />
          </div>
        </div>
        <div className="flex gap-3 p-6 border-t">
          <button onClick={onClose} className="btn-secondary flex-1">Anuluj</button>
          <button
            onClick={() => mutation.mutate()}
            disabled={!amount || mutation.isPending}
            className="btn-primary flex-1"
          >
            {mutation.isPending ? 'Zapisywanie...' : 'Dodaj płatność'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function InvoiceDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const isKsiegowy = user?.role === 'ksiegowy'
  const isAdmin = user?.role === 'admin' || user?.role === 'wlasciciel'
  const [showPaymentModal, setShowPaymentModal] = useState(false)
  const [actionMsg, setActionMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [showPdfMenu, setShowPdfMenu] = useState(false)
  const [changingCostType, setChangingCostType] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['invoice', id],
    queryFn: () => getInvoice(id!),
    enabled: !!id,
  })

  const deleteMut = useMutation({
    mutationFn: () => deleteInvoice(id!),
    onSuccess: () => navigate('/faktury'),
    onError: (e: unknown) => setActionMsg({ type: 'error', text: (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Błąd usuwania' }),
  })

  const costTypeMut = useMutation({
    mutationFn: (ct: string) => updateInvoiceCostType(id!, ct),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoice', id] })
      setChangingCostType(false)
    },
    onError: () => setChangingCostType(false),
  })

  const accountingMut = useMutation({
    mutationFn: (approved: boolean) => setAccountingApproved(id!, approved),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['invoice', id] }),
    onError: () => setActionMsg({ type: 'error', text: 'Błąd zmiany statusu księgowania' }),
  })

  const kSefMut = useMutation({
    mutationFn: () => sendToKsef(id!),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['invoice', id] })
      setActionMsg({ type: 'success', text: `Wysłano do KSeF. Numer KSeF: ${res.ksef_number}` })
    },
    onError: (e: unknown) => setActionMsg({ type: 'error', text: (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Błąd KSeF' }),
  })

  if (isLoading) {
    return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div></div>
  }

  if (!data) return null

  const { invoice, items, payments, history, contractor, company, total_paid, remaining } = data

  const canEdit = !isKsiegowy && invoice.status === 'szkic'
  const canDelete = !isKsiegowy && invoice.status === 'szkic'
  const canSendKsef = !isKsiegowy && !['anulowana', 'zaakceptowana_ksef'].includes(invoice.status)
  const canDownloadPdf = !isKsiegowy || invoice.accounting_approved

  const downloadPdf = (includeCostType = true) => {
    setShowPdfMenu(false)
    import('../../api/client').then(({ tokenStore }) => {
      const token = tokenStore.getAccessToken()
      fetch(getInvoicePdfUrl(id!, includeCostType), { headers: { Authorization: `Bearer ${token ?? ''}` } })
        .then(r => r.blob())
        .then(blob => {
          const url = URL.createObjectURL(blob)
          const a = document.createElement('a')
          a.href = url
          a.download = `faktura_${invoice.number.replace(/\//g, '_')}.pdf`
          a.click()
          URL.revokeObjectURL(url)
        })
    })
  }

  const downloadAttachment = () => {
    import('../../api/client').then(({ tokenStore }) => {
      const token = tokenStore.getAccessToken()
      fetch(getInvoiceAttachmentUrl(id!), { headers: { Authorization: `Bearer ${token ?? ''}` } })
        .then(r => r.blob())
        .then(blob => {
          const url = URL.createObjectURL(blob)
          const a = document.createElement('a')
          a.href = url
          a.download = invoice.attachment_filename || 'zalacznik'
          a.click()
          URL.revokeObjectURL(url)
        })
    })
  }

  return (
    <div className="space-y-6 max-w-5xl">
      {showPaymentModal && (
        <AddPaymentModal
          invoiceId={id!}
          onClose={() => setShowPaymentModal(false)}
          onSuccess={() => queryClient.invalidateQueries({ queryKey: ['invoice', id] })}
        />
      )}

      <div className="flex items-center gap-4">
        <Link to="/faktury" className="flex items-center gap-1 text-gray-500 hover:text-gray-700 text-sm">
          <ArrowLeft size={16} /> Powrót
        </Link>
      </div>

      {actionMsg && (
        <div className={`flex items-center gap-3 p-4 rounded-xl border ${actionMsg.type === 'success' ? 'bg-green-50 border-green-200 text-green-700' : 'bg-red-50 border-red-200 text-red-700'}`}>
          {actionMsg.type === 'success' ? <CheckCircle size={18} /> : <AlertCircle size={18} />}
          <p className="text-sm">{actionMsg.text}</p>
          <button onClick={() => setActionMsg(null)} className="ml-auto"><X size={16} /></button>
        </div>
      )}

      {/* Accounting status banner */}
      {isKsiegowy && (
        <div className={`flex items-center gap-4 p-5 rounded-xl border-2 ${
          invoice.accounting_approved
            ? 'bg-emerald-50 border-emerald-300'
            : 'bg-red-50 border-red-300'
        }`}>
          {invoice.accounting_approved
            ? <ShieldCheck size={28} className="text-emerald-600 shrink-0" />
            : <ShieldX size={28} className="text-red-500 shrink-0" />
          }
          <div>
            <p className={`text-base font-bold ${invoice.accounting_approved ? 'text-emerald-800' : 'text-red-700'}`}>
              {invoice.accounting_approved
                ? 'Faktura zatwierdzona do księgowania'
                : 'Faktura NIE nadaje się do księgowania'}
            </p>
            {invoice.accounting_approved && invoice.type === 'zakup' && invoice.cost_type && (
              <p className="text-sm text-emerald-700 mt-1">
                Rodzaj: <strong>{invoice.cost_type === 'towar' ? 'Towar' : 'Usługa'}</strong>
              </p>
            )}
            {!invoice.accounting_approved && (
              <p className="text-sm text-red-600 mt-1">Administrator musi zatwierdzić fakturę przed zaksięgowaniem. Pobieranie PDF jest zablokowane.</p>
            )}
          </div>
        </div>
      )}

      <div className="card">
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{invoice.number}</h1>
            <div className="flex items-center gap-3 mt-2">
              <StatusBadge status={invoice.status} />
              <span className="text-sm text-gray-500"><InvoiceTypeLabel type={invoice.type} /></span>
              {invoice.source !== 'manual' && (
                <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full">{invoice.source.toUpperCase()}</span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            {/* Admin: accounting approval toggle */}
            {isAdmin && (
              <button
                onClick={() => accountingMut.mutate(!invoice.accounting_approved)}
                disabled={accountingMut.isPending}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium border transition-colors ${
                  invoice.accounting_approved
                    ? 'bg-emerald-50 border-emerald-300 text-emerald-700 hover:bg-emerald-100'
                    : 'bg-gray-50 border-gray-300 text-gray-600 hover:bg-gray-100'
                }`}
                title={invoice.accounting_approved ? 'Kliknij aby cofnąć zatwierdzenie' : 'Zatwierdź do księgowania'}
              >
                {invoice.accounting_approved ? <ShieldCheck size={16} /> : <ShieldX size={16} />}
                {invoice.accounting_approved ? 'Zatwierdzone do KS' : 'Nie zatwierdzone'}
              </button>
            )}
            {/* PDF download with options */}
            <div className="relative">
              <div className="flex">
                <button
                  onClick={() => canDownloadPdf && downloadPdf(true)}
                  disabled={!canDownloadPdf}
                  className={`btn-secondary rounded-r-none border-r-0 ${!canDownloadPdf ? 'opacity-40 cursor-not-allowed' : ''}`}
                  title={!canDownloadPdf ? 'Faktura nie została zatwierdzona do księgowania' : undefined}
                >
                  <FileDown size={16} /> PDF
                </button>
                {!isKsiegowy && (
                  <button
                    onClick={() => setShowPdfMenu(v => !v)}
                    className="btn-secondary rounded-l-none px-2"
                    title="Opcje PDF"
                  >
                    <ChevronDown size={14} />
                  </button>
                )}
              </div>
              {showPdfMenu && !isKsiegowy && (
                <div className="absolute right-0 mt-1 bg-white border border-gray-200 rounded-xl shadow-lg z-10 min-w-52 py-1">
                  <button onClick={() => downloadPdf(true)} className="w-full text-left px-4 py-2 text-sm hover:bg-gray-50">
                    PDF z informacją Towar/Usługa
                  </button>
                  <button onClick={() => downloadPdf(false)} className="w-full text-left px-4 py-2 text-sm hover:bg-gray-50">
                    PDF bez informacji Towar/Usługa
                  </button>
                </div>
              )}
            </div>
            {/* Attachment download */}
            {invoice.attachment_filename && (!isKsiegowy || invoice.accounting_approved) && (
              <button onClick={downloadAttachment} className="btn-secondary" title={`Pobierz załącznik: ${invoice.attachment_filename}`}>
                <Paperclip size={16} /> Załącznik
              </button>
            )}
            {!isKsiegowy && (
              <button onClick={() => setShowPaymentModal(true)} className="btn-secondary">
                <Plus size={16} /> Płatność
              </button>
            )}
            {canSendKsef && (
              <button onClick={() => kSefMut.mutate()} disabled={kSefMut.isPending} className="btn-secondary">
                <Send size={16} /> {kSefMut.isPending ? 'Wysyłanie...' : 'Wyślij do KSeF'}
              </button>
            )}
            {canEdit && (
              <Link to={`/faktury/${id}/edytuj`} className="btn-primary">
                <Edit size={16} /> Edytuj
              </Link>
            )}
            {canDelete && (
              <button
                onClick={() => window.confirm('Czy na pewno usunąć fakturę?') && deleteMut.mutate()}
                className="btn-danger"
              >
                <Trash2 size={16} /> Usuń
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="font-semibold text-gray-700 mb-3">Sprzedawca</h3>
          {company ? (
            <div className="space-y-1 text-sm">
              <p className="font-bold text-gray-900">{company.name}</p>
              <p className="text-gray-500">NIP: {company.nip}</p>
              <p className="text-gray-500">{company.address}</p>
              <p className="text-gray-500">{company.city}</p>
            </div>
          ) : <p className="text-gray-400 text-sm">Brak danych</p>}
        </div>
        <div className="card">
          <h3 className="font-semibold text-gray-700 mb-3">Nabywca</h3>
          {contractor ? (
            <div className="space-y-1 text-sm">
              <p className="font-bold text-gray-900">{contractor.name}</p>
              <p className="text-gray-500">NIP: {contractor.nip}</p>
              <p className="text-gray-500">{contractor.address}</p>
              <p className="text-gray-500">{`${contractor.postal_code || ''} ${contractor.city || ''}`.trim()}</p>
              {contractor.email && <p className="text-gray-500">{contractor.email}</p>}
            </div>
          ) : <p className="text-gray-400 text-sm">Brak danych nabywcy</p>}
        </div>
      </div>

      <div className="card">
        <h3 className="font-semibold text-gray-700 mb-3">Daty i warunki</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div><p className="text-gray-400">Data wystawienia</p><p className="font-medium">{formatDate(invoice.issue_date)}</p></div>
          <div><p className="text-gray-400">Data sprzedaży</p><p className="font-medium">{formatDate(invoice.sale_date)}</p></div>
          <div><p className="text-gray-400">Termin płatności</p><p className="font-medium">{formatDate(invoice.due_date)}</p></div>
          <div><p className="text-gray-400">Waluta</p><p className="font-medium">{invoice.currency}</p></div>
        </div>
      </div>

      {/* Cost type section – only for zakup invoices */}
      {invoice.type === 'zakup' && (
        <div className="card">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-gray-700">Rodzaj kosztu (faktura kosztowa)</h3>
            {!changingCostType && !isKsiegowy && (
              <button
                onClick={() => setChangingCostType(true)}
                className="text-xs text-blue-600 hover:underline"
              >
                Zmień
              </button>
            )}
          </div>
          <div className="mt-3">
            {changingCostType ? (
              <div className="flex items-center gap-3">
                <select
                  autoFocus
                  defaultValue={invoice.cost_type || ''}
                  className="input-field max-w-xs"
                  disabled={costTypeMut.isPending}
                  onChange={e => {
                    if (e.target.value !== '') costTypeMut.mutate(e.target.value)
                  }}
                >
                  <option value="">— nie określono —</option>
                  <option value="towar">Towar</option>
                  <option value="usluga">Usługa</option>
                </select>
                <button
                  onClick={() => setChangingCostType(false)}
                  className="text-sm text-gray-400 hover:text-gray-600"
                >
                  Anuluj
                </button>
              </div>
            ) : invoice.cost_type ? (
              <span className={`inline-flex items-center text-sm font-semibold px-3 py-1 rounded-full border ${COST_TYPE_COLORS[invoice.cost_type] || 'bg-gray-100 text-gray-600'}`}>
                {COST_TYPE_LABELS[invoice.cost_type] || invoice.cost_type}
              </span>
            ) : (
              <p className="text-gray-400 text-sm">Nie określono — kliknij "Zmień" aby ustawić</p>
            )}
          </div>
        </div>
      )}

      <div className="card p-0 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100">
          <h3 className="font-semibold text-gray-700">Pozycje faktury</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="table-header">Lp.</th>
                <th className="table-header">Nazwa</th>
                <th className="table-header">Jm.</th>
                <th className="table-header text-right">Ilość</th>
                <th className="table-header text-right">Cena netto</th>
                <th className="table-header text-right">Stawka VAT</th>
                <th className="table-header text-right">Netto</th>
                <th className="table-header text-right">VAT</th>
                <th className="table-header text-right">Brutto</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item: Record<string, unknown>, i: number) => (
                <tr key={item.id as string} className="border-b border-gray-50">
                  <td className="table-cell text-gray-400">{i + 1}</td>
                  <td className="table-cell font-medium">{item.name as string}</td>
                  <td className="table-cell text-gray-500">{item.unit as string}</td>
                  <td className="table-cell text-right">{item.quantity as number}</td>
                  <td className="table-cell text-right">{formatCurrency(item.unit_price_net as number)}</td>
                  <td className="table-cell text-right">{item.vat_rate as string}%</td>
                  <td className="table-cell text-right">{formatCurrency(item.net_amount as number)}</td>
                  <td className="table-cell text-right">{formatCurrency(item.vat_amount as number)}</td>
                  <td className="table-cell text-right font-semibold">{formatCurrency(item.gross_amount as number)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot className="bg-blue-50">
              <tr>
                <td colSpan={6} className="table-cell font-bold text-right">RAZEM:</td>
                <td className="table-cell text-right font-bold">{formatCurrency(invoice.net_amount)}</td>
                <td className="table-cell text-right font-bold">{formatCurrency(invoice.vat_amount)}</td>
                <td className="table-cell text-right font-bold text-blue-700">{formatCurrency(invoice.gross_amount)}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      <div className="card">
        <h3 className="font-semibold text-gray-700 mb-4">Płatności</h3>
        <div className="grid grid-cols-3 gap-4 mb-4 p-4 bg-gray-50 rounded-lg text-sm">
          <div><p className="text-gray-400">Do zapłaty</p><p className="font-bold text-lg">{formatCurrency(invoice.gross_amount)}</p></div>
          <div><p className="text-gray-400">Zapłacono</p><p className="font-bold text-lg text-green-600">{formatCurrency(total_paid)}</p></div>
          <div><p className="text-gray-400">Pozostało</p><p className={`font-bold text-lg ${remaining > 0 ? 'text-red-600' : 'text-green-600'}`}>{formatCurrency(remaining)}</p></div>
        </div>
        {payments.length > 0 ? (
          <table className="w-full text-sm">
            <thead><tr className="border-b"><th className="text-left py-2 text-gray-500">Data</th><th className="text-left py-2 text-gray-500">Metoda</th><th className="text-right py-2 text-gray-500">Kwota</th></tr></thead>
            <tbody>
              {payments.map((p: Record<string, unknown>) => (
                <tr key={p.id as string} className="border-b border-gray-50">
                  <td className="py-2">{formatDate(p.payment_date as string)}</td>
                  <td className="py-2 text-gray-500">{p.method as string}</td>
                  <td className="py-2 text-right font-medium">{formatCurrency(p.amount as number)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : <p className="text-gray-400 text-sm">Brak zarejestrowanych płatności</p>}
      </div>

      {(invoice.ksef_number || invoice.ksef_reference_number) && (
        <div className="card bg-green-50 border-green-200">
          <h3 className="font-semibold text-green-700 mb-3">Informacje KSeF</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
            {invoice.ksef_reference_number && <div><p className="text-gray-500">Numer referencyjny</p><p className="font-mono font-medium">{invoice.ksef_reference_number}</p></div>}
            {invoice.ksef_number && <div><p className="text-gray-500">Numer KSeF</p><p className="font-mono font-medium">{invoice.ksef_number}</p></div>}
          </div>
        </div>
      )}

      <div className="card">
        <h3 className="font-semibold text-gray-700 mb-4">Historia statusów</h3>
        <div className="space-y-3">
          {history.map((h: Record<string, unknown>) => (
            <div key={h.id as string} className="flex items-start gap-3 text-sm">
              <div className="w-2 h-2 bg-blue-400 rounded-full mt-2 shrink-0"></div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  {!!h.old_status && <span className="text-gray-400">{String(h.old_status)}</span>}
                  {!!h.old_status && <span className="text-gray-300">→</span>}
                  <span className="font-medium">{String(h.new_status)}</span>
                  <span className="text-gray-400 text-xs ml-auto">{formatDate(h.changed_at as string)}</span>
                </div>
                {!!h.reason && <p className="text-gray-400 text-xs mt-0.5">{String(h.reason)}</p>}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
