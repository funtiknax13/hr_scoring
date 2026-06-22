import { useEffect, useRef, useState } from 'react'
import { ArrowLeft, ChevronDown, ChevronUp, Upload, AlertTriangle, FlaskConical } from 'lucide-react'
import client from '../api/client'
import { useAuth } from '../context/AuthContext'
import {
  CandidateResultOut, CriterionScore, Rubric,
  ScoringJobDetailOut, ScoringJobOut, ScoringOutput, ResumeProfile, ScoringVacancyOut,
} from '../api/types'

const STATUS_LABEL: Record<string, string> = {
  pending: 'В очереди', running: 'Обработка', done: 'Готово', error: 'Ошибка',
}
const STATUS_COLOR: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-700',
  running: 'bg-blue-100 text-blue-700',
  done: 'bg-green-100 text-green-700',
  error: 'bg-red-100 text-red-700',
}

function Badge({ status }: { status: string }) {
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLOR[status] ?? 'bg-gray-100 text-gray-600'}`}>
      {STATUS_LABEL[status] ?? status}
    </span>
  )
}

function ScoreBar({ score }: { score: number }) {
  const pct = Math.round(score)
  const color = pct >= 70 ? 'bg-green-500' : pct >= 45 ? 'bg-yellow-500' : 'bg-red-400'
  return (
    <div className="flex items-center gap-2 min-w-0">
      <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden min-w-[60px]">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-sm font-semibold tabular-nums w-8 text-right">{pct}</span>
    </div>
  )
}

function EvalResults({ job }: { job: ScoringJobDetailOut }) {
  if (!job.is_eval || job.status !== 'done') return null

  const expected: Record<string, number> = job.expected_scores ? JSON.parse(job.expected_scores) : {}
  if (Object.keys(expected).length === 0) return null

  // Строим таблицу: для каждого файла с эталоном — ожидаемый и реальный балл
  const rows = job.results
    .filter((r) => r.candidate_filename in expected && r.total_score != null)
    .sort((a, b) => expected[b.candidate_filename] - expected[a.candidate_filename])

  const tau = job.eval_tau
  const tauColor = tau == null ? 'text-gray-400' : tau >= 0.8 ? 'text-green-600' : tau >= 0.5 ? 'text-yellow-600' : 'text-red-500'

  // Ранги по ожидаемым и реальным баллам
  const byActual = [...rows].sort((a, b) => (b.total_score ?? 0) - (a.total_score ?? 0))
  const actualRank: Record<number, number> = {}
  byActual.forEach((r, i) => { actualRank[r.candidate_id] = i + 1 })

  const byExpected = [...rows].sort((a, b) => expected[b.candidate_filename] - expected[a.candidate_filename])
  const expectedRank: Record<number, number> = {}
  byExpected.forEach((r, i) => { expectedRank[r.candidate_id] = i + 1 })

  return (
    <div className="bg-white rounded-2xl border border-indigo-200 p-5 mb-4">
      <div className="flex items-center gap-2 mb-3">
        <FlaskConical size={16} className="text-indigo-500" />
        <p className="text-sm font-semibold text-indigo-700">Результаты тестирования</p>
        {tau != null && (
          <span className={`ml-auto text-sm font-bold ${tauColor}`}>
            τ = {tau.toFixed(2)}
            <span className="text-xs font-normal text-gray-400 ml-1">
              {tau >= 0.8 ? '— отлично' : tau >= 0.5 ? '— есть расхождения' : '— ранжирование нарушено'}
            </span>
          </span>
        )}
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-xs text-gray-400 uppercase tracking-wide border-b border-gray-100">
            <th className="pb-2 text-left">Кандидат</th>
            <th className="pb-2 text-center">Ожидалось</th>
            <th className="pb-2 text-center">Получено</th>
            <th className="pb-2 text-center">Ранг ожид.</th>
            <th className="pb-2 text-center">Ранг факт.</th>
            <th className="pb-2 text-center"></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const exp = expected[r.candidate_filename]
            const act = Math.round(r.total_score ?? 0)
            const er = expectedRank[r.candidate_id]
            const ar = actualRank[r.candidate_id]
            const match = er === ar
            return (
              <tr key={r.id} className="border-b border-gray-50">
                <td className="py-2 text-gray-700 truncate max-w-[160px]">
                  {r.candidate_name ?? r.candidate_filename}
                </td>
                <td className="py-2 text-center text-gray-500">{exp}</td>
                <td className="py-2 text-center font-semibold text-gray-900">{act}</td>
                <td className="py-2 text-center text-gray-400">#{er}</td>
                <td className="py-2 text-center text-gray-400">#{ar}</td>
                <td className="py-2 text-center text-lg">
                  {match ? '✓' : ar < er ? '↑' : '↓'}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function CandidateDetail({ result }: { result: CandidateResultOut }) {
  const profile: ResumeProfile | null = result.profile_json ? JSON.parse(result.profile_json) : null
  const scoring: ScoringOutput | null = result.result_json ? JSON.parse(result.result_json) : null

  return (
    <div className="mt-3 pt-3 border-t border-gray-100 space-y-4 text-sm">
      {profile && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1">Профиль</p>
            {profile.total_years_experience != null && (
              <p className="text-gray-700">Опыт: <span className="font-medium">{profile.total_years_experience} лет</span></p>
            )}
            {profile.summary && <p className="text-gray-600 mt-1">{profile.summary}</p>}
          </div>
          {profile.skills.length > 0 && (
            <div>
              <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1">Навыки</p>
              <div className="flex flex-wrap gap-1">
                {profile.skills.map((s) => (
                  <span key={s} className="px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded text-xs">{s}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {scoring && (
        <>
          <div>
            <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-2">Оценка по критериям</p>
            <div className="space-y-2">
              {scoring.criterion_scores.map((c: CriterionScore) => (
                <div key={c.name} className="bg-gray-50 rounded-lg p-3">
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <span className="font-medium text-gray-800 text-xs">{c.name}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gray-400">увер. {Math.round(c.confidence * 100)}%</span>
                      <span className="font-bold text-gray-900 text-sm">{c.score}/10</span>
                    </div>
                  </div>
                  {c.evidence && (
                    <p className="mt-1 text-xs text-gray-500 italic border-l-2 border-indigo-200 pl-2">«{c.evidence}»</p>
                  )}
                  {c.reasoning && <p className="mt-1 text-xs text-gray-600">{c.reasoning}</p>}
                  {c.insufficient_evidence && (
                    <p className="mt-1 text-xs text-amber-600">⚠ Недостаточно данных для оценки</p>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {scoring.strengths.length > 0 && (
              <div>
                <p className="text-xs font-medium text-green-600 mb-1">✓ Сильные стороны</p>
                <ul className="space-y-0.5">{scoring.strengths.map((s, i) => <li key={i} className="text-xs text-gray-600">• {s}</li>)}</ul>
              </div>
            )}
            {scoring.gaps.length > 0 && (
              <div>
                <p className="text-xs font-medium text-orange-600 mb-1">△ Пробелы</p>
                <ul className="space-y-0.5">{scoring.gaps.map((s, i) => <li key={i} className="text-xs text-gray-600">• {s}</li>)}</ul>
              </div>
            )}
            {scoring.red_flags.length > 0 && (
              <div>
                <p className="text-xs font-medium text-red-600 mb-1">✗ Red flags</p>
                <ul className="space-y-0.5">{scoring.red_flags.map((s, i) => <li key={i} className="text-xs text-gray-600">• {s}</li>)}</ul>
              </div>
            )}
          </div>

          {scoring.overall_reasoning && (
            <div className="bg-indigo-50 rounded-lg p-3">
              <p className="text-xs font-medium text-indigo-700 mb-1">Вывод для рекрутёра</p>
              <p className="text-xs text-gray-700">{scoring.overall_reasoning}</p>
            </div>
          )}
        </>
      )}
    </div>
  )
}

function CandidateRow({ result, rank }: { result: CandidateResultOut; rank: number }) {
  const [expanded, setExpanded] = useState(false)
  const canExpand = result.status === 'done' || result.status === 'skipped'

  return (
    <>
      <tr
        className={`border-b border-gray-100 ${canExpand ? 'cursor-pointer hover:bg-gray-50' : ''}`}
        onClick={() => canExpand && setExpanded((v) => !v)}
      >
        <td className="py-3 px-3 text-sm text-gray-400 w-8">{result.status === 'done' ? rank : '—'}</td>
        <td className="py-3 px-3">
          <p className="text-sm font-medium text-gray-900 truncate max-w-[150px] sm:max-w-xs">
            {result.candidate_name ?? result.candidate_filename}
          </p>
          {result.candidate_name && (
            <p className="text-xs text-gray-400 truncate max-w-[150px] sm:max-w-xs">{result.candidate_filename}</p>
          )}
        </td>
        <td className="py-3 px-3 min-w-[120px]">
          {result.total_score != null ? <ScoreBar score={result.total_score} /> : <span className="text-xs text-gray-400">—</span>}
        </td>
        <td className="py-3 px-3 text-xs text-gray-500 hidden sm:table-cell">
          {result.overall_confidence != null ? `${Math.round(result.overall_confidence * 100)}%` : '—'}
        </td>
        <td className="py-3 px-3">
          <div className="flex items-center gap-2">
            <Badge status={result.status} />
            {result.manipulation_attempt && <span title="Попытка манипуляции"><AlertTriangle size={14} className="text-red-500" /></span>}
          </div>
        </td>
        <td className="py-3 px-3 text-gray-400 w-6">
          {canExpand && (expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />)}
        </td>
      </tr>
      {expanded && (
        <tr className="bg-gray-50">
          <td colSpan={6} className="px-4 pb-4">
            <CandidateDetail result={result} />
          </td>
        </tr>
      )}
    </>
  )
}

function JobDetail({ job, onBack }: { job: ScoringJobDetailOut; onBack: () => void }) {
  const rubric: Rubric | null = job.rubric_json ? JSON.parse(job.rubric_json) : null
  const ranked = [...job.results].sort((a, b) => (b.total_score ?? -1) - (a.total_score ?? -1))
  let rank = 0

  return (
    <div>
      <button onClick={onBack} className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-800 mb-4 transition-colors">
        <ArrowLeft size={16} /> Назад к списку
      </button>

      <div className="bg-white rounded-2xl border border-gray-200 p-5 mb-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-semibold text-gray-900">{job.vacancy_title ?? job.vacancy_filename}</h2>
              {job.is_eval && (
                <span className="flex items-center gap-1 px-2 py-0.5 bg-indigo-100 text-indigo-600 rounded-full text-xs font-medium">
                  <FlaskConical size={11} /> eval
                </span>
              )}
            </div>
            <p className="text-xs text-gray-400 mt-0.5">{job.model_name} · {new Date(job.created_at).toLocaleString('ru')}</p>
          </div>
          <Badge status={job.status} />
        </div>
        {job.error_message && <p className="mt-3 text-sm text-red-600 bg-red-50 rounded-lg p-3">{job.error_message}</p>}
        <div className="flex gap-4 mt-3 text-sm text-gray-500">
          <span>Всего: <b className="text-gray-900">{job.total_candidates}</b></span>
          <span>Готово: <b className="text-gray-900">{job.done_candidates}</b></span>
          {job.skipped_candidates > 0 && <span>Из кэша: <b className="text-gray-900">{job.skipped_candidates}</b></span>}
        </div>
      </div>

      <EvalResults job={job} />

      {rubric && (
        <div className="bg-white rounded-2xl border border-gray-200 p-5 mb-4">
          <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-2">Рубрика</p>
          <div className="flex flex-wrap gap-2">
            {rubric.criteria.map((c) => (
              <span key={c.name} className="px-2 py-1 bg-gray-100 rounded text-xs text-gray-700">
                {c.name} <span className="text-gray-400">·{Math.round(c.weight * 100)}%</span>
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100 text-xs text-gray-400 uppercase tracking-wide">
                <th className="py-3 px-3 text-left w-8">#</th>
                <th className="py-3 px-3 text-left">Кандидат</th>
                <th className="py-3 px-3 text-left min-w-[120px]">Балл</th>
                <th className="py-3 px-3 text-left hidden sm:table-cell">Увер.</th>
                <th className="py-3 px-3 text-left">Статус</th>
                <th className="w-6" />
              </tr>
            </thead>
            <tbody>
              {ranked.map((r) => {
                if (r.status === 'done') rank++
                return <CandidateRow key={r.id} result={r} rank={rank} />
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export default function ScoringPage() {
  const { user } = useAuth()
  const canRun = user?.role !== 'analyst'
  const vacancyRef = useRef<HTMLInputElement>(null)
  const resumesRef = useRef<HTMLInputElement>(null)

  const [vacancyMode, setVacancyMode] = useState<'upload' | 'select'>('upload')
  const [vacancyFile, setVacancyFile] = useState<File | null>(null)
  const [existingVacancies, setExistingVacancies] = useState<ScoringVacancyOut[]>([])
  const [selectedVacancyId, setSelectedVacancyId] = useState<number | null>(null)

  const [resumeFiles, setResumeFiles] = useState<File[]>([])
  const [isEval, setIsEval] = useState(false)

  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [jobs, setJobs] = useState<ScoringJobOut[]>([])
  const [selectedJob, setSelectedJob] = useState<ScoringJobDetailOut | null>(null)
  const [view, setView] = useState<'list' | 'detail'>('list')

  useEffect(() => {
    loadJobs()
    loadVacancies()
  }, [])

  useEffect(() => {
    if (!selectedJob) return
    if (!['pending', 'running'].includes(selectedJob.status)) return
    const t = setInterval(() => loadJobDetail(selectedJob.id), 3000)
    return () => clearInterval(t)
  }, [selectedJob?.id, selectedJob?.status])

  async function loadJobs() {
    const r = await client.get<ScoringJobOut[]>('/api/scoring/jobs')
    setJobs(r.data)
  }

  async function loadVacancies() {
    const r = await client.get<ScoringVacancyOut[]>('/api/scoring/vacancies')
    setExistingVacancies(r.data)
  }

  async function loadJobDetail(id: number) {
    const r = await client.get<ScoringJobDetailOut>(`/api/scoring/jobs/${id}`)
    setSelectedJob(r.data)
    setJobs((prev) => prev.map((j) => (j.id === id ? r.data : j)))
  }

  async function handleSubmit() {
    const hasVacancy = vacancyMode === 'upload' ? !!vacancyFile : !!selectedVacancyId
    if (!hasVacancy || resumeFiles.length === 0) return
    setError('')
    setSubmitting(true)
    try {
      const fd = new FormData()
      if (vacancyMode === 'upload' && vacancyFile) {
        fd.append('vacancy_file', vacancyFile)
      } else if (vacancyMode === 'select' && selectedVacancyId) {
        fd.append('vacancy_id', String(selectedVacancyId))
      }
      resumeFiles.forEach((f) => fd.append('resume_files', f))
      if (isEval) fd.append('is_eval', 'true')

      const r = await client.post<ScoringJobOut>('/api/scoring/jobs', fd)
      setJobs((prev) => [r.data, ...prev])
      setVacancyFile(null)
      setSelectedVacancyId(null)
      setResumeFiles([])
      setIsEval(false)
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(msg ?? 'Ошибка при отправке')
    } finally {
      setSubmitting(false)
    }
  }

  function openJob(id: number) {
    loadJobDetail(id)
    setView('detail')
  }

  const canSubmit = (vacancyMode === 'upload' ? !!vacancyFile : !!selectedVacancyId) && resumeFiles.length > 0

  if (view === 'detail' && selectedJob) {
    return <JobDetail job={selectedJob} onBack={() => setView('list')} />
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <h1 className="text-xl font-bold text-gray-900">Скоринг резюме</h1>

      {canRun && (
        <div className="bg-white rounded-2xl border border-gray-200 p-5 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Вакансия */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm font-medium text-gray-700">Вакансия</p>
                <div className="flex rounded-lg overflow-hidden border border-gray-200 text-xs">
                  <button
                    onClick={() => setVacancyMode('upload')}
                    className={`px-2 py-1 transition-colors ${vacancyMode === 'upload' ? 'bg-indigo-600 text-white' : 'text-gray-500 hover:bg-gray-50'}`}
                  >
                    Загрузить
                  </button>
                  <button
                    onClick={() => setVacancyMode('select')}
                    className={`px-2 py-1 transition-colors ${vacancyMode === 'select' ? 'bg-indigo-600 text-white' : 'text-gray-500 hover:bg-gray-50'}`}
                  >
                    Из истории
                  </button>
                </div>
              </div>

              {vacancyMode === 'upload' ? (
                <>
                  <div
                    onClick={() => vacancyRef.current?.click()}
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={(e) => { e.preventDefault(); setVacancyFile(e.dataTransfer.files[0]) }}
                    className="border-2 border-dashed border-gray-200 rounded-xl p-4 flex flex-col items-center justify-center gap-2 cursor-pointer hover:border-indigo-400 hover:bg-indigo-50 transition-colors min-h-[100px]"
                  >
                    <Upload size={20} className="text-gray-400" />
                    <span className="text-xs text-gray-500 text-center">
                      {vacancyFile ? vacancyFile.name : 'Перетащи или нажми'}
                    </span>
                  </div>
                  <input ref={vacancyRef} type="file" className="hidden" accept=".md,.txt,.pdf,.docx,.html,.htm"
                    onChange={(e) => setVacancyFile(e.target.files?.[0] ?? null)} />
                </>
              ) : (
                <select
                  value={selectedVacancyId ?? ''}
                  onChange={(e) => setSelectedVacancyId(e.target.value ? Number(e.target.value) : null)}
                  className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm text-gray-700 focus:outline-none focus:border-indigo-400 min-h-[100px] bg-white"
                  size={4}
                >
                  {existingVacancies.length === 0 && (
                    <option disabled value="">Нет сохранённых вакансий</option>
                  )}
                  {existingVacancies.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.title ?? v.filename}
                    </option>
                  ))}
                </select>
              )}
            </div>

            {/* Резюме */}
            <div>
              <p className="text-sm font-medium text-gray-700 mb-2">
                Резюме <span className="text-gray-400 font-normal">({resumeFiles.length} файлов)</span>
              </p>
              <div
                onClick={() => resumesRef.current?.click()}
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => { e.preventDefault(); setResumeFiles((prev) => [...prev, ...Array.from(e.dataTransfer.files)]) }}
                className="border-2 border-dashed border-gray-200 rounded-xl p-4 flex flex-col items-center justify-center gap-2 cursor-pointer hover:border-indigo-400 hover:bg-indigo-50 transition-colors min-h-[100px]"
              >
                <Upload size={20} className="text-gray-400" />
                <span className="text-xs text-gray-500 text-center">Перетащи или нажми · несколько файлов</span>
              </div>
              <input ref={resumesRef} type="file" multiple className="hidden" accept=".md,.txt,.pdf,.docx,.html,.htm"
                onChange={(e) => setResumeFiles((prev) => [...prev, ...Array.from(e.target.files ?? [])])} />
              {resumeFiles.length > 0 && (
                <ul className="mt-2 space-y-1 max-h-28 overflow-y-auto">
                  {resumeFiles.map((f, i) => (
                    <li key={i} className="flex items-center justify-between text-xs text-gray-600 bg-gray-50 rounded px-2 py-1">
                      <span className="truncate">{f.name}</span>
                      <button onClick={(e) => { e.stopPropagation(); setResumeFiles((prev) => prev.filter((_, j) => j !== i)) }}
                        className="ml-2 text-gray-400 hover:text-red-500">✕</button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          {/* Режим тестирования */}
          <div className="border border-gray-100 rounded-xl p-3">
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={isEval}
                onChange={(e) => setIsEval(e.target.checked)}
                className="w-4 h-4 accent-indigo-600"
              />
              <FlaskConical size={14} className="text-indigo-500" />
              <span className="text-sm font-medium text-gray-700">Режим тестирования (eval)</span>
            </label>
            {isEval && (
              <div className="mt-2 ml-6 text-xs text-gray-500 bg-indigo-50 rounded-lg p-3 space-y-1">
                <p>Назовите файлы резюме по шаблону <code className="bg-white px-1 rounded font-mono">имя_БАЛЛ.расширение</code></p>
                <p className="text-gray-400">Примеры: <code className="font-mono">anna_85.md</code>, <code className="font-mono">boris_50.pdf</code>, <code className="font-mono">viktor_20.docx</code></p>
                <p className="text-gray-400">БАЛЛ — ваша экспертная оценка (0–100). После скоринга система покажет, насколько ранжирование модели совпало с вашим.</p>
              </div>
            )}
          </div>

          {error && <p className="text-sm text-red-500">{error}</p>}

          <button
            onClick={handleSubmit}
            disabled={!canSubmit || submitting}
            className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-300 text-white font-medium rounded-xl text-sm transition-colors"
          >
            {submitting ? 'Отправка…' : '🚀 Запустить скоринг'}
          </button>
        </div>
      )}

      {/* Jobs list */}
      {jobs.length > 0 && (
        <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-100">
            <h2 className="text-sm font-semibold text-gray-700">История заданий</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-100 text-xs text-gray-400 uppercase tracking-wide">
                  <th className="py-3 px-4 text-left">Вакансия</th>
                  <th className="py-3 px-4 text-left hidden sm:table-cell">Кандидаты</th>
                  <th className="py-3 px-4 text-left">Статус</th>
                  <th className="py-3 px-4 text-left hidden md:table-cell">Дата</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr
                    key={job.id}
                    onClick={() => openJob(job.id)}
                    className="border-b border-gray-50 hover:bg-gray-50 cursor-pointer transition-colors"
                  >
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-medium text-gray-900 truncate max-w-[160px] sm:max-w-xs">
                          {job.vacancy_title ?? job.vacancy_filename}
                        </p>
                        {job.is_eval && <FlaskConical size={12} className="text-indigo-400 shrink-0" />}
                      </div>
                    </td>
                    <td className="py-3 px-4 text-sm text-gray-500 hidden sm:table-cell">
                      {job.done_candidates + job.skipped_candidates}/{job.total_candidates}
                    </td>
                    <td className="py-3 px-4"><Badge status={job.status} /></td>
                    <td className="py-3 px-4 text-xs text-gray-400 hidden md:table-cell">
                      {new Date(job.created_at).toLocaleString('ru')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
