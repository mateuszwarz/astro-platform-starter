import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Plus, Trash2, Play, CheckCircle, XCircle, AlertCircle, Pencil, Wifi } from 'lucide-react'
import { emailApi, EmailSource, EmailSourceCreate } from '../../api/email'

const defaultForm: EmailSourceCreate = {
  name: '',
  host: '',
  port: 993,
  username: '',
  password: '',
  use_ssl: true,
  folder: 'INBOX',
  filter_senders: null,
  processed_label: null,
  is_active: true,
}

export default function EmailSources() {
  const qc = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [editId, setEditId] = useState<string | null>(null)
  const [form, setForm] = useState<EmailSourceCreate>(defaultForm)
  const [testResult, setTestResult] = useState<{ ok: boolean; error?: string | null; unseen_count?: number; folders?: string[] } | null>(null)
  const [testLoading, setTestLoading] = useState(false)
  const [filterSendersText, setFilterSendersText] = useState('')

  const { data: sources = [], isLoading } = useQuery({
    queryKey: ['email-sources'],
    queryFn: emailApi.listSources,
  })

  const createMutation = useMutation({
    mutationFn: emailApi.createSource,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['email-sources'] }); resetForm() },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<EmailSourceCreate> }) =>
      emailApi.updateSource(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['email-sources'] }); resetForm() },
  })

  const deleteMutation = useMutation({
    mutationFn: emailApi.deleteSource,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['email-sources'] }),
  })

  const triggerMutation = useMutation({
    mutationFn: emailApi.triggerFetch,
    onSuccess: (data: { task_id: string; message: string }) => alert(data.message),
  })

  function resetForm() {
    setShowForm(false)
    setEditId(null)
    setForm(defaultForm)
    setFilterSendersText('')
    setTestResult(null)
  }

  function startEdit(source: EmailSource) {
    setEditId(source.id)
    setForm({
      name: source.name,
      host: source.host,
      port: source.port,
      username: source.username,
      password: '',
      use_ssl: source.use_ssl,
      folder: source.folder,
      filter_senders: source.filter_senders,
      processed_label: source.processed_label,
      is_active: source.is_active,
    })
    setFilterSendersText((source.filter_senders || []).join('\n'))
    setShowForm(true)
    setTestResult(null)
  }

  async function handleTest() {
    setTestLoading(true)
    setTestResult(null)
    try {
      const result = await emailApi.testConnection({
        host: form.host,
        port: form.port,
        username: form.username,
        password: form.password,
        use_ssl: form.use_ssl,
        folder: form.folder,
      })
      setTestResult(result)
    } catch {
      setTestResult({ ok: false, error: 'Błąd połączenia' })
    } finally {
      setTestLoading(false)
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const senders = filterSendersText.trim()
      ? filterSendersText.split('\n').map((s) => s.trim()).filter(Boolean)
      : null
    const payload = { ...form, filter_senders: senders }

    if (editId) {
      updateMutation.mutate({ id: editId, data: payload })
    } else {
      createMutation.mutate(payload)
    }
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Skrzynki pocztowe</h1>
          <p className="text-slate-500 text-sm mt-1">Automatyczne pobieranie faktur z IMAP</p>
        </div>
        <div className="flex gap-2">
          <Link
            to="/poczta/log"
            className="px-4 py-2 text-sm border border-slate-300 rounded-lg hover:bg-slate-50"
          >
            Dziennik
          </Link>
          <button
            onClick={() => { setShowForm(true); setEditId(null); setForm(defaultForm); setFilterSendersText('') }}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
          >
            <Plus size={16} /> Dodaj skrzynkę
          </button>
        </div>
      </div>

      {/* Form */}
      {showForm && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">
            {editId ? 'Edytuj skrzynkę' : 'Nowa skrzynka IMAP'}
          </h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <label className="block text-sm font-medium text-slate-700 mb-1">Nazwa</label>
                <input
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="np. Faktury biuro"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Serwer IMAP</label>
                <input
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  value={form.host}
                  onChange={(e) => setForm({ ...form, host: e.target.value })}
                  placeholder="imap.gmail.com"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Port</label>
                <input
                  type="number"
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  value={form.port}
                  onChange={(e) => setForm({ ...form, port: parseInt(e.target.value) || 993 })}
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Login (e-mail)</label>
                <input
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  value={form.username}
                  onChange={(e) => setForm({ ...form, username: e.target.value })}
                  placeholder="faktury@firma.pl"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Hasło {editId && <span className="text-slate-400 font-normal">(zostaw puste aby nie zmieniać)</span>}
                </label>
                <input
                  type="password"
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  placeholder={editId ? '••••••••' : 'Hasło lub hasło do aplikacji'}
                  required={!editId}
                  autoComplete="new-password"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Folder</label>
                <input
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  value={form.folder}
                  onChange={(e) => setForm({ ...form, folder: e.target.value })}
                  placeholder="INBOX"
                />
              </div>
              <div className="flex items-center gap-2 pt-6">
                <input
                  type="checkbox"
                  id="use_ssl"
                  checked={form.use_ssl}
                  onChange={(e) => setForm({ ...form, use_ssl: e.target.checked })}
                  className="rounded"
                />
                <label htmlFor="use_ssl" className="text-sm text-slate-700">SSL/TLS</label>
              </div>
              <div className="col-span-2">
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Filtry nadawców <span className="text-slate-400 font-normal">(jeden na linię, np. @firma.pl)</span>
                </label>
                <textarea
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  rows={3}
                  value={filterSendersText}
                  onChange={(e) => setFilterSendersText(e.target.value)}
                  placeholder="@dostawca.pl&#10;faktury@contrahent.com"
                />
              </div>
            </div>

            {/* Test result */}
            {testResult && (
              <div className={`flex items-start gap-2 p-3 rounded-lg text-sm ${testResult.ok ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
                {testResult.ok
                  ? <CheckCircle size={16} className="mt-0.5 shrink-0" />
                  : <XCircle size={16} className="mt-0.5 shrink-0" />
                }
                <span>
                  {testResult.ok
                    ? `Połączenie OK. Nieprzeczytanych: ${testResult.unseen_count}`
                    : `Błąd: ${testResult.error}`
                  }
                </span>
              </div>
            )}

            <div className="flex items-center gap-3 pt-2">
              <button
                type="submit"
                className="px-5 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium"
                disabled={createMutation.isPending || updateMutation.isPending}
              >
                {editId ? 'Zapisz zmiany' : 'Dodaj skrzynkę'}
              </button>
              <button
                type="button"
                onClick={handleTest}
                disabled={testLoading || !form.host || !form.username || (!form.password && !editId)}
                className="flex items-center gap-2 px-4 py-2 border border-slate-300 rounded-lg hover:bg-slate-50 text-sm disabled:opacity-50"
              >
                <Wifi size={14} />
                {testLoading ? 'Sprawdzam...' : 'Testuj połączenie'}
              </button>
              <button
                type="button"
                onClick={resetForm}
                className="px-4 py-2 text-sm text-slate-500 hover:text-slate-700"
              >
                Anuluj
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Sources list */}
      {isLoading ? (
        <div className="text-center py-10 text-slate-400">Ładowanie...</div>
      ) : sources.length === 0 ? (
        <div className="text-center py-16 text-slate-400">
          <AlertCircle size={40} className="mx-auto mb-3 opacity-30" />
          <p className="font-medium">Brak skrzynek pocztowych</p>
          <p className="text-sm mt-1">Dodaj skrzynkę IMAP, aby automatycznie pobierać faktury</p>
        </div>
      ) : (
        <div className="space-y-3">
          {sources.map((source: EmailSource) => (
            <div key={source.id} className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-slate-900">{source.name}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${source.is_active ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-500'}`}>
                      {source.is_active ? 'Aktywna' : 'Wyłączona'}
                    </span>
                  </div>
                  <p className="text-sm text-slate-500 mt-0.5">
                    {source.username} @ {source.host}:{source.port} ({source.folder})
                  </p>
                  {source.last_checked_at && (
                    <p className="text-xs text-slate-400 mt-1">
                      Ostatnie sprawdzenie: {new Date(source.last_checked_at).toLocaleString('pl-PL')}
                    </p>
                  )}
                  {source.last_error && (
                    <p className="text-xs text-red-500 mt-1 flex items-center gap-1">
                      <XCircle size={12} /> {source.last_error}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => triggerMutation.mutate(source.id)}
                    disabled={triggerMutation.isPending}
                    title="Pobierz teraz"
                    className="p-2 text-slate-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                  >
                    <Play size={16} />
                  </button>
                  <button
                    onClick={() => startEdit(source)}
                    title="Edytuj"
                    className="p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
                  >
                    <Pencil size={16} />
                  </button>
                  <button
                    onClick={() => {
                      if (confirm(`Usunąć skrzynkę "${source.name}"?`)) deleteMutation.mutate(source.id)
                    }}
                    title="Usuń"
                    className="p-2 text-slate-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
