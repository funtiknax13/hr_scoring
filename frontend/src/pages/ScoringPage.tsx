import { useEffect, useRef, useState } from 'react'
import { ArrowLeft, ChevronDown, ChevronUp, Upload, AlertTriangle } from 'lucide-react'
import client from '../api/client'
import { useAuth } from '../context/AuthContext'
import {
  CandidateResultOut, CriterionScore, Rubric,
  ScoringJobDetailOut, ScoringJobOut, ScoringOutput, ResumeProfile,
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
            {result.manipulation_attempt && <AlertTriangle size={14} className="text-red-500" title="Попытка манипуляции" />}
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
            <h2 className="text-lg font-semibold text-gray-900">{job.vacancy_title ?? job.vacancy_filename}</h2>
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
  const [vacancyFile, setVacancyFile] = useState<File | null>(null)
  const [resumeFiles, setResumeFiles] = useState<File[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [jobs, setJobs] = useState<ScoringJobOut[]>([])
  const [selectedJob, setSelectedJob] = useState<ScoringJobDetailOut | null>(null)
  const [view, setView] = useState<'list' | 'detail'>('list')

  useEffect(() => {
    loadJobs()
  }, [])

  // Polling while a job is active
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

  async function loadJobDetail(id: number) {
    const r = await client.get<ScoringJobDetailOut>(`/api/scoring/jobs/${id}`)
    setSelectedJob(r.data)
    setJobs((prev) => prev.map((j) => (j.id === id ? r.data : j)))
  }

  async function handleSubmit() {
    if (!vacancyFile || resumeFiles.length === 0) return
    setError('')
    setSubmitting(true)
    try {
      const fd = new FormData()
      fd.append('vacancy_file', vacancyFile)
      resumeFiles.forEach((f) => fd.append('resume_files', f))
      const r = await client.post<ScoringJobOut>('/api/scoring/jobs', fd)
      setJobs((prev) => [r.data, ...prev])
      setVacancyFile(null)
      setResumeFiles([])
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

  if (view === 'detail' && selectedJob) {
    return <JobDetail job={selectedJob} onBack={() => setView('list')} />
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <h1 className="text-xl font-bold text-gray-900">Скоринг резюме</h1>

      {/* Upload form — только для admin и hr */}
      {canRun && <div className="bg-white rounded-2xl border border-gray-200 p-5 space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Vacancy */}
          <div>
            <p className="text-sm font-medium text-gray-700 mb-2">Вакансия</p>
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
          </div>

          {/* Resumes */}
          <div>
            <p className="text-sm font-medium text-gray-700 mb-2">Резюме <span className="text-gray-400 font-normal">({resumeFiles.length} файлов)</span></p>
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

        {error && <p className="text-sm text-red-500">{error}</p>}

        <button
          onClick={handleSubmit}
          disabled={!vacancyFile || resumeFiles.length === 0 || submitting}
          className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-300 text-white font-medium rounded-xl text-sm transition-colors"
        >
          {submitting ? 'Отправка…' : '🚀 Запустить скоринг'}
        </button>
      </div>}

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
                      <p className="text-sm font-medium text-gray-900 truncate max-w-[180px] sm:max-w-xs">
                        {job.vacancy_title ?? job.vacancy_filename}
                      </p>
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
