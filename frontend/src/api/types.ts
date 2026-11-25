export interface ApiPage<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface ApiErrorPayload {
  detail: string
  code: string
  errors: Record<string, string[] | Record<string, string[]>>
}

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly errors: ApiErrorPayload['errors']

  constructor(
    status: number,
    payload: Partial<ApiErrorPayload>,
  ) {
    super(payload.detail ?? 'No se pudo completar la petición.')
    this.name = 'ApiError'
    this.status = status
    this.code = payload.code ?? 'api_error'
    this.errors = payload.errors ?? {}
  }
}

export interface SessionUser {
  username: string
  is_operator: boolean
}

export interface SessionState {
  authenticated: boolean
  user: SessionUser | null
}

export interface LoginResponse extends SessionState {
  authenticated: true
  user: SessionUser
  csrfToken: string
}

export interface Category {
  id: number
  name: string
}

export interface Tag {
  id: number
  name: string
}

export interface ExperienceSummary {
  id: number
  position: string
  company_or_project: string
}

export interface QuestionSummary {
  id: number
  question: string
}

export interface Answer {
  id: number
  question_id: number
  text: string
}

export interface QuestionVariant {
  id: number
  question_id: number
  text: string
}

export interface Question {
  id: number
  question: string
  category: Category
  tags: Tag[]
  professional_experiences: ExperienceSummary[]
  answers: Answer[]
  variants: QuestionVariant[]
  created_at: string
  updated_at: string
}

export interface QuestionInput {
  question: string
  category_id: number
  tag_ids: number[]
  professional_experience_ids: number[]
}

export interface CandidateProfile {
  id: number
  name: string
  professional_title: string
  summary: string
  location: string
  linkedin_url: string
  github_url: string
  portfolio_url: string
}

export interface ProfessionalExperience {
  id: number
  position: string
  company_or_project: string
  start_date: string | null
  end_date: string | null
  responsibilities: string
  achievements: string
  questions: QuestionSummary[]
}

export interface ProfessionalExperienceInput {
  position: string
  company_or_project: string
  start_date: string | null
  end_date: string | null
  responsibilities: string
  achievements: string
  question_ids: number[]
}
