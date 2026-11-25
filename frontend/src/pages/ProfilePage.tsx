import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { LoaderCircle, Save, UserRound } from 'lucide-react'
import { useState, type FormEvent } from 'react'

import { api } from '@/api/client'
import type { CandidateProfile } from '@/api/types'
import { ApiFeedback, FieldErrors, FormError } from '@/components/ApiFeedback'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'

type ProfileValues = Omit<CandidateProfile, 'id'>

const emptyProfile: ProfileValues = {
  name: '',
  professional_title: '',
  summary: '',
  location: '',
  linkedin_url: '',
  github_url: '',
  portfolio_url: '',
}

function toProfileValues(profile: CandidateProfile): ProfileValues {
  return {
    name: profile.name,
    professional_title: profile.professional_title,
    summary: profile.summary,
    location: profile.location,
    linkedin_url: profile.linkedin_url,
    github_url: profile.github_url,
    portfolio_url: profile.portfolio_url,
  }
}

export function ProfilePage() {
  const queryClient = useQueryClient()
  const profileQuery = useQuery({
    queryKey: ['profile'],
    queryFn: api.profile,
  })
  const [draftValues, setDraftValues] = useState<ProfileValues | null>(null)
  const [saved, setSaved] = useState(false)
  const values = draftValues ?? (
    profileQuery.data ? toProfileValues(profileQuery.data) : emptyProfile
  )

  const saveMutation = useMutation({
    mutationFn: () =>
      profileQuery.data
        ? api.updateProfile(values)
        : api.createProfile(values),
    onSuccess: async (profile) => {
      setDraftValues(toProfileValues(profile))
      setSaved(true)
      await queryClient.invalidateQueries({ queryKey: ['profile'] })
    },
  })

  function updateField(field: keyof ProfileValues, value: string) {
    setSaved(false)
    setDraftValues((current) => ({
      ...(current ?? values),
      [field]: value,
    }))
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    saveMutation.mutate()
  }

  return (
    <div className="workspace-page">
      <div className="page-eyebrow">PERFIL PROFESIONAL</div>
      <div className="workspace-page-heading">
        <div className="page-icon">
          <UserRound aria-hidden="true" size={22} />
        </div>
        <div>
          <h1>Perfil</h1>
          <p>
            Mantén actualizada la información profesional asociada a tu base de
            conocimiento local.
          </p>
        </div>
      </div>

      {profileQuery.error && <ApiFeedback error={profileQuery.error} />}
      {profileQuery.isLoading ? (
        <div className="state-panel" role="status">
          <LoaderCircle aria-hidden="true" className="icon-spin" size={19} />
          Cargando perfil…
        </div>
      ) : (
        <Card className="editor-card profile-card">
          <CardHeader className="editor-card-header">
            <div className="editor-title">
              <div className="editor-icon">
                <UserRound aria-hidden="true" size={17} />
              </div>
              <div>
                <h2>{profileQuery.data ? 'Tus datos profesionales' : 'Crea tu perfil'}</h2>
                <p>
                  {profileQuery.data
                    ? 'Los cambios se guardan en la base de datos local.'
                    : 'Todavía no existe un perfil en la base de datos.'}
                </p>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <form className="data-form profile-form" onSubmit={submit}>
              <label className="form-field">
                <span>Nombre <b aria-hidden="true">*</b></span>
                <input
                  maxLength={150}
                  onChange={(event) => updateField('name', event.target.value)}
                  required
                  value={values.name}
                />
                <FieldErrors error={saveMutation.error} field="name" />
              </label>
              <label className="form-field">
                <span>Titular profesional</span>
                <input
                  maxLength={200}
                  onChange={(event) =>
                    updateField('professional_title', event.target.value)
                  }
                  value={values.professional_title}
                />
                <FieldErrors error={saveMutation.error} field="professional_title" />
              </label>
              <label className="form-field form-field-wide">
                <span>Resumen</span>
                <textarea
                  onChange={(event) => updateField('summary', event.target.value)}
                  rows={4}
                  value={values.summary}
                />
                <FieldErrors error={saveMutation.error} field="summary" />
              </label>
              <label className="form-field">
                <span>Ubicación</span>
                <input
                  maxLength={200}
                  onChange={(event) => updateField('location', event.target.value)}
                  value={values.location}
                />
                <FieldErrors error={saveMutation.error} field="location" />
              </label>
              <label className="form-field">
                <span>LinkedIn</span>
                <input
                  onChange={(event) =>
                    updateField('linkedin_url', event.target.value)
                  }
                  placeholder="https://"
                  type="url"
                  value={values.linkedin_url}
                />
                <FieldErrors error={saveMutation.error} field="linkedin_url" />
              </label>
              <label className="form-field">
                <span>GitHub</span>
                <input
                  onChange={(event) => updateField('github_url', event.target.value)}
                  placeholder="https://"
                  type="url"
                  value={values.github_url}
                />
                <FieldErrors error={saveMutation.error} field="github_url" />
              </label>
              <label className="form-field">
                <span>Portafolio</span>
                <input
                  onChange={(event) =>
                    updateField('portfolio_url', event.target.value)
                  }
                  placeholder="https://"
                  type="url"
                  value={values.portfolio_url}
                />
                <FieldErrors error={saveMutation.error} field="portfolio_url" />
              </label>
              {saveMutation.error && (
                <div className="form-field-wide">
                  <FormError error={saveMutation.error} />
                </div>
              )}
              <div className="form-actions form-field-wide">
                <Button disabled={saveMutation.isPending || !values.name.trim()}>
                  {saveMutation.isPending ? (
                    <LoaderCircle
                      aria-hidden="true"
                      className="icon-spin"
                      size={15}
                    />
                  ) : (
                    <Save aria-hidden="true" size={15} />
                  )}
                  {profileQuery.data ? 'Guardar cambios' : 'Crear perfil'}
                </Button>
                {saved && (
                  <span className="saved-message" role="status">
                    Guardado correctamente
                  </span>
                )}
              </div>
            </form>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
