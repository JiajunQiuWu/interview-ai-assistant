import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  BookOpen,
  Check,
  CircleAlert,
  LoaderCircle,
  Plus,
  Search,
  Tag as TagIcon,
  Trash2,
  X,
} from 'lucide-react'
import { useState, type FormEvent } from 'react'

import { api } from '@/api/client'
import type {
  ApiPage,
  Category,
  ProfessionalExperience,
  Question,
  QuestionInput,
} from '@/api/types'
import { ApiFeedback, FieldErrors, FormError } from '@/components/ApiFeedback'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'

type KnowledgeTab = 'preguntas' | 'categorias' | 'etiquetas'

export function KnowledgePage() {
  const [tab, setTab] = useState<KnowledgeTab>('preguntas')
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')
  const questionsQuery = useQuery({
    queryKey: ['questions', search, category],
    queryFn: () => api.questions({ search, category }),
    enabled: tab === 'preguntas',
  })
  const categoriesQuery = useQuery({
    queryKey: ['categories'],
    queryFn: api.categories,
  })
  const tagsQuery = useQuery({ queryKey: ['tags'], queryFn: api.tags })

  return (
    <div className="workspace-page">
      <div className="page-eyebrow">BASE DE CONOCIMIENTO</div>
      <div className="workspace-page-heading">
        <div className="page-icon">
          <BookOpen aria-hidden="true" size={22} />
        </div>
        <div>
          <h1>Conocimiento</h1>
          <p>
            Gestiona preguntas, respuestas, variantes, categorías y etiquetas
            guardadas localmente.
          </p>
        </div>
      </div>

      <div aria-label="Secciones de conocimiento" className="content-tabs" role="tablist">
        {(
          [
            ['preguntas', 'Preguntas'],
            ['categorias', 'Categorías'],
            ['etiquetas', 'Etiquetas'],
          ] as const
        ).map(([key, label]) => (
          <button
            aria-selected={tab === key}
            className={`content-tab${tab === key ? ' content-tab-active' : ''}`}
            key={key}
            onClick={() => setTab(key)}
            role="tab"
            type="button"
          >
            {label}
          </button>
        ))}
      </div>

      {tab === 'preguntas' && (
        <QuestionsSection
          categories={categoriesQuery.data?.results ?? []}
          category={category}
          onCategoryChange={setCategory}
          onSearchChange={setSearch}
          questions={questionsQuery.data?.results ?? []}
          search={search}
          queryError={questionsQuery.error ?? categoriesQuery.error}
          queryLoading={questionsQuery.isLoading || categoriesQuery.isLoading}
        />
      )}
      {tab === 'categorias' && (
        <NameListSection
          label="categoría"
          onCreate={api.createCategory}
          onDelete={api.deleteCategory}
          onUpdate={api.updateCategory}
          query={categoriesQuery}
          queryKey="categories"
          title="Categorías"
        />
      )}
      {tab === 'etiquetas' && (
        <NameListSection
          icon={<TagIcon aria-hidden="true" size={17} />}
          label="etiqueta"
          onCreate={api.createTag}
          onDelete={api.deleteTag}
          onUpdate={api.updateTag}
          query={tagsQuery}
          queryKey="tags"
          title="Etiquetas"
        />
      )}
    </div>
  )
}

