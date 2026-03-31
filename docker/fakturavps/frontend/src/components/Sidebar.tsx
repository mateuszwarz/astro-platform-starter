import { NavLink } from 'react-router-dom'
import { LayoutDashboard, FileText, Users, CreditCard, BarChart2, LogOut, Zap, Mail, Landmark } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { clsx } from 'clsx'

const navItems = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/faktury', icon: FileText, label: 'Faktury' },
  { to: '/kontrahenci', icon: Users, label: 'Kontrahenci' },
  { to: '/platnosci', icon: CreditCard, label: 'Płatności' },
  { to: '/wyciagi', icon: Landmark, label: 'Wyciągi bankowe' },
  { to: '/raporty', icon: BarChart2, label: 'Raporty' },
  { to: '/poczta', icon: Mail, label: 'Poczta' },
]

const roleLabels: Record<string, string> = {
  admin: 'Administrator',
  wlasciciel: 'Właściciel',
  ksiegowy: 'Księgowy',
  pracownik: 'Pracownik',
  audytor: 'Audytor',
}

export const Sidebar = () => {
  const { user, logout } = useAuth()

  return (
    <aside className="fixed inset-y-0 left-0 w-64 bg-slate-900 text-white flex flex-col z-10">
      <div className="flex items-center gap-3 px-6 py-5 border-b border-slate-700">
        <div className="w-9 h-9 bg-blue-600 rounded-lg flex items-center justify-center">
          <Zap size={20} className="text-white" />
        </div>
        <div>
          <h1 className="font-bold text-lg leading-tight">FakturaVPS</h1>
          <p className="text-slate-400 text-xs">System fakturowania</p>
        </div>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors text-sm font-medium',
                isActive
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-300 hover:bg-slate-800 hover:text-white'
              )
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="px-4 py-4 border-t border-slate-700">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-9 h-9 bg-slate-700 rounded-full flex items-center justify-center text-sm font-semibold">
            {user?.full_name?.charAt(0)?.toUpperCase() || 'U'}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{user?.full_name}</p>
            <p className="text-xs text-slate-400">{roleLabels[user?.role || ''] || user?.role}</p>
          </div>
        </div>
        <button
          onClick={logout}
          className="flex items-center gap-2 w-full px-3 py-2 text-sm text-slate-300 hover:bg-slate-800 hover:text-white rounded-lg transition-colors"
        >
          <LogOut size={16} />
          Wyloguj
        </button>
      </div>
    </aside>
  )
}
