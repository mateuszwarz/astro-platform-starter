import { useState, useEffect, useRef } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { getInvoice, createInvoice, updateInvoice, uploadOcr } from '../../api/invoices'
import { getContractors } from '../../api/contractors'
import { formatCurrency } from '../../utils/format'
import { ArrowLeft, Plus, Trash2, Save, Upload, FileText, X, Loader2 } from 'lucide-react'

interface InvoiceItemForm {
  name: string
  quantity: string
  unit: string
  unit_price_net: string
  vat_rate: string
  net_amount: number
  vat_amount: number
  gross_amount: number
}

const VAT_RATES = ['23', '8', '5', '0', 'zw', 'np']
const INVOICE_TYPES = [
  { value: 'sprzedaz', label: 'Faktura VAT (sprzedaż)' },
  { value: 'zakup', label: 'Faktura zakupowa' },
  { value: 'korekta', label: 'Faktura korygująca' },
  { value: 'zaliczkowa', label: 'Faktura zaliczkowa' },
  { value: 'proforma', label: 'Pro Forma' },
  { value: 'paragon', label: 'Paragon' },
]

const calcItem = (qty: string, price: string, vatRate: string): { net: number; vat: number; gross: number } => {
  const q = parseFloat(qty) || 0
  const p = parseFloat(price) || 0
  const vatRates: Record<string, number> = { '23': 0.23, '8': 0.08, '5': 0.05, '0': 0, 'zw': 0, 'np': 0 }
  const rate = vatRates[vatRate] ?? 0.23
  const net = Math.round(q * p * 100) / 100
  const vat = Math.round(net * rate * 100) / 100
  return { net, vat, gross: net + vat }
}

const emptyItem = (): InvoiceItemForm => ({
  name: '',
  quantity: '1',
  unit: 'szt',
  unit_price_net: '',
  vat_rate: '23',
  net_amount: 0,
  vat_amount: 0,
  gross_amount: 0,
})

