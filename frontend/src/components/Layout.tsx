import { NavLink, useNavigate } from 'react-router-dom'
import { Brain, Briefcase, LogOut, Settings } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

const nav = [
  { to: '/scoring', icon: Brain, label: 'Скоринг' },
  { to: '/vacancies', icon: Briefcase, label: 'Вакансии' },
]

export default function Layout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <div className="flex min-h-screen">
      {/* Sidebar — desktop */}
      <aside className="hidden md:flex md:flex-col md:w-56 bg-white border-r border-gray-200 fixed h-full z-10">
        <div className="px-5 py-5 border-b border-gray-100">
          <span className="font-bold text-indigo-600 text-lg">HR Scoring</span>
          <p className="text-xs text-gray-400 mt-0.5 truncate">{user?.username} · {user?.role}</p>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1">
          {nav.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-indigo-50 text-indigo-700'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                }`
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
          {user?.role === 'admin' && (
            <a
              href="/admin"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-gray-600 hover:bg-gray-50 hover:text-gray-900"
            >
              <Settings size={18} />
              Админка
            </a>
          )}
        </nav>
        <div className="px-3 py-4 border-t border-gray-100">
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm text-gray-600 hover:bg-red-50 hover:text-red-600 transition-colors"
          >
            <LogOut size={18} />
            Выйти
          </button>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 md:ml-56 flex flex-col min-h-screen">
        {/* Mobile header */}
        <header className="md:hidden bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between sticky top-0 z-10">
          <span className="font-bold text-indigo-600">HR Scoring</span>
          <span className="text-xs text-gray-400">{user?.username}</span>
        </header>

        <main className="flex-1 p-4 md:p-6 pb-20 md:pb-6">
          {children}
        </main>

        {/* Bottom nav — mobile */}
        <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 flex z-10">
          {nav.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex-1 flex flex-col items-center py-3 text-xs font-medium transition-colors ${
                  isActive ? 'text-indigo-600' : 'text-gray-500'
                }`
              }
            >
              <Icon size={20} />
              <span className="mt-0.5">{label}</span>
            </NavLink>
          ))}
          <button
            onClick={handleLogout}
            className="flex-1 flex flex-col items-center py-3 text-xs font-medium text-gray-500"
          >
            <LogOut size={20} />
            <span className="mt-0.5">Выйти</span>
          </button>
        </nav>
      </div>
    </div>
  )
}
