import { InvoiceType } from '../types'

interface InvoiceTypeLabelProps {
  type: InvoiceType | string
}

const typeLabels: Record<string, string> = {
  sprzedaz: 'Sprzedaż',
  zakup: 'Zakup',
  korekta: 'Korekta',
  zaliczkowa: 'Zaliczkowa',
  proforma: 'Pro Forma',
  paragon: 'Paragon',
}

export const InvoiceTypeLabel = ({ type }: InvoiceTypeLabelProps) => {
  return <span>{typeLabels[type] ?? type}</span>
}
