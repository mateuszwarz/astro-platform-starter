import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getVatReport, getIncomeCosts, getAgingReport, getTopContractors } from '../../api/reports'
import { formatCurrency, MONTH_NAMES_FULL } from '../../utils/format'
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts'
import { Download } from 'lucide-react'

const TABS = ['Rejestr VAT', 'Przychody vs Koszty', 'Wiekowanie należności', 'Top Kontrahenci'] as const
type Tab = typeof TABS[number]

const currentYear = new Date().getFullYear()
const currentMonth = new Date().getMonth() + 1
const YEARS = Array.from({ length: 5 }, (_, i) => currentYear - i)

export default function Reports() {
  const [tab, setTab] = useState<Tab>('Rejestr VAT')
  const [vatYear, setVatYear] = useState(currentYear)
  const [vatMonth, setVatMonth] = useState(currentMonth)
  const [vatType, setVatType] = useState('sprzedaz')
  const [incomeYear, setIncomeYear] = useState(currentYear)
  const [topYear, setTopYear] = useState(currentYear)

  const { data: vatData } = useQuery({
    queryKey: ['vat-report', vatYear, vatMonth, vatType],
    queryFn: () => getVatReport(vatYear, vatMonth, vatType),
    enabled: tab === 'Rejestr VAT',
  })

  const { data: incomeData } = useQuery({
    queryKey: ['income-costs', incomeYear],
    queryFn: () => getIncomeCosts(incomeYear),
    enabled: tab === 'Przychody vs Koszty',
  })

  const { data: agingData } = useQuery({
    queryKey: ['aging'],
    queryFn: getAgingReport,
    enabled: tab === 'Wiekowanie należności',
  })

  const { data: topData } = useQuery({
    queryKey: ['top-contractors', topYear],
    queryFn: () => getTopContractors(topYear),
    enabled: tab === 'Top Kontrahenci',
  })

  const exportVatCSV = () => {
    if (!vatData) return
    const headers = ['Nr faktury', 'Data', 'Kontrahent', 'NIP', 'Netto 0%', 'Netto 5%', 'VAT 5%', 'Netto 8%', 'VAT 8%', 'Netto 23%', 'VAT 23%', 'Brutto']
    const rows = vatData.rows.map((r: Record<string, unknown>) => [
      r.number, r.issue_date, r.contractor_name, r.contractor_nip,
      r.net_0, r.net_5, r.vat_5, r.net_8, r.vat_8, r.net_23, r.vat_23, r.gross
    ])
    const csv = [headers, ...rows].map((r: unknown[]) => r.join(';')).join('\n')
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' })
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `rejestr_vat_${vatYear}_${vatMonth}.csv`; a.click()
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Raporty</h1>

      <div className="flex border-b border-gray-200 gap-1">
        {TABS.map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
              tab === t
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === 'Rejestr VAT' && (
        <div className="space-y-4">
          <div className="card">
            <div className="flex flex-wrap items-center gap-4">
              <select value={vatYear} onChange={e => setVatYear(Number(e.target.value))} className="input-field w-28">
                {YEARS.map(y => <option key={y} value={y}>{y}</option>)}
              </select>
              <select value={vatMonth} onChange={e => setVatMonth(Number(e.target.value))} className="input-field w-40">
                {MONTH_NAMES_FULL.map((m, i) => <option key={i+1} value={i+1}>{m}</option>)}
              </select>
              <select value={vatType} onChange={e => setVatType(e.target.value)} className="input-field w-36">
                <option value="sprzedaz">Sprzedaż</option>
                <option value="zakup">Zakup</option>
              </select>
              <button onClick={exportVatCSV} className="btn-secondary ml-auto">
                <Download size={16} /> Eksport CSV
              </button>
            </div>
          </div>

          <div className="card p-0 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="table-header">Nr faktury</th>
                    <th className="table-header">Data</th>
                    <th className="table-header">Kontrahent</th>
                    <th className="table-header">NIP</th>
                    <th className="table-header text-right">Netto 0%</th>
                    <th className="table-header text-right">Netto 8%</th>
                    <th className="table-header text-right">VAT 8%</th>
                    <th className="table-header text-right">Netto 23%</th>
                    <th className="table-header text-right">VAT 23%</th>
                    <th className="table-header text-right">Brutto</th>
                  </tr>
                </thead>
                <tbody>
                  {(vatData?.rows || []).length === 0 ? (
                    <tr><td colSpan={10} className="text-center py-8 text-gray-400">Brak danych dla wybranych kryteriów</td></tr>
                  ) : (
                    vatData?.rows?.map((r: Record<string, unknown>, i: number) => (
                      <tr key={i} className="border-b border-gray-50">
                        <td className="table-cell font-medium">{r.number as string}</td>
                        <td className="table-cell text-gray-500">{r.issue_date as string}</td>
                        <td className="table-cell">{r.contractor_name as string}</td>
                        <td className="table-cell font-mono text-xs">{r.contractor_nip as string}</td>
                        <td className="table-cell text-right">{formatCurrency(r.net_0 as number)}</td>
                        <td className="table-cell text-right">{formatCurrency(r.net_8 as number)}</td>
                        <td className="table-cell text-right">{formatCurrency(r.vat_8 as number)}</td>
                        <td className="table-cell text-right">{formatCurrency(r.net_23 as number)}</td>
                        <td className="table-cell text-right">{formatCurrency(r.vat_23 as number)}</td>
                        <td className="table-cell text-right font-semibold">{formatCurrency(r.gross as number)}</td>
                      </tr>
                    ))
                  )}
                </tbody>
                {vatData?.totals && (
                  <tfoot className="bg-blue-50 border-t-2 border-blue-200 font-semibold">
                    <tr>
                      <td colSpan={4} className="table-cell text-right">RAZEM:</td>
                      <td className="table-cell text-right">{formatCurrency(vatData.totals.net_0)}</td>
                      <td className="table-cell text-right">{formatCurrency(vatData.totals.net_8)}</td>
                      <td className="table-cell text-right">{formatCurrency(vatData.totals.vat_8)}</td>
                      <td className="table-cell text-right">{formatCurrency(vatData.totals.net_23)}</td>
                      <td className="table-cell text-right">{formatCurrency(vatData.totals.vat_23)}</td>
                      <td className="table-cell text-right text-blue-700">{formatCurrency(vatData.totals.gross)}</td>
                    </tr>
                  </tfoot>
                )}
              </table>
            </div>
          </div>
        </div>
      )}

      {tab === 'Przychody vs Koszty' && (
        <div className="space-y-4">
          <div className="card">
            <div className="flex items-center gap-4">
              <label className="text-sm font-medium text-gray-700">Rok:</label>
              <select value={incomeYear} onChange={e => setIncomeYear(Number(e.target.value))} className="input-field w-28">
                {YEARS.map(y => <option key={y} value={y}>{y}</option>)}
              </select>
            </div>
          </div>

          <div className="card">
            <h3 className="font-semibold text-gray-700 mb-4">Przychody vs Koszty {incomeYear}</h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={incomeData?.rows || []} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="month_name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                <Tooltip formatter={(v: number) => formatCurrency(v)} />
                <Legend />
                <Bar dataKey="income" name="Przychody" fill="#3b82f6" radius={[4,4,0,0]} />
                <Bar dataKey="costs" name="Koszty" fill="#f97316" radius={[4,4,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="card p-0 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="table-header">Miesiąc</th>
                    <th className="table-header text-right">Przychody</th>
                    <th className="table-header text-right">Koszty</th>
                    <th className="table-header text-right">Zysk/Strata</th>
                  </tr>
                </thead>
                <tbody>
                  {(incomeData?.rows || []).map((r: Record<string, unknown>) => (
                    <tr key={r.month as number} className="border-b border-gray-50">
                      <td className="table-cell font-medium">{r.month_name as string}</td>
                      <td className="table-cell text-right text-blue-600">{formatCurrency(r.income as number)}</td>
                      <td className="table-cell text-right text-orange-600">{formatCurrency(r.costs as number)}</td>
                      <td className={`table-cell text-right font-semibold ${(r.profit as number) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {formatCurrency(r.profit as number)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {tab === 'Wiekowanie należności' && (
        <div className="space-y-4">
          <div className="card">
            <p className="text-sm text-gray-500">Wiekowanie należności i zobowiązań na dzień {agingData?.date || '-'}</p>
          </div>
          <div className="card p-0 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="table-header">Kontrahent</th>
                    <th className="table-header text-right">0-30 dni</th>
                    <th className="table-header text-right">31-60 dni</th>
                    <th className="table-header text-right">61-90 dni</th>
                    <th className="table-header text-right">90+ dni</th>
                    <th className="table-header text-right">RAZEM</th>
                  </tr>
                </thead>
                <tbody>
                  {(agingData?.rows || []).length === 0 ? (
                    <tr><td colSpan={6} className="text-center py-8 text-gray-400">Brak danych</td></tr>
                  ) : (
                    agingData?.rows?.map((r: Record<string, unknown>, i: number) => (
                      <tr key={i} className="border-b border-gray-50">
                        <td className="table-cell font-medium">{r.contractor_name as string}</td>
                        <td className="table-cell text-right">{formatCurrency(r.bucket_0_30 as number)}</td>
                        <td className="table-cell text-right text-yellow-600">{formatCurrency(r.bucket_31_60 as number)}</td>
                        <td className="table-cell text-right text-orange-600">{formatCurrency(r.bucket_61_90 as number)}</td>
                        <td className="table-cell text-right text-red-600">{formatCurrency(r.bucket_90_plus as number)}</td>
                        <td className="table-cell text-right font-semibold">{formatCurrency(r.total as number)}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {tab === 'Top Kontrahenci' && (
        <div className="space-y-4">
          <div className="card">
            <div className="flex items-center gap-4">
              <label className="text-sm font-medium text-gray-700">Rok:</label>
              <select value={topYear} onChange={e => setTopYear(Number(e.target.value))} className="input-field w-28">
                {YEARS.map(y => <option key={y} value={y}>{y}</option>)}
              </select>
            </div>
          </div>
          <div className="card p-0 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="table-header">Lp.</th>
                    <th className="table-header">Kontrahent</th>
                    <th className="table-header">NIP</th>
                    <th className="table-header text-right">Obrót netto</th>
                    <th className="table-header text-right">Obrót brutto</th>
                    <th className="table-header text-right">Liczba faktur</th>
                  </tr>
                </thead>
                <tbody>
                  {(topData?.rows || []).length === 0 ? (
                    <tr><td colSpan={6} className="text-center py-8 text-gray-400">Brak danych</td></tr>
                  ) : (
                    topData?.rows?.map((r: Record<string, unknown>, i: number) => (
                      <tr key={i} className="border-b border-gray-50">
                        <td className="table-cell text-gray-400 font-medium">{i + 1}</td>
                        <td className="table-cell font-medium">{r.contractor_name as string}</td>
                        <td className="table-cell font-mono text-xs text-gray-500">{r.contractor_nip as string}</td>
                        <td className="table-cell text-right">{formatCurrency(r.total_net as number)}</td>
                        <td className="table-cell text-right font-semibold">{formatCurrency(r.total_gross as number)}</td>
                        <td className="table-cell text-right">{r.invoice_count as number}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
