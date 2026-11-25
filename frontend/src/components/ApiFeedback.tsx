import { AlertCircle } from 'lucide-react'

import { ApiError } from '@/api/types'

export function ApiFeedback({
  error,
  fallback = 'No se pudieron cargar los datos. Comprueba Django e inténtalo de nuevo.',
}: {
  error: unknown
  fallback?: string
}) {
  if (!error) return null

  const message =
    error instanceof ApiError
      ? error.code === 'not_authenticated'
        ? 'La sesión ya no está autenticada. Inicia sesión de nuevo.'
        : error.code === 'permission_denied'
          ? 'Tu cuenta no tiene permisos de operador para acceder a estos datos.'
          : error.code === 'csrf_failed'
            ? 'La comprobación de seguridad ha fallado. Recarga e inténtalo de nuevo.'
            : error.message
      : error instanceof Error
        ? error.message
        : fallback

  return (
    <div className="api-feedback" role="alert">
      <AlertCircle aria-hidden="true" size={17} />
      <span>{message}</span>
    </div>
  )
}

export function FieldErrors({
  error,
  field,
}: {
  error: unknown
  field: string
}) {
  if (!(error instanceof ApiError)) return null
  const value = error.errors[field]
  const messages = Array.isArray(value) ? value : []
  if (!messages.length) return null

  return (
    <span className="field-error" role="alert">
      {messages.join(' ')}
    </span>
  )
}

export function FormError({ error }: { error: unknown }) {
  if (!(error instanceof ApiError)) return <ApiFeedback error={error} />
  const messages = error.errors.non_field_errors
  const message =
    Array.isArray(messages) && messages.length
      ? messages.join(' ')
      : error.message

  return (
    <div className="form-error" role="alert">
      {message}
    </div>
  )
}
