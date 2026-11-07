import { createContext, useContext, useEffect, useState } from 'react'
import { setCsrfToken, storeApi } from '../services/api'

const AuthContext = createContext(null)
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null); const [loading, setLoading] = useState(true)
  useEffect(() => { storeApi.me().then((r) => { setUser(r.user); setCsrfToken(r.csrf_token) }).catch(() => {}).finally(() => setLoading(false)) }, [])
  async function authenticate(kind, data) { const r = await storeApi[kind](data); setUser(r.user); setCsrfToken(r.csrf_token); return r }
  async function logout() { await storeApi.logout(); setUser(null); setCsrfToken('') }
  return <AuthContext.Provider value={{ user, loading, login: (d) => authenticate('login', d), register: (d) => authenticate('register', d), logout }}>{children}</AuthContext.Provider>
}
export const useAuth = () => useContext(AuthContext)
