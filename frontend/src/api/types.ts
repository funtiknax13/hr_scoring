export interface UserMe {
  id: number
  username: string
  role: string
}

// ---------- Scoring ----------

export type JobStatus = 'pending' | 'running' | 'done' | 'error'
export type ResultStatus = 'pending' | 'done' | 'skipped' | 'error'

export interface ScoringJobOut {
  id: number
  vacancy_id: number
  vacancy_title: string | null
  vacancy_filename: string
  status: JobStatus
  model_name: string
  prompt_versions: string
  error_message: string | null
  created_at: string
  finished_at: string | null
  total_candidates: number
  done_candidates: number
  skipped_candidates: number
}

export interface CandidateResultOut {
  id: number
  candidate_id: number
  candidate_name: string | null
  candidate_filename: string
  status: ResultStatus
  total_score: number | null
  overall_confidence: number | null
  manipulation_attempt: boolean | null
  result_json: string | null
  profile_json: string | null
  error: string | null
  created_at: string
}

export interface ScoringJobDetailOut extends ScoringJobOut {
  rubric_json: string | null
  results: CandidateResultOut[]
}

export interface Criterion {
  name: string
  weight: number
  description: string
}

export interface Rubric {
  role_title: string
  criteria: Criterion[]
  must_haves: string[]
  nice_to_haves: string[]
}

export interface CriterionScore {
  name: string
  score: number
  evidence: string
  reasoning: string
  confidence: number
  insufficient_evidence: boolean
}

export interface ScoringOutput {
  criterion_scores: CriterionScore[]
  strengths: string[]
  gaps: string[]
  red_flags: string[]
  overall_reasoning: string
}

export interface ResumeProfile {
  candidate_name: string
  total_years_experience: number | null
  skills: string[]
  roles: string[]
  education: string
  summary: string
  manipulation_attempt: boolean
}

// ---------- Vacancies ----------

export interface SessionOut {
  id: number
  source: string
  query: string
  city: string | null
  count: number
  fetched_at: string
}

export interface VacancyOut {
  id: number
  source: string
  external_id: string
  title: string
  location: string | null
  url: string | null
  first_seen: string
  last_seen: string
}

export interface VacancyWithSnapshot extends VacancyOut {
  latest: {
    salary_from: number | null
    salary_to: number | null
    currency: string | null
    fetched_at: string
  } | null
}

export interface SessionDetailOut extends SessionOut {
  vacancies: VacancyWithSnapshot[]
}
