export const formatCurrency = (value: number): string => {
  return new Intl.NumberFormat('pl-PL', {
    style: 'currency',
    currency: 'PLN',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)
}

export const formatDate = (dateStr: string | null | undefined): string => {
  if (!dateStr) return '-'
  try {
    const d = new Date(dateStr)
    return d.toLocaleDateString('pl-PL', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    })
  } catch {
    return dateStr
  }
}

export const MONTH_NAMES = [
  'Sty', 'Lut', 'Mar', 'Kwi', 'Maj', 'Cze',
  'Lip', 'Sie', 'Wrz', 'Paź', 'Lis', 'Gru'
]

export const MONTH_NAMES_FULL = [
  'Styczeń', 'Luty', 'Marzec', 'Kwiecień', 'Maj', 'Czerwiec',
  'Lipiec', 'Sierpień', 'Wrzesień', 'Październik', 'Listopad', 'Grudzień'
]

export const validateNIP = (nip: string): boolean => {
  const cleaned = nip.replace(/[\s-]/g, '')
  if (!/^\d{10}$/.test(cleaned)) return false
  const weights = [6, 5, 7, 2, 3, 4, 5, 6, 7, 8]
  const digits = cleaned.split('').map(Number)
  const sum = weights.reduce((acc, w, i) => acc + w * digits[i], 0)
  return sum % 11 === digits[9]
}
