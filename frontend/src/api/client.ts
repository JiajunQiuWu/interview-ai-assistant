import { ApiError } from './types'
import type {
  ApiPage,
  CandidateProfile,
  Category,
  LoginResponse,
  ProfessionalExperience,
  ProfessionalExperienceInput,
  Question,
  QuestionInput,
  QuestionVariant,
  SessionState,
  Tag,
  Answer,
} from './types'

let csrfToken: string | null = null

const unsafeMethods = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])

async function readError(response: Response): Promise<ApiError> {
  let payload: Record<string, unknown> = {}
  try {
    const body: unknown = await response.json()
    if (typeof body === 'object' && body !== null) {
      payload = body as Record<string, unknown>
    }
  } catch {
    payload = {}
  }

  const detail = typeof payload.detail === 'string' ? payload.detail : undefined
  const code = typeof payload.code === 'string' ? payload.code : undefined
  const errors =
    typeof payload.errors === 'object' && payload.errors !== null
      ? (payload.errors as ApiError['errors'])
      : undefined

  return new ApiError(response.status, { detail, code, errors })
}

export async function refreshCsrfToken(): Promise<string> {
  const response = await fetch('/api/auth/csrf/', {
    method: 'GET',
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
    cache: 'no-store',
  })
  if (!response.ok) {
    throw await readError(response)
  }
  const payload: unknown = await response.json()
  if (
    typeof payload !== 'object' ||
    payload === null ||
    !('csrfToken' in payload) ||
    typeof payload.csrfToken !== 'string'
  ) {
    throw new Error('Django no devolvió un token CSRF válido.')
  }
  csrfToken = payload.csrfToken
  return csrfToken
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const method = (options.method ?? 'GET').toUpperCase()
  const headers = new Headers(options.headers)
  headers.set('Accept', 'application/json')

  if (options.body !== undefined && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  if (unsafeMethods.has(method)) {
    const token = csrfToken ?? (await refreshCsrfToken())
    headers.set('X-CSRFToken', token)
  }

  const response = await fetch(path, {
    ...options,
    method,
    headers,
    credentials: 'same-origin',
  })
  if (!response.ok) {
    const error = await readError(response)
    if (
      error.status === 403 &&
      error.code === 'not_authenticated' &&
      !path.startsWith('/api/auth/')
    ) {
      window.dispatchEvent(new Event('auth-session-expired'))
    }
    throw error
  }
  if (response.status === 204) {
    return undefined as T
  }
  return (await response.json()) as T
}

function jsonBody(value: unknown): string {
  return JSON.stringify(value)
}

export const api = {
  health: async (): Promise<{ status: 'ok' }> => {
    const response = await fetch('/api/health/', {
      method: 'GET',
      credentials: 'same-origin',
      headers: { Accept: 'application/json' },
      cache: 'no-store',
    })
    if (!response.ok) {
      throw new ApiError(response.status, {
        detail: `El health check respondió ${response.status}.`,
        code: 'health_unavailable',
      })
    }
    const payload: unknown = await response.json()
    if (
      typeof payload !== 'object' ||
      payload === null ||
      !('status' in payload) ||
      payload.status !== 'ok'
    ) {
      throw new Error('El health check devolvió una respuesta inesperada.')
    }
    return { status: 'ok' }
  },

  session: () => request<SessionState>('/api/auth/session/'),

  async login(username: string, password: string): Promise<LoginResponse> {
    if (!csrfToken) {
      await refreshCsrfToken()
    }
    const result = await request<LoginResponse>('/api/auth/login/', {
      method: 'POST',
      body: jsonBody({ username, password }),
    })
    csrfToken = result.csrfToken
    return result
  },

  async logout(): Promise<void> {
    await request<void>('/api/auth/logout/', {
      method: 'POST',
      body: jsonBody({}),
    })
    csrfToken = null
  },

  categories: () => request<ApiPage<Category>>('/api/categories/?page_size=100'),
  createCategory: (name: string) =>
    request<Category>('/api/categories/', {
      method: 'POST',
      body: jsonBody({ name }),
    }),
  updateCategory: (id: number, name: string) =>
    request<Category>(`/api/categories/${id}/`, {
      method: 'PATCH',
      body: jsonBody({ name }),
    }),
  deleteCategory: (id: number) =>
    request<void>(`/api/categories/${id}/`, { method: 'DELETE' }),

  tags: () => request<ApiPage<Tag>>('/api/tags/?page_size=100'),
  createTag: (name: string) =>
    request<Tag>('/api/tags/', {
      method: 'POST',
      body: jsonBody({ name }),
    }),
  updateTag: (id: number, name: string) =>
    request<Tag>(`/api/tags/${id}/`, {
      method: 'PATCH',
      body: jsonBody({ name }),
    }),
  deleteTag: (id: number) => request<void>(`/api/tags/${id}/`, { method: 'DELETE' }),

  questions: (filters: { search?: string; category?: string } = {}) => {
    const params = new URLSearchParams({ page_size: '100' })
    if (filters.search) params.set('search', filters.search)
    if (filters.category) params.set('category', filters.category)
    return request<ApiPage<Question>>(`/api/questions/?${params.toString()}`)
  },
  createQuestion: (value: QuestionInput) =>
    request<Question>('/api/questions/', {
      method: 'POST',
      body: jsonBody(value),
    }),
  updateQuestion: (id: number, value: QuestionInput) =>
    request<Question>(`/api/questions/${id}/`, {
      method: 'PATCH',
      body: jsonBody(value),
    }),
  deleteQuestion: (id: number) =>
    request<void>(`/api/questions/${id}/`, { method: 'DELETE' }),

  createAnswer: (questionId: number, text: string) =>
    request<Answer>(`/api/questions/${questionId}/answers/`, {
      method: 'POST',
      body: jsonBody({ text }),
    }),
  updateAnswer: (id: number, text: string) =>
    request<Answer>(`/api/answers/${id}/`, {
      method: 'PATCH',
      body: jsonBody({ text }),
    }),
  deleteAnswer: (id: number) =>
    request<void>(`/api/answers/${id}/`, { method: 'DELETE' }),

  createVariant: (questionId: number, text: string) =>
    request<QuestionVariant>(`/api/questions/${questionId}/variants/`, {
      method: 'POST',
      body: jsonBody({ text }),
    }),
  updateVariant: (id: number, text: string) =>
    request<QuestionVariant>(`/api/variants/${id}/`, {
      method: 'PATCH',
      body: jsonBody({ text }),
    }),
  deleteVariant: (id: number) =>
    request<void>(`/api/variants/${id}/`, { method: 'DELETE' }),

  async profile(): Promise<CandidateProfile | null> {
    try {
      return await request<CandidateProfile>('/api/profile/')
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        return null
      }
      throw error
    }
  },
  createProfile: (value: Omit<CandidateProfile, 'id'>) =>
    request<CandidateProfile>('/api/profile/', {
      method: 'POST',
      body: jsonBody(value),
    }),
  updateProfile: (value: Partial<Omit<CandidateProfile, 'id'>>) =>
    request<CandidateProfile>('/api/profile/', {
      method: 'PATCH',
      body: jsonBody(value),
    }),

  experiences: () =>
    request<ApiPage<ProfessionalExperience>>('/api/experiences/?page_size=100'),
  createExperience: (value: ProfessionalExperienceInput) =>
    request<ProfessionalExperience>('/api/experiences/', {
      method: 'POST',
      body: jsonBody(value),
    }),
  updateExperience: (id: number, value: ProfessionalExperienceInput) =>
    request<ProfessionalExperience>(`/api/experiences/${id}/`, {
      method: 'PATCH',
      body: jsonBody(value),
    }),
  deleteExperience: (id: number) =>
    request<void>(`/api/experiences/${id}/`, { method: 'DELETE' }),
}
