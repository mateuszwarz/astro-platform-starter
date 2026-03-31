import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getContractors, deleteContractor } from '../../api/contractors'
import { Contractor } from '../../types'
import { Plus, Search, Edit, Trash2, ChevronLeft, ChevronRight } from 'lucide-react'

const CATEGORY_LABELS: Record<string, string> = { klient: 'Klient', dostawca: 'Dostawca', oba: 'Klient/Dostawca' }
const STATUS_LABELS: Record<string, string> = { aktywny: 'Aktywny', nieaktywny: 'Nieaktywny', ryzykowny: 'Ryzykowny' }
const STATUS_COLORS: Record<string, string> = {
  aktywny: 'bg-green-100 text-green-700',
  nieaktywny: 'bg-gray-100 text-gray-500',
  ryzykowny: 'bg-red-100 text-red-700',
}

const PAGE_SIZE = 50

export default function ContractorList() {
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')
  const [status, setStatus] = useState('')
  const [page, setPage] = useState(0)
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['contractors', search, category, status, page],
    queryFn: () => getContractors({ search: search || undefined, category: category || undefined, status: status || undefined, skip: page * PAGE_SIZE, limit: PAGE_SIZE }),
  })

  const deleteMut = useMutation({
    mutationFn: deleteContractor,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['contractors'] }),
  })

  const items: Contractor[] = data?.items || []
  const total = data?.total || 0
  const totalPages = Math.ceil(total / PAGE_SIZE)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Kontrahenci</h1>
        <Link to="/kontrahenci/nowy" className="btn-primary">
          <Plus size={16} /> Nowy kontrahent
        </Link>
      </div>

      <div className="card">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="relative">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input type="text" placeholder="Szukaj nazwa, NIP, email..." value={search} onChange={e => { setSearch(e.target.value); setPage(0) }} className="input-field pl-9" />
          </div>
          <select value={category} onChange={e => { setCategory(e.target.value); setPage(0) }} className="input-field">
            <option value="">Wszystkie kategorie</option>
            <option value="klient">Klient</option>
            <option value="dostawca">Dostawca</option>
            <option value="oba">Klient/Dostawca</option>
          </select>
          <select value={status} onChange={e => { setStatus(e.target.value); setPage(0) }} className="input-field">
            <option value="">Wszystkie statusy</option>
            <option value="aktywny">Aktywny</option>
            <option value="nieaktywny">Nieaktywny</option>
            <option value="ryzykowny">Ryzykowny</option>
          </select>
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
                    <th className="table-header">Nazwa</th>
                    <th className="table-header">NIP</th>
                    <th className="table-header">Email</th>
                    <th className="table-header">Telefon</th>
                    <th className="table-header">Termin płatności</th>
                    <th className="table-header">Kategoria</th>
                    <th className="table-header">Status</th>
                    <th className="table-header">Akcje</th>
                  </tr>
                </thead>
                <tbody>
                  {items.length === 0 ? (
                    <tr><td colSpan={8} className="text-center py-12 text-gray-400">Brak kontrahentów</td></tr>
                  ) : (
                    items.map(c => (
                      <tr key={c.id} className="border-b border-gray-50 hover:bg-gray-50 transition-colors">
                        <td className="table-cell">
                          <p className="font-medium text-gray-900">{c.name}</p>
                          <p className="text-xs text-gray-400">{c.city}</p>
                        </td>
                        <td className="table-cell font-mono text-sm">{c.nip || '-'}</td>
                        <td className="table-cell text-gray-500 text-sm">{c.email || '-'}</td>
                        <td className="table-cell text-gray-500 text-sm">{c.phone || '-'}</td>
                        <td className="table-cell text-center">{c.default_payment_days} dni</td>
                        <td className="table-cell text-gray-500 text-sm">{CATEGORY_LABELS[c.category] || c.category}</td>
                        <td className="table-cell">
                          <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[c.status] || ''}`}>
                            {STATUS_LABELS[c.status] || c.status}
                          </span>
                        </td>
                        <td className="table-cell">
                          <div className="flex items-center gap-2">
                            <Link to={`/kontrahenci/${c.id}/edytuj`} className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors">
                              <Edit size={15} />
                            </Link>
                            <button
                              onClick={() => window.confirm('Usunąć kontrahenta?') && deleteMut.mutate(c.id)}
                              className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                            >
                              <Trash2 size={15} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
            <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200">
              <p className="text-sm text-gray-500">Wyświetlono {items.length} z {total} kontrahentów</p>
              <div className="flex items-center gap-2">
                <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0} className="btn-secondary py-1.5 px-2 disabled:opacity-30"><ChevronLeft size={16} /></button>
                <span className="text-sm text-gray-700">Strona {page + 1} z {Math.max(1, totalPages)}</span>
                <button onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))} disabled={page >= totalPages - 1} className="btn-secondary py-1.5 px-2 disabled:opacity-30"><ChevronRight size={16} /></button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