export default function InvoiceForm() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const isEdit = Boolean(id)

  const [type, setType] = useState('sprzedaz')
  const [contractorId, setContractorId] = useState('')
  const [issueDate, setIssueDate] = useState(new Date().toISOString().split('T')[0])
  const [saleDate, setSaleDate] = useState(new Date().toISOString().split('T')[0])
  const [dueDate, setDueDate] = useState('')
  const [notes, setNotes] = useState('')
  const [currency, setCurrency] = useState('PLN')
  const [costType, setCostType] = useState('')
  const [attachmentPath, setAttachmentPath] = useState('')
  const [attachmentFilename, setAttachmentFilename] = useState('')
  const [items, setItems] = useState<InvoiceItemForm[]>([emptyItem()])
  const [error, setError] = useState('')
  const [contractorSearch, setContractorSearch] = useState('')
  const [ocrLoading, setOcrLoading] = useState(false)
  const [ocrMsg, setOcrMsg] = useState<{ type: 'ok' | 'err'; text: string } | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const { data: invoiceData } = useQuery({
    queryKey: ['invoice', id],
    queryFn: () => getInvoice(id!),
    enabled: isEdit,
  })

  const { data: contractorsData } = useQuery({
    queryKey: ['contractors', contractorSearch],
    queryFn: () => getContractors({ search: contractorSearch, limit: 20 }),
  })

  useEffect(() => {
    if (invoiceData && isEdit) {
      const inv = invoiceData.invoice
      setType(inv.type)
      setContractorId(inv.contractor_id || '')
      setIssueDate(inv.issue_date)
      setSaleDate(inv.sale_date || '')
      setDueDate(inv.due_date || '')
      setNotes(inv.notes || '')
      setCurrency(inv.currency || 'PLN')
      setCostType(inv.cost_type || '')
      setAttachmentPath(inv.attachment_path || '')
      setAttachmentFilename(inv.attachment_filename || '')
      if (invoiceData.items?.length) {
        setItems(invoiceData.items.map((i: Record<string, unknown>) => ({
          name: i.name as string,
          quantity: String(i.quantity),
          unit: (i.unit as string) || 'szt',
          unit_price_net: String(i.unit_price_net),
          vat_rate: i.vat_rate as string,
          net_amount: i.net_amount as number,
          vat_amount: i.vat_amount as number,
          gross_amount: i.gross_amount as number,
        })))
      }
    }
  }, [invoiceData, isEdit])

  const handleOcrUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setOcrLoading(true)
    setOcrMsg(null)
    try {
      const result = await uploadOcr(file)
      // Pre-fill form fields with extracted data
      if (result.detected_type) setType(result.detected_type)
      if (result.issue_date) setIssueDate(result.issue_date)
      if (result.sale_date) setSaleDate(result.sale_date)
      if (result.due_date) setDueDate(result.due_date)
      if (result.attachment_path) setAttachmentPath(result.attachment_path)
      if (result.attachment_filename) setAttachmentFilename(result.attachment_filename)
      setOcrMsg({ type: 'ok', text: `Rozpoznano dokument. Sprawdź i uzupełnij pola formularza. Plik "${file.name}" zapisany jako załącznik.` })
    } catch {
      setOcrMsg({ type: 'err', text: 'Błąd OCR. Sprawdź format pliku (PDF, JPG, PNG).' })
    } finally {
      setOcrLoading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const mutation = useMutation({
    mutationFn: (data: unknown) => isEdit ? updateInvoice(id!, data) : createInvoice(data),
    onSuccess: (res) => navigate(`/faktury/${res.id}`),
    onError: (e: unknown) => setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Błąd zapisu faktury'),
  })

  const updateItem = (idx: number, field: keyof InvoiceItemForm, value: string) => {
    setItems(prev => {
      const updated = [...prev]
      updated[idx] = { ...updated[idx], [field]: value }
      const item = updated[idx]
      const { net, vat, gross } = calcItem(item.quantity, item.unit_price_net, item.vat_rate)
      updated[idx] = { ...item, net_amount: net, vat_amount: vat, gross_amount: gross }
      return updated
    })
  }

  const addItem = () => setItems(prev => [...prev, emptyItem()])
  const removeItem = (idx: number) => setItems(prev => prev.filter((_, i) => i !== idx))

  const totals = items.reduce((acc, item) => ({
    net: acc.net + item.net_amount,
    vat: acc.vat + item.vat_amount,
    gross: acc.gross + item.gross_amount,
  }), { net: 0, vat: 0, gross: 0 })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    const payload = {
      type,
      contractor_id: contractorId || null,
      issue_date: issueDate,
      sale_date: saleDate || null,
      due_date: dueDate || null,
      notes: notes || null,
      currency,
      source: attachmentPath ? 'ocr' : 'manual',
      cost_type: type === 'zakup' && costType ? costType : null,
      attachment_path: attachmentPath || null,
      attachment_filename: attachmentFilename || null,
      items: items.map((item, i) => ({
        name: item.name,
        quantity: parseFloat(item.quantity) || 0,
        unit: item.unit,
        unit_price_net: parseFloat(item.unit_price_net) || 0,
        vat_rate: item.vat_rate,
        position_order: i + 1,
      })),
    }
    mutation.mutate(payload)
  }

  const contractors = contractorsData?.items || []

  return (
    <div className="max-w-5xl space-y-6">
      <div className="flex items-center gap-4">
        <Link to="/faktury" className="flex items-center gap-1 text-gray-500 hover:text-gray-700 text-sm">
          <ArrowLeft size={16} /> Powrót
        </Link>
        <h1 className="text-2xl font-bold text-gray-900">
          {isEdit ? 'Edytuj fakturę' : 'Nowa faktura'}
        </h1>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">{error}</div>
      )}

      {/* OCR Upload Section */}
      <div className="card border-2 border-dashed border-blue-200 bg-blue-50/30">
        <div className="flex items-start gap-4">
          <div className="flex-1">
            <h2 className="font-semibold text-gray-700 mb-1 flex items-center gap-2">
              <Upload size={16} className="text-blue-500" />
              Wczytaj fakturę ze zdjęcia lub PDF
            </h2>
            <p className="text-xs text-gray-500 mb-3">
              Prześlij skan, zdjęcie lub PDF faktury — aplikacja rozpozna tekst i wstępnie wypełni formularz.
              Oryginalny plik zostanie zapisany jako załącznik.
            </p>
            <div className="flex items-center gap-3">
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.jpg,.jpeg,.png,.tiff,.tif,.webp,.bmp"
                onChange={handleOcrUpload}
                className="hidden"
                id="ocr-upload"
                disabled={ocrLoading}
              />
              <label
                htmlFor="ocr-upload"
                className={`btn-secondary cursor-pointer flex items-center gap-2 ${ocrLoading ? 'opacity-50 pointer-events-none' : ''}`}
              >
                {ocrLoading ? <Loader2 size={15} className="animate-spin" /> : <Upload size={15} />}
                {ocrLoading ? 'Rozpoznaję...' : 'Wybierz plik'}
              </label>
              {attachmentFilename && (
                <div className="flex items-center gap-2 text-sm text-green-700 bg-green-50 border border-green-200 rounded-lg px-3 py-1.5">
                  <FileText size={14} />
                  <span className="truncate max-w-48">{attachmentFilename}</span>
                  <button
                    type="button"
                    onClick={() => { setAttachmentPath(''); setAttachmentFilename('') }}
                    className="text-gray-400 hover:text-red-500 ml-1"
                  >
                    <X size={13} />
                  </button>
                </div>
              )}
            </div>
            {ocrMsg && (
              <p className={`mt-2 text-xs rounded-lg px-3 py-2 ${ocrMsg.type === 'ok' ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-600 border border-red-200'}`}>
                {ocrMsg.text}
              </p>
            )}
          </div>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="card">
          <h2 className="font-semibold text-gray-700 mb-4">Informacje podstawowe</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Typ dokumentu</label>
              <select value={type} onChange={e => setType(e.target.value)} className="input-field">
                {INVOICE_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Waluta</label>
              <select value={currency} onChange={e => setCurrency(e.target.value)} className="input-field">
                <option value="PLN">PLN</option>
                <option value="EUR">EUR</option>
                <option value="USD">USD</option>
              </select>
            </div>
            {type === 'zakup' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Rodzaj kosztu
                  <span className="ml-1 text-xs text-gray-400">(faktury kosztowe)</span>
                </label>
                <select value={costType} onChange={e => setCostType(e.target.value)} className="input-field">
                  <option value="">— nie określono —</option>
                  <option value="towar">Towar</option>
                  <option value="usluga">Usługa</option>
                </select>
              </div>
            )}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Data wystawienia</label>
              <input type="date" value={issueDate} onChange={e => setIssueDate(e.target.value)} required className="input-field" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Data sprzedaży</label>
              <input type="date" value={saleDate} onChange={e => setSaleDate(e.target.value)} className="input-field" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Termin płatności</label>
              <input type="date" value={dueDate} onChange={e => setDueDate(e.target.value)} className="input-field" />
            </div>
          </div>
        </div>

        <div className="card">
          <h2 className="font-semibold text-gray-700 mb-4">Kontrahent</h2>
          <div className="mb-3">
            <input
              type="text"
              placeholder="Wyszukaj kontrahenta (nazwa, NIP)..."
              value={contractorSearch}
              onChange={e => setContractorSearch(e.target.value)}
              className="input-field"
            />
          </div>
          <select
            value={contractorId}
            onChange={e => setContractorId(e.target.value)}
            className="input-field"
          >
            <option value="">-- Wybierz kontrahenta --</option>
            {contractors.map((c: Record<string, unknown>) => (
              <option key={c.id as string} value={c.id as string}>
                {c.name as string} {c.nip ? `(NIP: ${c.nip})` : ''}
              </option>
            ))}
          </select>
        </div>

        <div className="card p-0 overflow-hidden">
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
            <h2 className="font-semibold text-gray-700">Pozycje faktury</h2>
            <button type="button" onClick={addItem} className="btn-secondary text-xs py-1.5">
              <Plus size={14} /> Dodaj pozycję
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="table-header" style={{ minWidth: 200 }}>Nazwa</th>
                  <th className="table-header" style={{ minWidth: 80 }}>Jm.</th>
                  <th className="table-header" style={{ minWidth: 80 }}>Ilość</th>
                  <th className="table-header" style={{ minWidth: 120 }}>Cena netto</th>
                  <th className="table-header" style={{ minWidth: 90 }}>VAT</th>
                  <th className="table-header text-right" style={{ minWidth: 110 }}>Netto</th>
                  <th className="table-header text-right" style={{ minWidth: 110 }}>VAT</th>
                  <th className="table-header text-right" style={{ minWidth: 110 }}>Brutto</th>
                  <th className="table-header" style={{ minWidth: 40 }}></th>
                </tr>
              </thead>
              <tbody>
                {items.map((item, idx) => (
                  <tr key={idx} className="border-b border-gray-50">
                    <td className="px-2 py-2">
                      <input value={item.name} onChange={e => updateItem(idx, 'name', e.target.value)} placeholder="Nazwa towaru/usługi" required className="input-field" />
                    </td>
                    <td className="px-2 py-2">
                      <input value={item.unit} onChange={e => updateItem(idx, 'unit', e.target.value)} className="input-field" />
                    </td>
                    <td className="px-2 py-2">
                      <input type="number" step="0.0001" min="0" value={item.quantity} onChange={e => updateItem(idx, 'quantity', e.target.value)} required className="input-field" />
                    </td>
                    <td className="px-2 py-2">
                      <input type="number" step="0.01" min="0" value={item.unit_price_net} onChange={e => updateItem(idx, 'unit_price_net', e.target.value)} required className="input-field" />
                    </td>
                    <td className="px-2 py-2">
                      <select value={item.vat_rate} onChange={e => updateItem(idx, 'vat_rate', e.target.value)} className="input-field">
                        {VAT_RATES.map(r => <option key={r} value={r}>{r}%</option>)}
                      </select>
                    </td>
                    <td className="px-2 py-2 text-right text-sm font-medium text-gray-700">{formatCurrency(item.net_amount)}</td>
                    <td className="px-2 py-2 text-right text-sm text-gray-500">{formatCurrency(item.vat_amount)}</td>
                    <td className="px-2 py-2 text-right text-sm font-semibold">{formatCurrency(item.gross_amount)}</td>
                    <td className="px-2 py-2">
                      {items.length > 1 && (
                        <button type="button" onClick={() => removeItem(idx)} className="text-red-400 hover:text-red-600 p-1">
                          <Trash2 size={15} />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot className="bg-blue-50 border-t-2 border-blue-200">
                <tr>
                  <td colSpan={5} className="px-4 py-3 font-semibold text-right text-gray-700">RAZEM:</td>
                  <td className="px-4 py-3 text-right font-semibold">{formatCurrency(totals.net)}</td>
                  <td className="px-4 py-3 text-right font-semibold">{formatCurrency(totals.vat)}</td>
                  <td className="px-4 py-3 text-right font-bold text-blue-700">{formatCurrency(totals.gross)}</td>
                  <td></td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>

        <div className="card">
          <h2 className="font-semibold text-gray-700 mb-3">Uwagi</h2>
          <textarea
            value={notes}
            onChange={e => setNotes(e.target.value)}
            rows={3}
            placeholder="Opcjonalne notatki do faktury..."
            className="input-field"
          />
        </div>

        <div className="flex items-center justify-end gap-3">
          <Link to="/faktury" className="btn-secondary">Anuluj</Link>
          <button type="submit" disabled={mutation.isPending} className="btn-primary">
            <Save size={16} />
            {mutation.isPending ? 'Zapisywanie...' : (isEdit ? 'Zapisz zmiany' : 'Utwórz fakturę')}
          </button>
        </div>
      </form>
    </div>
  )
}
