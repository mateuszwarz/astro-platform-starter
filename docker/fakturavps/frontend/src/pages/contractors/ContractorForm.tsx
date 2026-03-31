import { useEffect, useState } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { getContractor, createContractor, updateContractor } from '../../api/contractors'
import { validateNIP } from '../../utils/format'
import { ArrowLeft, Save, CheckCircle, XCircle } from 'lucide-react'

export default function ContractorForm() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const isEdit = Boolean(id)

  const [nip, setNip] = useState('')
  const [nipValid, setNipValid] = useState<boolean | null>(null)
  const [name, setName] = useState('')
  const [regon, setRegon] = useState('')
  const [address, setAddress] = useState('')
  const [postalCode, setPostalCode] = useState('')
  const [city, setCity] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [bankAccount, setBankAccount] = useState('')
  const [defaultPaymentDays, setDefaultPaymentDays] = useState('14')
  const [category, setCategory] = useState('klient')
  const [status, setStatus] = useState('aktywny')
  const [notes, setNotes] = useState('')
  const [error, setError] = useState('')

  const { data } = useQuery({
    queryKey: ['contractor', id],
    queryFn: () => getContractor(id!),
    enabled: isEdit,
  })

  useEffect(() => {
    if (data?.contractor && isEdit) {
      const c = data.contractor
      setNip(c.nip || '')
      setName(c.name || '')
      setRegon(c.regon || '')
      setAddress(c.address || '')
      setPostalCode(c.postal_code || '')
      setCity(c.city || '')
      setEmail(c.email || '')
      setPhone(c.phone || '')
      setBankAccount(c.bank_account || '')
      setDefaultPaymentDays(String(c.default_payment_days || 14))
      setCategory(c.category || 'klient')
      setStatus(c.status || 'aktywny')
      setNotes(c.notes || '')
    }
  }, [data, isEdit])

  const verifyNip = () => {
    const valid = validateNIP(nip)
    setNipValid(valid)
  }

  const mutation = useMutation({
    mutationFn: (payload: unknown) => isEdit ? updateContractor(id!, payload) : createContractor(payload),
    onSuccess: () => navigate('/kontrahenci'),
    onError: (e: unknown) => setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Błąd zapisu'),
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    mutation.mutate({
      nip: nip || null,
      name,
      regon: regon || null,
      address: address || null,
      postal_code: postalCode || null,
      city: city || null,
      email: email || null,
      phone: phone || null,
      bank_account: bankAccount || null,
      default_payment_days: parseInt(defaultPaymentDays) || 14,
      category,
      status,
      notes: notes || null,
    })
  }

  return (
    <div className="max-w-2xl space-y-6">
      <div className="flex items-center gap-4">
        <Link to="/kontrahenci" className="flex items-center gap-1 text-gray-500 hover:text-gray-700 text-sm">
          <ArrowLeft size={16} /> Powrót
        </Link>
        <h1 className="text-2xl font-bold text-gray-900">
          {isEdit ? 'Edytuj kontrahenta' : 'Nowy kontrahent'}
        </h1>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">{error}</div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="card space-y-4">
          <h2 className="font-semibold text-gray-700">Dane identyfikacyjne</h2>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">NIP</label>
            <div className="flex gap-2">
              <input type="text" value={nip} onChange={e => { setNip(e.target.value); setNipValid(null) }} placeholder="1234567890" className="input-field flex-1" />
              <button type="button" onClick={verifyNip} className="btn-secondary shrink-0">
                Weryfikuj NIP
              </button>
            </div>
            {nipValid === true && (
              <p className="text-green-600 text-xs mt-1 flex items-center gap-1"><CheckCircle size={12} /> NIP prawidłowy</p>
            )}
            {nipValid === false && (
              <p className="text-red-600 text-xs mt-1 flex items-center gap-1"><XCircle size={12} /> Nieprawidłowy NIP</p>
            )}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nazwa *</label>
            <input type="text" value={name} onChange={e => setName(e.target.value)} required className="input-field" placeholder="Nazwa firmy lub imię i nazwisko" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">REGON</label>
            <input type="text" value={regon} onChange={e => setRegon(e.target.value)} className="input-field" placeholder="123456789" />
          </div>
        </div>

        <div className="card space-y-4">
          <h2 className="font-semibold text-gray-700">Adres</h2>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Ulica i numer</label>
            <input type="text" value={address} onChange={e => setAddress(e.target.value)} className="input-field" placeholder="ul. Przykładowa 1/2" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Kod pocztowy</label>
              <input type="text" value={postalCode} onChange={e => setPostalCode(e.target.value)} className="input-field" placeholder="00-001" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Miasto</label>
              <input type="text" value={city} onChange={e => setCity(e.target.value)} className="input-field" placeholder="Warszawa" />
            </div>
          </div>
        </div>

        <div className="card space-y-4">
          <h2 className="font-semibold text-gray-700">Dane kontaktowe</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <input type="email" value={email} onChange={e => setEmail(e.target.value)} className="input-field" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Telefon</label>
              <input type="text" value={phone} onChange={e => setPhone(e.target.value)} className="input-field" />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Numer konta bankowego</label>
            <input type="text" value={bankAccount} onChange={e => setBankAccount(e.target.value)} className="input-field" placeholder="PL00 0000 0000 0000 0000 0000 0000" />
          </div>
        </div>

        <div className="card space-y-4">
          <h2 className="font-semibold text-gray-700">Ustawienia</h2>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Domyślny termin płatności (dni)</label>
              <input type="number" min="0" max="365" value={defaultPaymentDays} onChange={e => setDefaultPaymentDays(e.target.value)} className="input-field" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Kategoria</label>
              <select value={category} onChange={e => setCategory(e.target.value)} className="input-field">
                <option value="klient">Klient</option>
                <option value="dostawca">Dostawca</option>
                <option value="oba">Klient/Dostawca</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
              <select value={status} onChange={e => setStatus(e.target.value)} className="input-field">
                <option value="aktywny">Aktywny</option>
                <option value="nieaktywny">Nieaktywny</option>
                <option value="ryzykowny">Ryzykowny</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Notatki</label>
            <textarea value={notes} onChange={e => setNotes(e.target.value)} rows={3} className="input-field" placeholder="Opcjonalne uwagi..." />
          </div>
        </div>

        <div className="flex items-center justify-end gap-3">
          <Link to="/kontrahenci" className="btn-secondary">Anuluj</Link>
          <button type="submit" disabled={mutation.isPending} className="btn-primary">
            <Save size={16} />
            {mutation.isPending ? 'Zapisywanie...' : (isEdit ? 'Zapisz zmiany' : 'Utwórz kontrahenta')}
          </button>
        </div>
      </form>
    </div>
  )
}
