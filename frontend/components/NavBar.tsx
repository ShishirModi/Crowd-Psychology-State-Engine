'use client'

import { useRouter } from 'next/navigation'
import { logout } from '@/lib/api'
import Link from 'next/link'

export default function NavBar() {
  const router = useRouter()

  async function handleLogout() {
    try { await logout() } catch {}
    localStorage.removeItem('cpse_user')
    router.push('/login')
  }

  return (
    <nav className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between">
      <div className="flex items-center gap-6">
        <span className="font-bold text-slate-800 text-sm tracking-wide">CPSE</span>
        <Link href="/dashboard" className="text-sm text-slate-600 hover:text-slate-800">
          Dashboard
        </Link>
        <Link href="/history" className="text-sm text-slate-600 hover:text-slate-800">
          History
        </Link>
      </div>
      <button
        onClick={handleLogout}
        className="text-xs text-slate-500 hover:text-slate-800 transition-colors"
      >
        Sign out
      </button>
    </nav>
  )
}
