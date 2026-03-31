import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getPayments, deletePayment } from '../../api/payments'
import { formatCurrency, formatDate } from '../../utils/format'
import { Trash2, ChevronLeft, ChevronRight } from 'lucide-react'

const METHOD_LABELS: Record<string, string> = {
  przelew: 'Przelew bankowy',
  gotowka: 'Gotówka',
  karta: 'Karta płatnicza',
}

const PAGE_SIZE = 50

export default function PaymentList() {
  const [page, setPage] = useState(0)
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['payments', page],
    queryFn: () => getPayments({ skip: page * PAGE_SIZE, limit: PAGE_SIZE }),
  })

  const deleteMut = useMutation({
    mutationFn: deletePayment,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['payments'] }),
  })

  const items = data?.items || []
  const total = data?.total || 0
  const totalPages = Math.ceil(total / PAGE_SIZE)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Płatności</h1>
        <p className="text-sm text-gray-500">Łącznie: {total}</p>
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
                    <th className="table-header">Faktura</th>
                    <th className="table-header">Data płatności</th>
                    <th className="table-header">Metoda</th>
                    <th className="table-header text-right">Kwota</th>
                    <th className="table-header">Notatki</th>
                    <th className="table-header">Akcje</th>
                  </tr>
                </thead>
                <tbody>
                  {items.length === 0 ? (
                    <tr><td colSpan={6} className="text-center py-12 text-gray-400">Brak płatności</td></tr>
                  ) : (
                    items.map((p: Record<string, unknown>) => (
                      <tr key={p.id as string} className="border-b border-gray-50 hover:bg-gray-50 transition-colors">
                        <td className="table-cell">
                          <Link to={`/faktury/${p.invoice_id}`} className="text-blue-600 hover:underline font-medium">
                            {(p.invoice_number as string) || (p.invoice_id as string)}
                          </Link>
                        </td>
                        <td className="table-cell text-gray-500">{formatDate(p.payment_date as string)}</td>
                        <td className="table-cell text-gray-500">{METHOD_LABELS[p.method as string] || p.method as string}</td>
                        <td className="table-cell text-right font-semibold">{formatCurrency(p.amount as number)}</td>
                        <td className="table-cell text-gray-400 text-sm">{(p.notes as string) || '-'}</td>
                        <td className="table-cell">
                          <button
                            onClick={() => window.confirm('Usunąć płatność?') && deleteMut.mutate(p.id as string)}
                            className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                          >
                            <Trash2 size={15} />
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
            <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200">
              <p className="text-sm text-gray-500">Wyświetlono {items.length} z {total} płatności</p>
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
