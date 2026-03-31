import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { ArrowLeft, CheckCircle, XCircle, Copy, AlertCircle, MinusCircle, Clock } from 'lucide-react'
import { emailApi, EmailMessage } from '../../api/email'

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  processed: { label: 'Przetworzono', color: 'bg-green-100 text-green-700', icon: <CheckCircle size={12} /> },
  error: { label: 'Błąd', color: 'bg-red-100 text-red-700', icon: <XCircle size={12} /> },
  duplicate: { label: 'Duplikat', color: 'bg-amber-100 text-amber-700', icon: <Copy size={12} /> },
  skipped: { label: 'Pominięto', color: 'bg-slate-100 text-slate-500', icon: <MinusCircle size={12} /> },
  pending: { label: 'Oczekuje', color: 'bg-blue-100 text-blue-700', icon: <Clock size={12} /> },
}

export default function EmailLog() {
  const [statusFilter, setStatusFilter] = useState('')
  const [page, setPage] = useState(0)
  const limit = 50

  const { data: messages = [], isLoading } = useQuery({
    queryKey: ['email-log-all', statusFilter, page],
    queryFn: () => emailApi.getAllLog({
      skip: page * limit,
      limit,
      ...(statusFilter ? { status: statusFilter } : {}),
    }),
  })

  function StatusBadge({ status }: { status: string }) {
    const cfg = STATUS_CONFIG[status] || { label: status, color: 'bg-slate-100 text-slate-500', icon: null }
    return (
      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${cfg.color}`}>
        {cfg.icon} {cfg.label}
      </span>
    )
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <Link to="/poczta" className="p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg">
          <ArrowLeft size={18} />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Dziennik poczty</h1>
          <p className="text-slate-500 text-sm">Historia przetworzonych wiadomości</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 mb-4">
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(0) }}
          className="border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Wszystkie statusy</option>
          <option value="processed">Przetworzono</option>
          <option value="duplicate">Duplikat</option>
          <option value="error">Błąd</option>
          <option value="skipped">Pominięto</option>
          <option value="pending">Oczekuje</option>
        </select>
      </div>

      {isLoading ? (
        <div className="text-center py-10 text-slate-400">Ładowanie...</div>
      ) : messages.length === 0 ? (
        <div className="text-center py-16 text-slate-400">
          <AlertCircle size={40} className="mx-auto mb-3 opacity-30" />
          <p className="font-medium">Brak wpisów</p>
        </div>
      ) : (
        <>
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-slate-600">Data</th>
                  <th className="text-left px-4 py-3 font-medium text-slate-600">Nadawca</th>
                  <th className="text-left px-4 py-3 font-medium text-slate-600">Temat</th>
                  <th className="text-left px-4 py-3 font-medium text-slate-600">Status</th>
                  <th className="text-right px-4 py-3 font-medium text-slate-600">Faktury</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {messages.map((msg: EmailMessage) => (
                  <tr key={msg.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3 text-slate-500 whitespace-nowrap">
                      {msg.received_at
                        ? new Date(msg.received_at).toLocaleString('pl-PL', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
                        : '—'}
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-medium text-slate-900 truncate max-w-[180px]">
                        {msg.sender_name || msg.sender_email || '—'}
                      </div>
                      {msg.sender_name && (
                        <div className="text-xs text-slate-400 truncate max-w-[180px]">{msg.sender_email}</div>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="truncate max-w-[280px] text-slate-700" title={msg.subject || ''}>
                        {msg.subject || '(bez tematu)'}
                      </div>
                      {msg.error_message && (
                        <div className="text-xs text-red-500 truncate max-w-[280px]" title={msg.error_message}>
                          {msg.error_message}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={msg.status} />
                    </td>
                    <td className="px-4 py-3 text-right">
                      {msg.invoices_created > 0 && (
                        <span className="text-green-700 font-medium">+{msg.invoices_created}</span>
                      )}
                      {msg.invoices_duplicated > 0 && (
                        <span className="text-amber-600 text-xs ml-1">({msg.invoices_duplicated} dup.)</span>
                      )}
                      {msg.invoices_created === 0 && msg.invoices_duplicated === 0 && (
                        <span className="text-slate-400">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between mt-4 text-sm text-slate-500">
            <span>Strona {page + 1}</span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                className="px-3 py-1.5 border border-slate-300 rounded-lg hover:bg-slate-50 disabled:opacity-40"
              >
                Poprzednia
              </button>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={messages.length < limit}
                className="px-3 py-1.5 border border-slate-300 rounded-lg hover:bg-slate-50 disabled:opacity-40"
              >
                Następna
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
