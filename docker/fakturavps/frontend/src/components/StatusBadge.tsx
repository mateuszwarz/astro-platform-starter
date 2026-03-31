import { InvoiceStatus } from '../types'
import { clsx } from 'clsx'

interface StatusBadgeProps {
  status: InvoiceStatus | string
}

const statusConfig: Record<string, { label: string; className: string }> = {
  szkic: { label: 'Szkic', className: 'bg-gray-100 text-gray-700' },
  oczekuje: { label: 'Oczekuje', className: 'bg-blue-100 text-blue-700' },
  czesciowo_zaplacona: { label: 'Częściowo zapłacona', className: 'bg-yellow-100 text-yellow-700' },
  zaplacona: { label: 'Zapłacona', className: 'bg-green-100 text-green-700' },
  przeterminowana: { label: 'Przeterminowana', className: 'bg-red-100 text-red-700' },
  anulowana: { label: 'Anulowana', className: 'bg-gray-100 text-gray-500 line-through' },
  w_ksef: { label: 'W KSeF', className: 'bg-orange-100 text-orange-700' },
  zaakceptowana_ksef: { label: 'Zaakceptowana (KSeF)', className: 'bg-emerald-100 text-emerald-800' },
  odrzucona_ksef: { label: 'Odrzucona (KSeF)', className: 'bg-red-100 text-red-900' },
}

export const StatusBadge = ({ status }: StatusBadgeProps) => {
  const config = statusConfig[status] ?? { label: status, className: 'bg-gray-100 text-gray-700' }
  return (
    <span className={clsx('inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium', config.className)}>
      {config.label}
    </span>
  )
}
