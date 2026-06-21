import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import client from '../api/client'
import { UserMe } from '../api/types'

interface AuthCtx {
  user: UserMe | null
  loading: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
}

const Ctx = createContext<AuthCtx | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserMe | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) { setLoading(false); return }
    client.get<UserMe>('/api/auth/me')
      .then((r) => setUser(r.data))
      .catch(() => localStorage.removeItem('token'))
      .finally(() => setLoading(false))
  }, [])

  async function login(username: string, password: string) {
    const r = await client.post<{ access_token: string }>('/api/auth/login', { username, password })
    localStorage.setItem('token', r.data.access_token)
    const me = await client.get<UserMe>('/api/auth/me')
    setUser(me.data)
  }

  function logout() {
    localStorage.removeItem('token')
    setUser(null)
  }

  return <Ctx.Provider value={{ user, loading, login, logout }}>{children}</Ctx.Provider>
}

export function useAuth() {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useAuth must be inside AuthProvider')
  return ctx
}
