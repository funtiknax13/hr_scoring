import { FormEvent, useState } from 'react'
import { ChevronDown, ChevronUp, ExternalLink } from 'lucide-react'
import client from '../api/client'
import { SessionDetailOut, SessionOut, VacancyWithSnapshot } from '../api/types'

function fmt(v: number | null | undefined): string {
  if (v == null || v === 0) return ''
  return v.toLocaleString('ru')
}

function salary(v: VacancyWithSnapshot): string {
  const s = v.latest
  if (!s) return '—'
  const from = fmt(s.salary_from)
  const to = fmt(s.salary_to)
  const cur = s.currency ?? ''
  if (from && to) return `${from} – ${to} ${cur}`
  if (from) return `от ${from} ${cur}`
  if (to) return `до ${to} ${cur}`
  return '—'
}

function SessionRow({ session }: { session: SessionOut }) {
  const [expanded, setExpanded] = useState(false)
  const [detail, setDetail] = useState<SessionDetailOut | null>(null)
  const [loading, setLoading] = useState(false)

  async function toggle() {
    if (!expanded && !detail) {
      setLoading(true)
      try {
        const r = await client.get<SessionDetailOut>(`/api/vacancies/sessions/${session.id}`)
        setDetail(r.data)
      } finally {
        setLoading(false)
      }
    }
    setExpanded((v) => !v)
  }

  return (
    <>
      <tr
        className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer transition-colors"
        onClick={toggle}
      >
        <td className="py-3 px-4 text-sm font-medium text-gray-900">{session.query}</td>
        <td className="py-3 px-4 text-xs text-gray-500 hidden sm:table-cell">{session.city ?? 'Вся Россия'}</td>
        <td className="py-3 px-4 text-sm text-gray-700">{session.count}</td>
        <td className="py-3 px-4 text-xs text-gray-400 hidden md:table-cell">
          {new Date(session.fetched_at).toLocaleString('ru')}
        </td>
        <td className="py-3 px-4 text-gray-400 w-6">
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </td>
      </tr>
      {expanded && (
        <tr className="bg-gray-50">
          <td colSpan={5} className="px-4 pb-4 pt-1">
            {loading && <p className="text-xs text-gray-400 py-2">Загрузка…</p>}
            {detail && detail.vacancies.length > 0 && (
              <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-100 text-xs text-gray-400">
                      <th className="py-2 px-3 text-left">Название</th>
                      <th className="py-2 px-3 text-left hidden sm:table-cell">Локация</th>
                      <th className="py-2 px-3 text-left">Зарплата</th>
                      <th className="py-2 px-3 w-6" />
                    </tr>
                  </thead>
                  <tbody>
                    {detail.vacancies.map((v) => (
                      <tr key={v.id} className="border-b border-gray-50">
                        <td className="py-2 px-3 font-medium text-gray-900 max-w-[200px] truncate">{v.title}</td>
                        <td className="py-2 px-3 text-gray-500 hidden sm:table-cell">{v.location ?? '—'}</td>
                        <td className="py-2 px-3 text-gray-700 whitespace-nowrap">{salary(v)}</td>
                        <td className="py-2 px-3">
                          {v.url && (
                            <a href={v.url} target="_blank" rel="noopener noreferrer"
                              className="text-indigo-500 hover:text-indigo-700"
                              onClick={(e) => e.stopPropagation()}>
                              <ExternalLink size={14} />
                            </a>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {detail && detail.vacancies.length === 0 && (
              <p className="text-xs text-gray-400 py-2">Нет вакансий в этой сессии</p>
            )}
          </td>
        </tr>
      )}
    </>
  )
}

export default function VacanciesPage() {
  const [source, setSource] = useState<'hh' | 'sj'>('hh')
  const [query, setQuery] = useState('')
  const [city, setCity] = useState('')
  const [maxPages, setMaxPages] = useState(3)
  const [searching, setSearching] = useState(false)
  const [error, setError] = useState('')
  const [sessions, setSessions] = useState<SessionOut[]>([])
  const [loaded, setLoaded] = useState(false)

  async function loadSessions() {
    const r = await client.get<SessionOut[]>(`/api/vacancies/sessions?source=${source}`)
    setSessions(r.data)
    setLoaded(true)
  }

  async function handleSearch(e: FormEvent) {
    e.preventDefault()
    setError('')
    setSearching(true)
    try {
      await client.post(`/api/vacancies/${source}`, {
        query,
        city: city || null,
        max_pages: maxPages,
      })
      await loadSessions()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(msg ?? 'Ошибка при выгрузке')
    } finally {
      setSearching(false)
    }
  }

  function handleSourceChange(s: 'hh' | 'sj') {
    setSource(s)
    setLoaded(false)
    setSessions([])
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <h1 className="text-xl font-bold text-gray-900">Вакансии</h1>

      {/* Source tabs */}
      <div className="flex gap-1 bg-gray-100 rounded-xl p-1 w-fit">
        {(['hh', 'sj'] as const).map((s) => (
          <button
            key={s}
            onClick={() => handleSourceChange(s)}
            className={`px-5 py-2 rounded-lg text-sm font-medium transition-colors ${
              source === s ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {s === 'hh' ? 'HeadHunter' : 'SuperJob'}
          </button>
        ))}
      </div>

      {/* Search form */}
      <form onSubmit={handleSearch} className="bg-white rounded-2xl border border-gray-200 p-5 space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Запрос</label>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Python-разработчик"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {source === 'hh' ? 'Город (необязательно)' : 'Город (необязательно)'}
            </label>
            <input
              type="text"
              value={city}
              onChange={(e) => setCity(e.target.value)}
              placeholder={source === 'hh' ? 'Москва' : 'Москва'}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>
        </div>
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-600">Страниц:</label>
            <input
              type="number"
              min={1}
              max={20}
              value={maxPages}
              onChange={(e) => setMaxPages(Number(e.target.value))}
              className="w-16 px-2 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            <span className="text-xs text-gray-400">× 100 вакансий</span>
          </div>
          <button
            type="submit"
            disabled={!query || searching}
            className="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-300 text-white font-medium rounded-lg text-sm transition-colors"
          >
            {searching ? 'Выгрузка…' : 'Выгрузить'}
          </button>
          {!loaded && (
            <button
              type="button"
              onClick={loadSessions}
              className="px-4 py-2 border border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-gray-50 transition-colors"
            >
              Показать историю
            </button>
          )}
        </div>
        {error && <p className="text-sm text-red-500">{error}</p>}
        {searching && (
          <p className="text-xs text-gray-400 animate-pulse">
            Идёт выгрузка — это может занять до {maxPages * 5} секунд…
          </p>
        )}
      </form>

      {/* Sessions */}
      {loaded && (
        <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-700">
              История выгрузок {source === 'hh' ? 'HeadHunter' : 'SuperJob'}
            </h2>
            <span className="text-xs text-gray-400">{sessions.length} сессий</span>
          </div>
          {sessions.length === 0 ? (
            <p className="px-5 py-8 text-sm text-gray-400 text-center">Нет выгрузок для этого источника</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-100 text-xs text-gray-400 uppercase tracking-wide">
                    <th className="py-3 px-4 text-left">Запрос</th>
                    <th className="py-3 px-4 text-left hidden sm:table-cell">Город</th>
                    <th className="py-3 px-4 text-left">Найдено</th>
                    <th className="py-3 px-4 text-left hidden md:table-cell">Дата</th>
                    <th className="w-6" />
                  </tr>
                </thead>
                <tbody>
                  {sessions.map((s) => <SessionRow key={s.id} session={s} />)}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
