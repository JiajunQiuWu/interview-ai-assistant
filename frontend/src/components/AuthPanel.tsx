import { useMutation, useQueryClient } from '@tanstack/react-query'
import { KeyRound, LoaderCircle, LockKeyhole, Sparkles } from 'lucide-react'
import { useState, type FormEvent } from 'react'

import { api } from '@/api/client'
import { ApiError } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { FormError } from '@/components/ApiFeedback'

export function LoginPanel({
  connectionAvailable,
}: {
  connectionAvailable: boolean
}) {
  const queryClient = useQueryClient()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const loginMutation = useMutation({
    mutationFn: () => api.login(username, password),
    onSuccess: async (session) => {
      setPassword('')
      queryClient.setQueryData(['api-session'], session)
      await queryClient.invalidateQueries({ queryKey: ['api-session'] })
    },
  })

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    loginMutation.mutate()
  }

  const fieldErrors =
    loginMutation.error instanceof ApiError ? loginMutation.error.errors : {}

  return (
    <div className="auth-page">
      <Card className="auth-card">
        <CardContent className="auth-card-content">
          <div className="auth-emblem">
            <Sparkles aria-hidden="true" size={22} />
          </div>
          <div className="section-eyebrow">ACCESO LOCAL</div>
          <h1>Tu espacio de preparación</h1>
          <p className="auth-description">
            Inicia sesión con tu cuenta de operador Django. Tus datos permanecen
            en este equipo.
          </p>
          {!connectionAvailable && (
            <div className="api-feedback" role="status">
              <LockKeyhole aria-hidden="true" size={17} />
              <span>
                No se puede contactar con Django. Inícialo en
                {' '}<code>127.0.0.1:8000</code> para autenticarte.
              </span>
            </div>
          )}
          {loginMutation.error && <FormError error={loginMutation.error} />}
          <form className="auth-form" onSubmit={submit}>
            <label className="form-field" htmlFor="login-username">
              <span>Usuario</span>
              <input
                autoComplete="username"
                id="login-username"
                name="username"
                onChange={(event) => setUsername(event.target.value)}
                required
                value={username}
              />
              {Array.isArray(fieldErrors.username) && (
                <span className="field-error">{fieldErrors.username.join(' ')}</span>
              )}
            </label>
            <label className="form-field" htmlFor="login-password">
              <span>Contraseña</span>
              <input
                autoComplete="current-password"
                id="login-password"
                name="password"
                onChange={(event) => setPassword(event.target.value)}
                required
                type="password"
                value={password}
              />
            </label>
            <Button
              className="auth-submit"
              disabled={loginMutation.isPending || !connectionAvailable}
              type="submit"
            >
              {loginMutation.isPending ? (
                <LoaderCircle aria-hidden="true" className="icon-spin" size={16} />
              ) : (
                <KeyRound aria-hidden="true" size={16} />
              )}
              Iniciar sesión
            </Button>
          </form>
          <div className="auth-footnote">
            <LockKeyhole aria-hidden="true" size={14} />
            Acceso protegido por sesión y verificación CSRF
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