function QuestionsSection({
  categories,
  category,
  onCategoryChange,
  onSearchChange,
  questions,
  search,
  queryError,
  queryLoading,
}: {
  categories: Category[]
  category: string
  onCategoryChange: (value: string) => void
  onSearchChange: (value: string) => void
  questions: Question[]
  search: string
  queryError: unknown
  queryLoading: boolean
}) {
  const queryClient = useQueryClient()
  const [createOpen, setCreateOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [createError, setCreateError] = useState<unknown>(null)
  const createMutation = useMutation({
    mutationFn: api.createQuestion,
    onSuccess: async () => {
      setCreateOpen(false)
      setCreateError(null)
      await queryClient.invalidateQueries({ queryKey: ['questions'] })
    },
    onError: setCreateError,
  })
  const updateMutation = useMutation({
    mutationFn: ({ id, value }: { id: number; value: QuestionInput }) =>
      api.updateQuestion(id, value),
    onSuccess: async () => {
      setEditingId(null)
      await queryClient.invalidateQueries({ queryKey: ['questions'] })
    },
  })
  const deleteMutation = useMutation({
    mutationFn: api.deleteQuestion,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['questions'] }),
  })
  const experienceQuery = useQuery({
    queryKey: ['experiences'],
    queryFn: api.experiences,
  })

  function submitNewQuestion(value: QuestionInput) {
    createMutation.mutate(value)
  }

  return (
    <div className="knowledge-content">
      <Card className="editor-card">
        <CardHeader className="editor-card-header">
          <div className="editor-title">
            <div className="editor-icon">
              <Plus aria-hidden="true" size={17} />
            </div>
            <div>
              <h2>{createOpen ? 'Nueva pregunta' : 'Banco de preguntas'}</h2>
              <p>Las preguntas se guardan en la base de datos local.</p>
            </div>
          </div>
          <Button
            onClick={() => {
              setCreateOpen((current) => !current)
              setCreateError(null)
            }}
            variant={createOpen ? 'ghost' : 'outline'}
          >
            {createOpen ? <X size={15} /> : <Plus size={15} />}
            {createOpen ? 'Cancelar' : 'Añadir pregunta'}
          </Button>
        </CardHeader>
        {createOpen && (
          <CardContent>
              <ApiFeedback error={experienceQuery.error} />
            <QuestionForm
              categories={[]}
              experiences={experienceQuery.data?.results ?? []}
              error={createError}
              onCancel={() => setCreateOpen(false)}
              onSave={submitNewQuestion}
              pending={createMutation.isPending}
              submitLabel="Guardar pregunta"
            />
          </CardContent>
        )}
      </Card>

      <div className="filter-row">
        <label className="search-field">
          <Search aria-hidden="true" size={16} />
          <span className="sr-only">Buscar preguntas</span>
          <input
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder="Buscar en preguntas y respuestas"
            value={search}
          />
        </label>
        <label className="filter-select">
          <span className="sr-only">Filtrar por categoría</span>
          <select
            onChange={(event) => onCategoryChange(event.target.value)}
            value={category}
          >
            <option value="">Todas las categorías</option>
            {categories.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      <ApiFeedback error={queryError} />
      <ApiFeedback error={createMutation.error} />
      {queryLoading ? (
        <LoadingPanel label="Cargando preguntas…" />
      ) : questions.length === 0 ? (
        <EmptyPanel
          description="Añade una pregunta para empezar a preparar tus entrevistas. El listado refleja únicamente datos guardados."
          title="Todavía no hay preguntas"
        />
      ) : (
        <div className="question-list">
          {questions.map((question) => (
            <Card className="question-card" key={question.id}>
              <CardContent className="question-card-content">
                {editingId === question.id ? (
                  <QuestionForm
                  categories={categories}
                  experiences={experienceQuery.data?.results ?? []}
                  error={updateMutation.error}
                  initial={question}
                  onCancel={() => setEditingId(null)}
                  onSave={(value) =>
                    updateMutation.mutate({ id: question.id, value })
                  }
                  pending={updateMutation.isPending}
                  submitLabel="Guardar cambios"
                  />
                ) : (
                  <>
                  <div className="question-heading">
                    <div>
                      <div className="question-category">
                        {question.category.name}
                      </div>
                      <h2>{question.question}</h2>
                    </div>
                    <div className="row-actions">
                      <Button
                        onClick={() => setEditingId(question.id)}
                        size="sm"
                        variant="outline"
                      >
                        Editar
                      </Button>
                      <Button
                        aria-label={`Eliminar pregunta: ${question.question}`}
                        onClick={() => {
                          if (
                            window.confirm(
                              '¿Eliminar esta pregunta y sus respuestas y variantes?',
                            )
                          ) {
                            deleteMutation.mutate(question.id)
                          }
                        }}
                        size="icon"
                        variant="ghost"
                      >
                        <Trash2 aria-hidden="true" size={15} />
                      </Button>
                    </div>
                  </div>
                  <div className="chip-row">
                    {question.tags.map((tag) => (
                      <span className="data-chip" key={tag.id}>
                        <TagIcon aria-hidden="true" size={12} />
                        {tag.name}
                      </span>
                    ))}
                    {question.professional_experiences.map((item) => (
                      <span className="data-chip" key={item.id}>
                        {item.position} · {item.company_or_project}
                      </span>
                    ))}
                  </div>
                  <QuestionRelatedContent question={question} />
                  </>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
      {deleteMutation.error && <ApiFeedback error={deleteMutation.error} />}
    </div>
  )
}

function QuestionForm({
  categories: categoriesProp,
  experiences,
  initial,
  error,
  onSave,
  onCancel,
  pending,
  submitLabel,
}: {
  categories: Category[]
  experiences: ProfessionalExperience[]
  initial?: Question
  error: unknown
  onSave: (value: QuestionInput) => void
  onCancel: () => void
  pending: boolean
  submitLabel: string
}) {
  const categoriesQuery = useQuery({
    queryKey: ['categories'],
    queryFn: api.categories,
    enabled: categoriesProp.length === 0,
  })
  const tagsQuery = useQuery({ queryKey: ['tags'], queryFn: api.tags })
  const categories =
    categoriesProp.length > 0
      ? categoriesProp
      : categoriesQuery.data?.results ?? []
  const tags = tagsQuery.data?.results ?? []
  const [question, setQuestion] = useState(initial?.question ?? '')
  const [categoryId, setCategoryId] = useState(
    initial ? String(initial.category.id) : '',
  )
  const [tagIds, setTagIds] = useState<number[]>(
    initial?.tags.map((tag) => tag.id) ?? [],
  )
  const [experienceIds, setExperienceIds] = useState<number[]>(
    initial?.professional_experiences.map((item) => item.id) ?? [],
  )

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    onSave({
      question: question.trim(),
      category_id: Number(categoryId),
      tag_ids: tagIds,
      professional_experience_ids: experienceIds,
    })
  }

  function toggleId(
    selected: number[],
    value: number,
    setSelected: (next: number[]) => void,
  ) {
    setSelected(
      selected.includes(value)
        ? selected.filter((item) => item !== value)
        : [...selected, value],
    )
  }

  return (
    <form className="data-form" onSubmit={submit}>
      {(categoriesQuery.error || tagsQuery.error) && (
        <ApiFeedback error={categoriesQuery.error ?? tagsQuery.error} />
      )}
      <label className="form-field form-field-wide">
        <span>Pregunta <b aria-hidden="true">*</b></span>
        <textarea
          aria-label="Pregunta"
          onChange={(event) => setQuestion(event.target.value)}
          required
          rows={2}
          value={question}
        />
        <FieldErrors error={error} field="question" />
      </label>
      <label className="form-field">
        <span>Categoría <b aria-hidden="true">*</b></span>
        <select
          onChange={(event) => setCategoryId(event.target.value)}
          required
          value={categoryId}
        >
          <option value="">Selecciona una categoría</option>
          {categories.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
        <FieldErrors error={error} field="category_id" />
      </label>
      <div className="form-field">
        <span>Etiquetas</span>
        <div className="checkbox-options">
          {tags.length ? (
            tags.map((tag) => (
              <label className="check-option" key={tag.id}>
                <input
                  checked={tagIds.includes(tag.id)}
                  onChange={() => toggleId(tagIds, tag.id, setTagIds)}
                  type="checkbox"
                />
                {tag.name}
              </label>
            ))
          ) : (
            <span className="form-hint">No hay etiquetas creadas.</span>
          )}
        </div>
        <FieldErrors error={error} field="tag_ids" />
      </div>
      <div className="form-field form-field-wide">
        <span>Experiencias relacionadas</span>
        <div className="checkbox-options">
          {experiences.length ? (
            experiences.map((experience) => (
              <label className="check-option" key={experience.id}>
                <input
                  checked={experienceIds.includes(experience.id)}
                  onChange={() =>
                    toggleId(experienceIds, experience.id, setExperienceIds)
                  }
                  type="checkbox"
                />
                {experience.position} · {experience.company_or_project}
              </label>
            ))
          ) : (
            <span className="form-hint">No hay experiencias creadas.</span>
          )}
        </div>
        <FieldErrors error={error} field="professional_experience_ids" />
      </div>
      {error != null && <FormError error={error} />}
      <div className="form-actions form-field-wide">
        <Button disabled={pending || categories.length === 0} type="submit">
          {pending ? <LoaderCircle className="icon-spin" size={15} /> : <Check size={15} />}
          {submitLabel}
        </Button>
        <Button onClick={onCancel} type="button" variant="ghost">
          Cancelar
        </Button>
      </div>
    </form>
  )
}

function QuestionRelatedContent({ question }: { question: Question }) {
  const queryClient = useQueryClient()
  const [newAnswer, setNewAnswer] = useState('')
  const [newVariant, setNewVariant] = useState('')
  const [editingAnswer, setEditingAnswer] = useState<number | null>(null)
  const [editingVariant, setEditingVariant] = useState<number | null>(null)
  const [answerDraft, setAnswerDraft] = useState('')
  const [variantDraft, setVariantDraft] = useState('')
  const [error, setError] = useState<unknown>(null)
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['questions'] })
  const createAnswer = useMutation({
    mutationFn: () => api.createAnswer(question.id, newAnswer.trim()),
    onSuccess: async () => {
      setNewAnswer('')
      setError(null)
      await refresh()
    },
    onError: setError,
  })
  const createVariant = useMutation({
    mutationFn: () => api.createVariant(question.id, newVariant.trim()),
    onSuccess: async () => {
      setNewVariant('')
      setError(null)
      await refresh()
    },
    onError: setError,
  })
  const updateAnswer = useMutation({
    mutationFn: () => api.updateAnswer(editingAnswer!, answerDraft.trim()),
    onSuccess: async () => {
      setEditingAnswer(null)
      await refresh()
    },
    onError: setError,
  })
  const updateVariant = useMutation({
    mutationFn: () => api.updateVariant(editingVariant!, variantDraft.trim()),
    onSuccess: async () => {
      setEditingVariant(null)
      await refresh()
    },
    onError: setError,
  })
  const deleteAnswer = useMutation({
    mutationFn: api.deleteAnswer,
    onSuccess: refresh,
    onError: setError,
  })
  const deleteVariant = useMutation({
    mutationFn: api.deleteVariant,
    onSuccess: refresh,
    onError: setError,
  })

  function submitText(
    event: FormEvent<HTMLFormElement>,
    action: () => void,
  ) {
    event.preventDefault()
    action()
  }

  return (
    <div className="related-content">
      <div className="related-column">
        <h3>Respuestas</h3>
        {question.answers.length ? (
          <ul className="related-list">
            {question.answers.map((answer) => (
              <li className="related-item" key={answer.id}>
                {editingAnswer === answer.id ? (
                  <form
                    className="related-edit-form"
                    onSubmit={(event) =>
                      submitText(event, () => updateAnswer.mutate())
                    }
                  >
                    <textarea
                      aria-label="Editar respuesta"
                      onChange={(event) => setAnswerDraft(event.target.value)}
                      required
                      value={answerDraft}
                    />
                    <Button disabled={updateAnswer.isPending} size="sm" type="submit">
                      Guardar
                    </Button>
                    <Button
                      onClick={() => setEditingAnswer(null)}
                      size="sm"
                      type="button"
                      variant="ghost"
                    >
                      Cancelar
                    </Button>
                  </form>
                ) : (
                  <>
                    <p>{answer.text}</p>
                    <div className="row-actions">
                      <Button
                        onClick={() => {
                          setEditingAnswer(answer.id)
                          setAnswerDraft(answer.text)
                        }}
                        size="sm"
                        variant="ghost"
                      >
                        Editar
                      </Button>
                      <Button
                        aria-label="Eliminar respuesta"
                        onClick={() => {
                          if (window.confirm('¿Eliminar esta respuesta?')) {
                            deleteAnswer.mutate(answer.id)
                          }
                        }}
                        size="icon"
                        variant="ghost"
                      >
                        <Trash2 size={14} />
                      </Button>
                    </div>
                  </>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <p className="related-empty">Todavía no hay respuestas.</p>
        )}
        <form
          className="related-add-form"
          onSubmit={(event) => submitText(event, () => createAnswer.mutate())}
        >
          <label className="sr-only" htmlFor={`answer-${question.id}`}>
            Añadir respuesta
          </label>
          <textarea
            id={`answer-${question.id}`}
            onChange={(event) => setNewAnswer(event.target.value)}
            placeholder="Escribe una respuesta…"
            required
            rows={2}
            value={newAnswer}
          />
          <Button
            aria-label="Añadir respuesta"
            disabled={createAnswer.isPending || !newAnswer.trim()}
            size="sm"
            type="submit"
            variant="outline"
          >
            <Plus size={14} />
            Añadir
          </Button>
        </form>
      </div>

      <div className="related-column">
        <h3>Variantes</h3>
        {question.variants.length ? (
          <ul className="related-list">
            {question.variants.map((variant) => (
              <li className="related-item" key={variant.id}>
                {editingVariant === variant.id ? (
                  <form
                    className="related-edit-form"
                    onSubmit={(event) =>
                      submitText(event, () => updateVariant.mutate())
                    }
                  >
                    <textarea
                      aria-label="Editar variante"
                      onChange={(event) => setVariantDraft(event.target.value)}
                      required
                      value={variantDraft}
                    />
                    <Button disabled={updateVariant.isPending} size="sm" type="submit">
                      Guardar
                    </Button>
                    <Button
                      onClick={() => setEditingVariant(null)}
                      size="sm"
                      type="button"
                      variant="ghost"
                    >
                      Cancelar
                    </Button>
                  </form>
                ) : (
                  <>
                    <p>{variant.text}</p>
                    <div className="row-actions">
                      <Button
                        onClick={() => {
                          setEditingVariant(variant.id)
                          setVariantDraft(variant.text)
                        }}
                        size="sm"
                        variant="ghost"
                      >
                        Editar
                      </Button>
                      <Button
                        aria-label="Eliminar variante"
                        onClick={() => {
                          if (window.confirm('¿Eliminar esta variante?')) {
                            deleteVariant.mutate(variant.id)
                          }
                        }}
                        size="icon"
                        variant="ghost"
                      >
                        <Trash2 size={14} />
                      </Button>
                    </div>
                  </>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <p className="related-empty">Todavía no hay variantes.</p>
        )}
        <form
          className="related-add-form"
          onSubmit={(event) => submitText(event, () => createVariant.mutate())}
        >
          <label className="sr-only" htmlFor={`variant-${question.id}`}>
            Añadir variante
          </label>
          <textarea
            id={`variant-${question.id}`}
            onChange={(event) => setNewVariant(event.target.value)}
            placeholder="Escribe otra formulación…"
            required
            rows={2}
            value={newVariant}
          />
          <Button
            aria-label="Añadir variante"
            disabled={createVariant.isPending || !newVariant.trim()}
            size="sm"
            type="submit"
            variant="outline"
          >
            <Plus size={14} />
            Añadir
          </Button>
        </form>
      </div>
      {error != null && (
        <div className="form-field-wide">
          <FormError error={error} />
        </div>
      )}
    </div>
  )
}

function NameListSection<T extends { id: number; name: string }>({
  icon,
  label,
  onCreate,
  onDelete,
  onUpdate,
  query,
  queryKey,
  title,
}: {
  icon?: React.ReactNode
  label: string
  onCreate: (name: string) => Promise<T>
  onDelete: (id: number) => Promise<void>
  onUpdate: (id: number, name: string) => Promise<T>
  query: { data?: ApiPage<T>; error: unknown; isLoading: boolean }
  queryKey: string
  title: string
}) {
  const queryClient = useQueryClient()
  const [name, setName] = useState('')
  const [editing, setEditing] = useState<number | null>(null)
  const [draft, setDraft] = useState('')
  const [error, setError] = useState<unknown>(null)
  const refresh = () => queryClient.invalidateQueries({ queryKey: [queryKey] })
  const createMutation = useMutation({
    mutationFn: onCreate,
    onSuccess: async () => {
      setName('')
      setError(null)
      await refresh()
    },
    onError: setError,
  })
  const updateMutation = useMutation({
    mutationFn: ({ id, value }: { id: number; value: string }) =>
      onUpdate(id, value),
    onSuccess: async () => {
      setEditing(null)
      await refresh()
    },
    onError: setError,
  })
  const deleteMutation = useMutation({
    mutationFn: onDelete,
    onSuccess: refresh,
    onError: setError,
  })

  function submitCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    createMutation.mutate(name.trim())
  }

  return (
    <div className="management-grid">
      <Card className="editor-card">
        <CardHeader className="editor-card-header">
          <div className="editor-title">
            <div className="editor-icon">{icon ?? <BookOpen size={17} />}</div>
            <div>
              <h2>{title}</h2>
              <p>Gestiona los nombres de {label}s disponibles.</p>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <form className="inline-create-form" onSubmit={submitCreate}>
            <label className="sr-only" htmlFor={`new-${label}`}>
              Nombre de {label}
            </label>
            <input
              id={`new-${label}`}
              maxLength={100}
              onChange={(event) => setName(event.target.value)}
              placeholder={`Nombre de ${label}`}
              required
              value={name}
            />
            <Button disabled={createMutation.isPending || !name.trim()} type="submit">
              <Plus size={15} />
              Añadir
            </Button>
          </form>
          {error != null && <FormError error={error} />}
        </CardContent>
      </Card>

      <Card className="editor-card">
        <CardContent className="name-list-content">
          {query.isLoading ? (
            <LoadingPanel label={`Cargando ${title.toLowerCase()}…`} />
          ) : query.error ? (
            <ApiFeedback error={query.error} />
          ) : query.data?.results.length ? (
            query.data.results.map((item) => (
              <div className="name-list-row" key={item.id}>
                {editing === item.id ? (
                  <form
                    className="inline-edit-form"
                    onSubmit={(event) => {
                      event.preventDefault()
                      updateMutation.mutate({ id: item.id, value: draft.trim() })
                    }}
                  >
                    <input
                      aria-label={`Editar ${label}`}
                      maxLength={100}
                      onChange={(event) => setDraft(event.target.value)}
                      required
                      value={draft}
                    />
                    <Button disabled={updateMutation.isPending} size="icon" type="submit">
                      <Check size={15} />
                    </Button>
                    <Button
                      onClick={() => setEditing(null)}
                      size="icon"
                      type="button"
                      variant="ghost"
                    >
                      <X size={15} />
                    </Button>
                  </form>
                ) : (
                  <>
                    <span className="name-list-label">
                      {icon ?? <TagIcon aria-hidden="true" size={14} />}
                      {item.name}
                    </span>
                    <div className="row-actions">
                      <Button
                        onClick={() => {
                          setEditing(item.id)
                          setDraft(item.name)
                        }}
                        size="sm"
                        variant="ghost"
                      >
                        Editar
                      </Button>
                      <Button
                        aria-label={`Eliminar ${label} ${item.name}`}
                        onClick={() => {
                          if (
                            window.confirm(
                              `¿Eliminar la ${label} «${item.name}»?`,
                            )
                          ) {
                            deleteMutation.mutate(item.id)
                          }
                        }}
                        size="icon"
                        variant="ghost"
                      >
                        <Trash2 size={14} />
                      </Button>
                    </div>
                  </>
                )}
              </div>
            ))
          ) : (
            <EmptyPanel
              description={`Crea una ${label} para poder asignarla a tus preguntas.`}
              title={`Todavía no hay ${label}s`}
            />
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function LoadingPanel({ label }: { label: string }) {
  return (
    <div className="state-panel" role="status">
      <LoaderCircle aria-hidden="true" className="icon-spin" size={19} />
      {label}
    </div>
  )
}

function EmptyPanel({
  description,
  title,
}: {
  description: string
  title: string
}) {
  return (
    <Card className="empty-card">
      <CardContent className="empty-content">
        <div className="empty-icon">
          <CircleAlert aria-hidden="true" size={19} />
        </div>
        <h2>{title}</h2>
        <p>{description}</p>
      </CardContent>
    </Card>
  )
}
