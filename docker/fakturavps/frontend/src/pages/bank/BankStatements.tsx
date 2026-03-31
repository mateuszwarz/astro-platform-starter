import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  uploadBankStatement, getBankStatements, getStatementTransactions,
  getMatchSuggestions, matchTransaction, confirmPayment, deleteBankStatement,
} from '../../api/bankStatements'
import { formatCurrency, formatDate } from '../../utils/format'
import type { BankStatement, BankTransaction, MatchSuggestion } from '../../types'
import {
  Upload, Loader2, Check, X, Search, AlertCircle, CheckCircle,
  ChevronDown, ChevronRight, Trash2, Link2, Link2Off,
} from 'lucide-react'

const MATCH_STATUS_LABELS: Record<string, string> = {
  unmatched: 'Nieprzypisana',
  matched: 'Auto-dopasowana',
  manual: 'Ręcznie dopasowana',
  ignored: 'Zignorowana',
}
const MATCH_STATUS_COLORS: Record<string, string> = {
  unmatched: 'bg-gray-100 text-gray-600',
  matched: 'bg-green-100 text-green-700',
  manual: 'bg-blue-100 text-blue-700',
  ignored: 'bg-yellow-100 text-yellow-700',
}

// ── Match row component ────────────────────────────────────────────────────────
function TransactionRow({
  t,
  statementId,
  onRefresh,
}: {
  t: BankTransaction
  statementId: string
  onRefresh: () => void
}) {
  const [expanded, setExpanded] = useState(false)
  const [suggestions, setSuggestions] = useState<MatchSuggestion[] | null>(null)
  const [loadingSugg, setLoadingSugg] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)
  const qc = useQueryClient()

  const matchMut = useMutation({
    mutationFn: ({ action, invoiceId, notes }: { action: 'match' | 'unmatch' | 'ignore'; invoiceId?: string; notes?: string }) =>
      matchTransaction(statementId, t.id, action, invoiceId, notes),
    onSuccess: () => { onRefresh(); setMsg(null) },
    onError: () => setMsg('Błąd dopasowania'),
  })

  const confirmMut = useMutation({
    mutationFn: () => confirmPayment(statementId, t.id),
    onSuccess: (res) => {
      setMsg(`Płatność potwierdzona! Faktura ${res.invoice_number} → ${res.invoice_status}`)
      onRefresh()
      qc.invalidateQueries({ queryKey: ['invoices'] })
    },
    onError: (e: unknown) => setMsg((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Błąd'),
  })

  const loadSuggestions = async () => {
    if (suggestions) { setExpanded(v => !v); return }
    setLoadingSugg(true)
    try {
      const data = await getMatchSuggestions(statementId, t.id)
      setSuggestions(data.suggestions)
      setExpanded(true)
    } catch {
      setMsg('Błąd pobierania sugestii')
    } finally {
      setLoadingSugg(false)
    }
  }

  const isCredit = t.amount > 0

  return (
    <>
      <tr className={`border-b border-gray-50 hover:bg-gray-50/50 ${t.match_status === 'ignored' ? 'opacity-50' : ''}`}>
        <td className="table-cell text-sm text-gray-500">{formatDate(t.transaction_date)}</td>
        <td className="table-cell">
          <p className="text-sm font-medium">{t.counterparty_name || '—'}</p>
          {t.description && <p className="text-xs text-gray-400 truncate max-w-56">{t.description}</p>}
        </td>
        <td className={`table-cell text-right font-semibold text-sm ${isCredit ? 'text-green-600' : 'text-red-600'}`}>
          {isCredit ? '+' : ''}{formatCurrency(t.amount)}
        </td>
        <td className="table-cell">
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${MATCH_STATUS_COLORS[t.match_status]}`}>
            {MATCH_STATUS_LABELS[t.match_status] || t.match_status}
            {t.match_confidence ? ` ${t.match_confidence}%` : ''}
          </span>
        </td>
        <td className="table-cell">
          {t.matched_invoice ? (
            <div className="text-xs">
              <p className="font-semibold text-blue-700">{t.matched_invoice.number}</p>
              <p className="text-gray-400">{t.matched_invoice.contractor_name}</p>
              <p className="text-gray-400">{formatCurrency(t.matched_invoice.gross_amount)}</p>
            </div>
          ) : (
            <span className="text-gray-300 text-xs">—</span>
          )}
        </td>
        <td className="table-cell">
          <div className="flex items-center gap-1">
            {/* Suggestions / Match */}
            {t.match_status !== 'ignored' && !t.matched_invoice && (
              <button
                onClick={loadSuggestions}
                className="btn-secondary py-1 px-2 text-xs"
                title="Pokaż sugestie dopasowania"
                disabled={loadingSugg}
              >
                {loadingSugg ? <Loader2 size={12} className="animate-spin" /> : <Search size={12} />}
              </button>
            )}
            {/* Confirm payment */}
            {t.matched_invoice && t.match_status !== 'ignored' && (
              <button
                onClick={() => confirmMut.mutate()}
                disabled={confirmMut.isPending}
                className="btn-primary py-1 px-2 text-xs"
                title="Potwierdź jako płatność"
              >
                {confirmMut.isPending ? <Loader2 size={12} className="animate-spin" /> : <Check size={12} />}
                <span className="hidden sm:inline ml-1">Potwierdź</span>
              </button>
            )}
            {/* Unmatch */}
            {t.matched_invoice && (
              <button
                onClick={() => matchMut.mutate({ action: 'unmatch' })}
                className="text-gray-400 hover:text-red-500 p-1"
                title="Usuń dopasowanie"
              >
                <Link2Off size={13} />
              </button>
            )}
            {/* Ignore */}
            {t.match_status !== 'ignored' && !t.matched_invoice && (
              <button
                onClick={() => matchMut.mutate({ action: 'ignore' })}
                className="text-gray-300 hover:text-yellow-500 p-1"
                title="Ignoruj transakcję"
              >
                <X size={13} />
              </button>
            )}
            {/* Unignore */}
            {t.match_status === 'ignored' && (
              <button
                onClick={() => matchMut.mutate({ action: 'unmatch' })}
                className="text-xs text-gray-400 hover:text-blue-600"
              >
                Przywróć
              </button>
            )}
          </div>
        </td>
      </tr>

      {/* Suggestions panel */}
      {expanded && suggestions && (
        <tr className="bg-blue-50/40">
          <td colSpan={6} className="px-4 py-3">
            {msg && (
              <p className="text-xs text-green-700 mb-2 bg-green-50 border border-green-200 rounded px-2 py-1">{msg}</p>
            )}
            {suggestions.length === 0 ? (
              <p className="text-sm text-gray-400">Brak pasujących faktur.</p>
            ) : (
              <div className="space-y-2">
                <p className="text-xs font-semibold text-gray-500 mb-1">Sugerowane faktury:</p>
                {suggestions.map(s => (
                  <div key={s.invoice_id} className="flex items-center justify-between bg-white rounded-lg border border-gray-200 px-3 py-2 text-sm">
                    <div>
                      <span className="font-semibold text-blue-700 mr-2">{s.invoice_number}</span>
                      <span className="text-gray-500">{s.contractor_name}</span>
                      <span className="mx-2 text-gray-300">|</span>
                      <span className="font-medium">{formatCurrency(s.invoice_gross)}</span>
                      <span className="mx-2 text-gray-300">|</span>
                      <span className={`text-xs px-1.5 py-0.5 rounded-full ${s.confidence >= 80 ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}>
                        {s.confidence}% pewność
                      </span>
                    </div>
                    <button
                      onClick={() => matchMut.mutate({ action: 'match', invoiceId: s.invoice_id })}
                      disabled={matchMut.isPending}
                      className="btn-primary py-1 px-3 text-xs flex items-center gap-1"
                    >
                      <Link2 size={12} /> Dopasuj
                    </button>
                  </div>
                ))}
              </div>
            )}
          </td>
        </tr>
      )}
    </>
  )
}

