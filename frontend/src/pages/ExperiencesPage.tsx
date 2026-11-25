import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  BriefcaseBusiness,
  CalendarDays,
  LoaderCircle,
  Plus,
  Trash2,
} from 'lucide-react'
import { useState, type FormEvent } from 'react'

import { api } from '@/api/client'
import type { ProfessionalExperience, ProfessionalExperienceInput } from '@/api/types'
import { ApiFeedback, FieldErrors, FormError } from '@/components/ApiFeedback'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'

export function ExperiencesPage() {
  const queryClient = useQueryClient()
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<ProfessionalExperience | null>(null)
  const experienceQuery = useQuery({
    queryKey: ['experiences'],
    queryFn: api.experiences,
  })
  const questionQuery = useQuery({
    queryKey: ['questions', 'all'],
    queryFn: () => api.questions(),
  })
  const createMutation = useMutation({
    mutationFn: api.createExperience,
    onSuccess: async () => {
      setFormOpen(false)
      await queryClient.invalidateQueries({ queryKey: ['experiences'] })
    },
  })
  const updateMutation = useMutation({
    mutationFn: ({ id, value }: { id: number; value: ProfessionalExperienceInput }) =>
      api.updateExperience(id, value),
    onSuccess: async () => {
      setEditing(null)
      await queryClient.invalidateQueries({ queryKey: ['experiences'] })
    },
  })
  const deleteMutation = useMutation({
    mutationFn: api.deleteExperience,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['experiences'] }),
  })

  function save(value: ProfessionalExperienceInput) {
    if (editing) {
      updateMutation.mutate({ id: editing.id, value })
    } else {
      createMutation.mutate(value)
    }
  }

  const questions = questionQuery.data?.results ?? []
  const experiences = experienceQuery.data?.results ?? []

  return (
    <div className="workspace-page">
      <div className="page-eyebrow">TRAYECTORIA PROFESIONAL</div>
      <div className="workspace-page-heading">
        <div className="page-icon">
          <BriefcaseBusiness aria-hidden="true" size={22} />
        </div>
        <div>
          <h1>Experiencias</h1>
          <p>
            Registra proyectos, responsabilidades y logros y relaciónalos con
            preguntas cuando resulte útil.
          </p>
        </div>
      </div>

      <Card className="editor-card">
        <CardHeader className="editor-card-header">
          <div className="editor-title">
            <div className="editor-icon">
              <Plus aria-hidden="true" size={17} />
            </div>
            <div>
              <h2>{editing ? 'Editar experiencia' : 'Experiencias profesionales'}</h2>
              <p>Los registros se almacenan localmente y admiten fechas abiertas.</p>
            </div>
          </div>
          {!editing && (
            <Button
              onClick={() => setFormOpen((current) => !current)}
              variant={formOpen ? 'ghost' : 'outline'}
            >
              <Plus size={15} />
              {formOpen ? 'Cancelar' : 'Añadir experiencia'}
            </Button>
          )}
        </CardHeader>
        {(formOpen || editing) && (
          <CardContent>
            <ExperienceForm
              error={editing ? updateMutation.error : createMutation.error}
              initial={editing ?? undefined}
              onCancel={() => {
                setFormOpen(false)
                setEditing(null)
              }}
              onSave={save}
              pending={createMutation.isPending || updateMutation.isPending}
              questions={questions}
            />
          </CardContent>
        )}
      </Card>

      <ApiFeedback error={experienceQuery.error ?? questionQuery.error} />
      {experienceQuery.isLoading ? (
        <div className="state-panel" role="status">
          <LoaderCircle aria-hidden="true" className="icon-spin" size={19} />
          Cargando experiencias…
        </div>
      ) : experiences.length === 0 ? (
        <Card className="empty-card">
          <CardContent className="empty-content">
            <div className="empty-icon">
              <BriefcaseBusiness aria-hidden="true" size={19} />
            </div>
            <h2>Todavía no hay experiencias</h2>
            <p>
              Añade un proyecto o puesto profesional. No se muestran registros
              de ejemplo.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="experience-list">
          {experiences.map((experience) => (
            <Card className="experience-card" key={experience.id}>
              <CardContent className="experience-card-content">
                <div className="experience-card-top">
                  <div className="experience-heading">
                    <div className="experience-icon">
                      <BriefcaseBusiness aria-hidden="true" size={17} />
                    </div>
                    <div>
                      <h2>{experience.position}</h2>
                      <p>{experience.company_or_project}</p>
                    </div>
                  </div>
                  <div className="row-actions">
                    <Button
                      onClick={() => {
                        setEditing(experience)
                        setFormOpen(false)
                      }}
                      size="sm"
                      variant="outline"
                    >
                      Editar
                    </Button>
                    <Button
                      aria-label={`Eliminar experiencia ${experience.position}`}
                      onClick={() => {
                        if (
                          window.confirm(
                            `¿Eliminar la experiencia «${experience.position}»? Las preguntas se conservarán.`,
                          )
                        ) {
                          deleteMutation.mutate(experience.id)
                        }
                      }}
                      size="icon"
                      variant="ghost"
                    >
                      <Trash2 aria-hidden="true" size={15} />
                    </Button>
                  </div>
                </div>
                <div className="experience-period">
                  <CalendarDays aria-hidden="true" size={14} />
                  {experience.start_date || 'Fecha de inicio no indicada'}
                  <span aria-hidden="true">—</span>
                  {experience.end_date || 'Actual / sin fecha de fin'}
                </div>
                <div className="experience-detail-grid">
                  <div>
                    <h3>Responsabilidades</h3>
                    <p>{experience.responsibilities}</p>
                  </div>
                  <div>
                    <h3>Logros</h3>
                    <p>{experience.achievements}</p>
                  </div>
                </div>
                {experience.questions.length > 0 && (
                  <div className="experience-question-links">
                    <span>Preguntas relacionadas</span>
                    <div className="chip-row">
                      {experience.questions.map((question) => (
                        <span className="data-chip" key={question.id}>
                          {question.question}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
      {deleteMutation.error && <FormError error={deleteMutation.error} />}
    </div>
  )
}

function ExperienceForm({
  initial,
  questions,
  error,
  pending,
  onSave,
  onCancel,
}: {
  initial?: ProfessionalExperience
  questions: { id: number; question: string }[]
  error: unknown
  pending: boolean
  onSave: (value: ProfessionalExperienceInput) => void
  onCancel: () => void
}) {
  const [position, setPosition] = useState(initial?.position ?? '')
  const [company, setCompany] = useState(initial?.company_or_project ?? '')
  const [startDate, setStartDate] = useState(initial?.start_date ?? '')
  const [endDate, setEndDate] = useState(initial?.end_date ?? '')
  const [responsibilities, setResponsibilities] = useState(
    initial?.responsibilities ?? '',
  )
  const [achievements, setAchievements] = useState(initial?.achievements ?? '')
  const [questionIds, setQuestionIds] = useState(
    initial?.questions.map((question) => question.id) ?? [],
  )

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    onSave({
      position: position.trim(),
      company_or_project: company.trim(),
      start_date: startDate || null,
      end_date: endDate || null,
      responsibilities: responsibilities.trim(),
      achievements: achievements.trim(),
      question_ids: questionIds,
    })
  }

  return (
    <form className="data-form" onSubmit={submit}>
      <label className="form-field">
        <span>Cargo <b aria-hidden="true">*</b></span>
        <input
          maxLength={150}
          onChange={(event) => setPosition(event.target.value)}
          required
          value={position}
        />
        <FieldErrors error={error} field="position" />
      </label>
      <label className="form-field">
        <span>Empresa o proyecto <b aria-hidden="true">*</b></span>
        <input
          maxLength={200}
          onChange={(event) => setCompany(event.target.value)}
          required
          value={company}
        />
        <FieldErrors error={error} field="company_or_project" />
      </label>
      <label className="form-field">
        <span>Fecha de inicio</span>
        <input
          onChange={(event) => setStartDate(event.target.value)}
          type="date"
          value={startDate}
        />
        <FieldErrors error={error} field="start_date" />
      </label>
      <label className="form-field">
        <span>Fecha de fin <small>(opcional)</small></span>
        <input
          onChange={(event) => setEndDate(event.target.value)}
          type="date"
          value={endDate}
        />
        <FieldErrors error={error} field="end_date" />
      </label>
      <label className="form-field">
        <span>Responsabilidades <b aria-hidden="true">*</b></span>
        <textarea
          onChange={(event) => setResponsibilities(event.target.value)}
          required
          rows={4}
          value={responsibilities}
        />
        <FieldErrors error={error} field="responsibilities" />
      </label>
      <label className="form-field">
        <span>Logros <b aria-hidden="true">*</b></span>
        <textarea
          onChange={(event) => setAchievements(event.target.value)}
          required
          rows={4}
          value={achievements}
        />
        <FieldErrors error={error} field="achievements" />
      </label>
      <div className="form-field form-field-wide">
        <span>Preguntas relacionadas</span>
        <div className="checkbox-options">
          {questions.length ? (
            questions.map((question) => (
              <label className="check-option check-option-wide" key={question.id}>
                <input
                  checked={questionIds.includes(question.id)}
                  onChange={() =>
                    setQuestionIds((current) =>
                      current.includes(question.id)
                        ? current.filter((id) => id !== question.id)
                        : [...current, question.id],
                    )
                  }
                  type="checkbox"
                />
                {question.question}
              </label>
            ))
          ) : (
            <span className="form-hint">
              No hay preguntas disponibles; la relación puede añadirse más tarde.
            </span>
          )}
        </div>
        <FieldErrors error={error} field="question_ids" />
      </div>
      {error != null && (
        <div className="form-field-wide">
          <FormError error={error} />
        </div>
      )}
      <div className="form-actions form-field-wide">
        <Button disabled={pending}>
          {pending ? (
            <LoaderCircle aria-hidden="true" className="icon-spin" size={15} />
          ) : (
            <Plus aria-hidden="true" size={15} />
          )}
          {initial ? 'Guardar cambios' : 'Guardar experiencia'}
        </Button>
        <Button onClick={onCancel} type="button" variant="ghost">
          Cancelar
        </Button>
      </div>
    </form>
  )
}
