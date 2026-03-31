import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { getDashboard } from '../api/reports'
import { DashboardData } from '../types'
import { StatusBadge } from '../components/StatusBadge'
import { formatCurrency, formatDate, MONTH_NAMES } from '../utils/format'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts'
import { TrendingUp, TrendingDown, AlertTriangle, CheckCircle, Wifi } from 'lucide-react'

export default function Dashboard() {
  const { data, isLoading } = useQuery<DashboardData>({
    queryKey: ['dashboard'],
    queryFn: getDashboard,
    refetchInterval: 60000,
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    )
  }

  const chartData = data?.monthly_revenue?.map((m) => ({
    name: MONTH_NAMES[m.month - 1],
    Przychody: m.revenue,
    Koszty: m.costs,
  })) || []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium ${
          data?.ksef_status === 'connected' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
        }`}>
          <Wifi size={14} />
          KSeF: {data?.ksef_status === 'connected' ? 'Połączony' : 'Brak połączenia'}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
        <div className="card">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm font-medium text-gray-500">Należności</p>
            <div className="w-9 h-9 bg-blue-100 rounded-lg flex items-center justify-center">
              <TrendingUp size={18} className="text-blue-600" />
            </div>
          </div>
          <p className="text-2xl font-bold text-gray-900">{formatCurrency(data?.receivables_total || 0)}</p>
          <p className="text-xs text-gray-400 mt-1">Do otrzymania</p>
        </div>

        <div className="card">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm font-medium text-gray-500">Zobowiązania</p>
            <div className="w-9 h-9 bg-orange-100 rounded-lg flex items-center justify-center">
              <TrendingDown size={18} className="text-orange-600" />
            </div>
          </div>
          <p className="text-2xl font-bold text-gray-900">{formatCurrency(data?.payables_total || 0)}</p>
          <p className="text-xs text-gray-400 mt-1">Do zapłacenia</p>
        </div>

        <div className="card">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm font-medium text-gray-500">Przeterminowane</p>
            <div className="w-9 h-9 bg-red-100 rounded-lg flex items-center justify-center">
              <AlertTriangle size={18} className="text-red-600" />
            </div>
          </div>
          <p className="text-2xl font-bold text-red-600">{data?.overdue_count || 0}</p>
          <p className="text-xs text-gray-400 mt-1">{formatCurrency(data?.overdue_amount || 0)}</p>
        </div>

        <div className="card">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm font-medium text-gray-500">Zapłacone w tym miesiącu</p>
            <div className="w-9 h-9 bg-green-100 rounded-lg flex items-center justify-center">
              <CheckCircle size={18} className="text-green-600" />
            </div>
          </div>
          <p className="text-2xl font-bold text-green-600">{formatCurrency(data?.paid_this_month || 0)}</p>
          <p className="text-xs text-gray-400 mt-1">Bieżący miesiąc</p>
        </div>
      </div>

      {(data?.overdue_count || 0) > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-start gap-3">
          <AlertTriangle size={20} className="text-red-500 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-red-700">Przeterminowane faktury</p>
            <p className="text-sm text-red-600 mt-0.5">
              Masz {data?.overdue_count} przeterminowanych faktur na łączną kwotę {formatCurrency(data?.overdue_amount || 0)}.{' '}
              <Link to="/faktury?status=przeterminowana" className="underline font-medium">
                Pokaż szczegóły
              </Link>
            </p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2 card">
          <h2 className="text-base font-semibold text-gray-900 mb-4">Przychody vs Koszty {new Date().getFullYear()}</h2>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={chartData} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
              <Tooltip formatter={(value: number) => formatCurrency(value)} />
              <Legend />
              <Bar dataKey="Przychody" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              <Bar dataKey="Koszty" fill="#f97316" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <h2 className="text-base font-semibold text-gray-900 mb-4">Faktury do opłacenia (7 dni)</h2>
          {(data?.pending_this_week?.length || 0) === 0 ? (
            <p className="text-gray-400 text-sm text-center py-8">Brak faktur do opłacenia</p>
          ) : (
            <div className="space-y-3">
              {data?.pending_this_week?.map((inv) => (
                <Link
                  key={inv.id}
                  to={`/faktury/${inv.id}`}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <div>
                    <p className="text-sm font-medium text-gray-900">{inv.number}</p>
                    <p className="text-xs text-gray-500">Termin: {formatDate(inv.due_date)}</p>
                  </div>
                  <p className="text-sm font-semibold text-gray-900">{formatCurrency(inv.gross_amount)}</p>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold text-gray-900">Ostatnie faktury</h2>
          <Link to="/faktury" className="text-sm text-blue-600 hover:underline">
            Pokaż wszystkie
          </Link>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="table-header">Numer</th>
                <th className="table-header">Typ</th>
                <th className="table-header">Data</th>
                <th className="table-header">Kwota brutto</th>
                <th className="table-header">Status</th>
              </tr>
            </thead>
            <tbody>
              {data?.recent_invoices?.map((inv) => (
                <tr key={inv.id} className="border-b border-gray-50 hover:bg-gray-50 transition-colors">
                  <td className="table-cell">
                    <Link to={`/faktury/${inv.id}`} className="text-blue-600 hover:underline font-medium">
                      {inv.number}
                    </Link>
                  </td>
                  <td className="table-cell text-gray-500">{inv.type}</td>
                  <td className="table-cell text-gray-500">{formatDate(inv.issue_date)}</td>
                  <td className="table-cell font-medium">{formatCurrency(inv.gross_amount)}</td>
                  <td className="table-cell">
                    <StatusBadge status={inv.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