// ── Statement detail panel ────────────────────────────────────────────────────
function StatementDetail({ statement, onBack }: { statement: BankStatement; onBack: () => void }) {
  const [filterStatus, setFilterStatus] = useState('')
  const [page, setPage] = useState(0)
  const PAGE = 30

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['bank-transactions', statement.id, filterStatus, page],
    queryFn: () => getStatementTransactions(statement.id, {
      match_status: filterStatus || undefined,
      skip: page * PAGE,
      limit: PAGE,
    }),
  })

  const transactions: BankTransaction[] = data?.items || []
  const total = data?.total || 0

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <button onClick={onBack} className="btn-secondary py-1.5 text-sm">← Powrót</button>
        <h2 className="text-lg font-bold text-gray-800">{statement.filename}</h2>
        <span className="text-sm text-gray-400">
          {statement.transaction_count} transakcji, {statement.matched_count} dopasowanych
        </span>
      </div>

      {/* Filter */}
      <div className="flex gap-2 flex-wrap">
        {['', 'unmatched', 'matched', 'manual', 'ignored'].map(s => (
          <button
            key={s}
            onClick={() => { setFilterStatus(s); setPage(0) }}
            className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
              filterStatus === s
                ? 'bg-blue-600 text-white border-blue-600'
                : 'bg-white text-gray-600 border-gray-300 hover:border-blue-400'
            }`}
          >
            {s === '' ? 'Wszystkie' : MATCH_STATUS_LABELS[s]}
          </button>
        ))}
      </div>

      <div className="card p-0 overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center h-32">
            <Loader2 size={24} className="animate-spin text-blue-500" />
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b text-xs">
                  <tr>
                    <th className="table-header">Data</th>
                    <th className="table-header">Kontrahent / Opis</th>
                    <th className="table-header text-right">Kwota</th>
                    <th className="table-header">Status</th>
                    <th className="table-header">Dopasowana faktura</th>
                    <th className="table-header">Akcje</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.length === 0 ? (
                    <tr><td colSpan={6} className="text-center py-10 text-gray-400 text-sm">Brak transakcji</td></tr>
                  ) : (
                    transactions.map(t => (
                      <TransactionRow
                        key={t.id}
                        t={t}
                        statementId={statement.id}
                        onRefresh={refetch}
                      />
                    ))
                  )}
                </tbody>
              </table>
            </div>
            <div className="flex items-center justify-between px-4 py-3 border-t text-sm text-gray-500">
              <span>Wyświetlono {transactions.length} z {total}</span>
              <div className="flex gap-2">
                <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0} className="btn-secondary py-1 px-2 disabled:opacity-30 text-xs">←</button>
                <span>Str. {page + 1}</span>
                <button onClick={() => setPage(p => p + 1)} disabled={(page + 1) * PAGE >= total} className="btn-secondary py-1 px-2 disabled:opacity-30 text-xs">→</button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function BankStatements() {
  const [selected, setSelected] = useState<BankStatement | null>(null)
  const [uploadMsg, setUploadMsg] = useState<{ type: 'ok' | 'err'; text: string } | null>(null)
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['bank-statements'],
    queryFn: () => getBankStatements(),
  })

  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteBankStatement(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['bank-statements'] }),
  })

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    setUploadMsg(null)
    try {
      const res = await uploadBankStatement(file)
      setUploadMsg({
        type: 'ok',
        text: `Wczytano "${res.filename}": ${res.transaction_count} transakcji, automatycznie dopasowano ${res.auto_matched}.`,
      })
      qc.invalidateQueries({ queryKey: ['bank-statements'] })
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setUploadMsg({ type: 'err', text: msg || 'Błąd wczytywania pliku' })
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const statements: BankStatement[] = data?.items || []

  if (selected) {
    return <StatementDetail statement={selected} onBack={() => setSelected(null)} />
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Wyciągi bankowe</h1>
      </div>

      {/* Upload area */}
      <div className="card border-2 border-dashed border-blue-200 bg-blue-50/20">
        <h2 className="font-semibold text-gray-700 mb-1 flex items-center gap-2">
          <Upload size={16} className="text-blue-500" />
          Wczytaj wyciąg bankowy
        </h2>
        <p className="text-xs text-gray-500 mb-3">
          Obsługiwane formaty: <strong>CSV</strong> (PKO BP, ING, mBank, Pekao) oraz <strong>MT940</strong> (SWIFT).
          Aplikacja automatycznie rozpozna transakcje i spróbuje dopasować je do faktur.
        </p>
        <div className="flex items-center gap-3 flex-wrap">
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.txt,.sta,.940,.mt940"
            onChange={handleUpload}
            className="hidden"
            id="stmt-upload"
            disabled={uploading}
          />
          <label
            htmlFor="stmt-upload"
            className={`btn-primary cursor-pointer flex items-center gap-2 ${uploading ? 'opacity-60 pointer-events-none' : ''}`}
          >
            {uploading ? <Loader2 size={16} className="animate-spin" /> : <Upload size={16} />}
            {uploading ? 'Wczytuję...' : 'Wybierz plik wyciągu'}
          </label>
          <p className="text-xs text-gray-400">Max 10 MB</p>
        </div>
        {uploadMsg && (
          <div className={`mt-3 flex items-start gap-2 text-sm rounded-lg px-3 py-2 border ${uploadMsg.type === 'ok' ? 'bg-green-50 text-green-700 border-green-200' : 'bg-red-50 text-red-600 border-red-200'}`}>
            {uploadMsg.type === 'ok' ? <CheckCircle size={16} className="shrink-0 mt-0.5" /> : <AlertCircle size={16} className="shrink-0 mt-0.5" />}
            {uploadMsg.text}
          </div>
        )}
      </div>

      {/* How it works */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { step: '1', title: 'Wczytaj plik', desc: 'Pobierz wyciąg z banku (CSV lub MT940) i załaduj tutaj.' },
          { step: '2', title: 'Sprawdź dopasowania', desc: 'Aplikacja automatycznie dopasowuje transakcje do faktur na podstawie kwoty, daty i NIP kontrahenta.' },
          { step: '3', title: 'Potwierdź płatności', desc: 'Kliknij "Potwierdź" przy dopasowanej transakcji, aby oznaczyć fakturę jako opłaconą.' },
        ].map(s => (
          <div key={s.step} className="card flex items-start gap-3">
            <div className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center text-sm font-bold shrink-0">
              {s.step}
            </div>
            <div>
              <p className="font-semibold text-gray-800 text-sm">{s.title}</p>
              <p className="text-xs text-gray-500 mt-0.5">{s.desc}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Statements list */}
      <div className="card p-0 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100">
          <h2 className="font-semibold text-gray-700">Wczytane wyciągi</h2>
        </div>
        {isLoading ? (
          <div className="flex items-center justify-center h-24">
            <Loader2 size={20} className="animate-spin text-blue-500" />
          </div>
        ) : statements.length === 0 ? (
          <p className="text-center text-gray-400 text-sm py-10">Brak wczytanych wyciągów</p>
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50 border-b text-xs">
              <tr>
                <th className="table-header">Plik</th>
                <th className="table-header">Format / Bank</th>
                <th className="table-header">Okres</th>
                <th className="table-header text-right">Transakcje</th>
                <th className="table-header text-right">Dopasowane</th>
                <th className="table-header">Wczytano</th>
                <th className="table-header"></th>
              </tr>
            </thead>
            <tbody>
              {statements.map((s: BankStatement) => {
                const pct = s.transaction_count > 0
                  ? Math.round((s.matched_count / s.transaction_count) * 100)
                  : 0
                return (
                  <tr key={s.id} className="border-b border-gray-50 hover:bg-blue-50/20 cursor-pointer" onClick={() => setSelected(s)}>
                    <td className="table-cell">
                      <p className="font-medium text-blue-700 text-sm">{s.filename}</p>
                    </td>
                    <td className="table-cell text-sm text-gray-500">{s.bank_name || 'Auto-detect'}</td>
                    <td className="table-cell text-sm text-gray-500">
                      {s.date_from && s.date_to
                        ? `${formatDate(s.date_from)} – ${formatDate(s.date_to)}`
                        : '—'}
                    </td>
                    <td className="table-cell text-right text-sm font-medium">{s.transaction_count}</td>
                    <td className="table-cell text-right">
                      <span className={`text-sm font-semibold ${pct === 100 ? 'text-green-600' : pct >= 50 ? 'text-blue-600' : 'text-gray-500'}`}>
                        {s.matched_count} <span className="text-gray-400 font-normal text-xs">({pct}%)</span>
                      </span>
                    </td>
                    <td className="table-cell text-sm text-gray-400">{formatDate(s.uploaded_at)}</td>
                    <td className="table-cell" onClick={e => e.stopPropagation()}>
                      <button
                        onClick={() => window.confirm('Usunąć wyciąg i wszystkie transakcje?') && deleteMut.mutate(s.id)}
                        className="text-gray-300 hover:text-red-500 p-1"
                      >
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
