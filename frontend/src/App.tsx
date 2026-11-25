import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import {
  Activity,
  ArrowRight,
  BookOpen,
  BriefcaseBusiness,
  Check,
  LayoutDashboard,
  LoaderCircle,
  LogOut,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  UserRound,
  Wifi,
  WifiOff,
} from 'lucide-react'
import {
  BrowserRouter,
  Link,
  Navigate,
  NavLink,
  Route,
  Routes,
  useLocation,
} from 'react-router-dom'

import { api } from '@/api/client'
import type { SessionState } from '@/api/types'
import { ApiFeedback } from '@/components/ApiFeedback'
import { LoginPanel } from '@/components/AuthPanel'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { ExperiencesPage } from '@/pages/ExperiencesPage'
import { KnowledgePage } from '@/pages/KnowledgePage'
import { ProfilePage } from '@/pages/ProfilePage'

type ConnectionStatus = 'checking' | 'available' | 'unavailable'

const navigation = [
  { label: 'Resumen', to: '/', icon: LayoutDashboard, end: true },
  { label: 'Conocimiento', to: '/conocimiento', icon: BookOpen },
  { label: 'Perfil', to: '/perfil', icon: UserRound },
  { label: 'Experiencias', to: '/experiencias', icon: BriefcaseBusiness },
]

function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <Link aria-label="Interview AI Assistant, ir al resumen" className="brand" to="/">
      <span aria-hidden="true" className="brand-mark">
        <Sparkles size={19} strokeWidth={2.2} />
      </span>
      {!compact && (
        <span className="brand-copy">
          <span className="brand-name">Interview AI</span>
          <span className="brand-caption">ASSISTANT</span>
        </span>
      )}
    </Link>
  )
}

function NavigationLinks() {
  return (
    <>
      {navigation.map(({ label, to, icon: Icon, ...options }) => (
        <NavLink
          aria-label={label}
          className={({ isActive }) =>
            `nav-link${isActive ? ' nav-link-active' : ''}`
          }
          key={to}
          to={to}
          {...options}
        >
          <Icon aria-hidden="true" size={18} strokeWidth={1.8} />
          <span>{label}</span>
        </NavLink>
      ))}
    </>
  )
}

function ConnectionStatus({
  status,
  compact = false,
}: {
  status: ConnectionStatus
  compact?: boolean
}) {
  const Icon =
    status === 'available' ? Wifi : status === 'unavailable' ? WifiOff : Activity
  const label =
    status === 'available'
      ? 'API disponible'
      : status === 'unavailable'
        ? 'API no disponible'
        : 'Comprobando conexión'

  return (
    <span
      aria-live="polite"
      className={`connection-status connection-${status}${compact ? ' connection-compact' : ''}`}
      role="status"
    >
      <Icon
        aria-hidden="true"
        className={status === 'checking' ? 'icon-pulse' : ''}
        size={15}
      />
      <span>{label}</span>
    </span>
  )
}

function AppShell() {
  const location = useLocation()
  const queryClient = useQueryClient()
  const healthQuery = useQuery({
    queryKey: ['api-health'],
    queryFn: api.health,
    retry: false,
    refetchOnWindowFocus: false,
  })
  const sessionQuery = useQuery({
    queryKey: ['api-session'],
    queryFn: api.session,
    retry: false,
  })
  const logoutMutation = useMutation({
    mutationFn: api.logout,
    onSuccess: async () => {
      queryClient.setQueryData<SessionState>(['api-session'], {
        authenticated: false,
        user: null,
      })
      await queryClient.invalidateQueries({ queryKey: ['api-session'] })
    },
  })
  useEffect(() => {
    const onExpired = () => {
      queryClient.setQueryData<SessionState>(['api-session'], {
        authenticated: false,
        user: null,
      })
    }
    window.addEventListener('auth-session-expired', onExpired)
    return () => window.removeEventListener('auth-session-expired', onExpired)
  }, [queryClient])
  const connectionStatus: ConnectionStatus = healthQuery.isFetching
    ? 'checking'
    : healthQuery.isError
      ? 'unavailable'
      : 'available'
  const pageTitle =
    navigation.find((item) => item.to === location.pathname)?.label ?? 'Resumen'
  const isOperator = Boolean(
    sessionQuery.data?.authenticated && sessionQuery.data.user?.is_operator,
  )

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Saltar al contenido
      </a>

      <aside aria-label="Barra lateral" className="sidebar">
        <Brand />
        <div className="sidebar-label">ESPACIO DE TRABAJO</div>
        <nav aria-label="Navegación principal" className="sidebar-nav">
          <NavigationLinks />
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-local">
            <ShieldCheck aria-hidden="true" size={17} />
            <span>Datos en tu equipo</span>
          </div>
          <div className="sidebar-caption">ENTORNO LOCAL · INTERVIEW AI</div>
        </div>
      </aside>

      <div className="main-column">
        <div className="mobile-header">
          <div className="mobile-brand-row">
            <Brand />
            <ConnectionStatus compact status={connectionStatus} />
          </div>
          <nav aria-label="Navegación móvil" className="mobile-nav">
            <NavigationLinks />
          </nav>
        </div>

        <header className="topbar">
          <div className="topbar-heading">
            <span className="topbar-kicker">PANEL LOCAL</span>
            <span aria-hidden="true" className="topbar-divider">
              /
            </span>
            <span>{pageTitle}</span>
          </div>
          <div className="topbar-local">
            <span aria-hidden="true" className="local-indicator" />
            {isOperator ? (
              <>
                <span className="operator-name">
                  {sessionQuery.data?.user?.username}
                </span>
                <Button
                  aria-label="Cerrar sesión"
                  disabled={logoutMutation.isPending}
                  onClick={() => logoutMutation.mutate()}
                  size="sm"
                  variant="ghost"
                >
                  <LogOut aria-hidden="true" size={15} />
                  Salir
                </Button>
              </>
            ) : (
              'Entorno local'
            )}
          </div>
        </header>

        <main className="page-content" id="main-content">
          {sessionQuery.isLoading ? (
            <div className="state-panel" role="status">
              <LoaderCircle aria-hidden="true" className="icon-spin" size={19} />
              Comprobando sesión del operador…
            </div>
          ) : sessionQuery.isError ? (
            <div className="auth-page">
              <ApiFeedback error={sessionQuery.error} />
              <Button
                onClick={() => void sessionQuery.refetch()}
                variant="outline"
              >
                <RefreshCw aria-hidden="true" size={15} />
                Reintentar conexión
              </Button>
            </div>
          ) : !sessionQuery.data?.authenticated ? (
            <LoginPanel connectionAvailable={healthQuery.isSuccess} />
          ) : !isOperator ? (
            <div className="auth-page">
              <ApiFeedback
                error={new Error('Tu cuenta no tiene permisos de operador.')}
              />
            </div>
          ) : (
            <>
              {logoutMutation.error && <ApiFeedback error={logoutMutation.error} />}
              <Routes>
                <Route
                  element={
                    <Dashboard
                      connectionStatus={connectionStatus}
                      isChecking={healthQuery.isFetching}
                      onCheck={() => void healthQuery.refetch()}
                    />
                  }
                  path="/"
                />
                <Route element={<KnowledgePage />} path="/conocimiento" />
                <Route element={<ProfilePage />} path="/perfil" />
                <Route element={<ExperiencesPage />} path="/experiencias" />
                <Route element={<Navigate replace to="/" />} path="*" />
              </Routes>
            </>
          )}
        </main>

        <footer className="page-footer">
          <span>Interview AI Assistant</span>
          <span>Procesamiento local · Sin servicios externos</span>
        </footer>
      </div>
    </div>
  )
}

function Dashboard({
  connectionStatus,
  isChecking,
  onCheck,
}: {
  connectionStatus: ConnectionStatus
  isChecking: boolean
  onCheck: () => void
}) {
  const cards = [
    {
      title: 'Conocimiento',
      description:
        'Preguntas, respuestas, variantes, categorías y etiquetas.',
      to: '/conocimiento',
      icon: BookOpen,
      label: '01',
    },
    {
      title: 'Perfil',
      description: 'Tu información profesional y enlaces de referencia.',
      to: '/perfil',
      icon: UserRound,
      label: '02',
    },
    {
      title: 'Experiencias',
      description: 'Proyectos, responsabilidades y logros.',
      to: '/experiencias',
      icon: BriefcaseBusiness,
      label: '03',
    },
  ]

  return (
    <div className="dashboard-page">
      <section aria-labelledby="welcome-title" className="hero-panel">
        <div className="hero-content">
          <div className="eyebrow">
            <span aria-hidden="true" className="eyebrow-dot" />
            TU ESPACIO DE PREPARACIÓN
          </div>
          <h1 id="welcome-title">Prepara tu próxima entrevista</h1>
          <p>
            Organiza tu conocimiento profesional y accede a tus herramientas de
            preparación desde un único espacio privado.
          </p>
          <Button asChild className="hero-action" size="lg">
            <Link to="/conocimiento">
              Ir al banco de preguntas
              <ArrowRight aria-hidden="true" size={17} />
            </Link>
          </Button>
        </div>
        <div aria-hidden="true" className="hero-decoration">
          <div className="orbit orbit-one" />
          <div className="orbit orbit-two" />
          <div className="hero-sparkle">
            <Sparkles size={32} strokeWidth={1.5} />
          </div>
          <div className="hero-glow" />
        </div>
        <div className="hero-footnote">
          <ShieldCheck aria-hidden="true" size={14} />
          Privado por diseño
        </div>
      </section>

      <section aria-labelledby="workspace-title" className="workspace-section">
        <div className="section-heading">
          <div>
            <div className="section-eyebrow">TU ESPACIO</div>
            <h2 id="workspace-title">Todo lo que necesitas, a mano</h2>
          </div>
          <span className="section-note">3 áreas de trabajo</span>
        </div>

        <div className="overview-grid">
          {cards.map(({ title, description, to, icon: Icon, label }) => (
            <Link
              aria-label={`Abrir ${title}`}
              className="overview-link"
              key={to}
              to={to}
            >
              <Card className="overview-card">
                <CardHeader className="overview-card-header">
                  <div className="overview-icon">
                    <Icon aria-hidden="true" size={20} strokeWidth={1.8} />
                  </div>
                  <span className="card-index">{label}</span>
                </CardHeader>
                <CardContent className="overview-card-content">
                  <div className="overview-title-row">
                    <h3>{title}</h3>
                    <ArrowRight
                      aria-hidden="true"
                      className="card-arrow"
                      size={17}
                    />
                  </div>
                  <p>{description}</p>
                  <span className="workspace-available">
                    <Check aria-hidden="true" size={13} />
                    Gestión disponible
                  </span>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      </section>

      <section aria-labelledby="connection-title" className="connection-section">
        <Card className="connection-card">
          <CardContent className="connection-content">
            <div className="connection-symbol">
              <Activity aria-hidden="true" size={19} />
            </div>
            <div className="connection-copy">
              <div className="connection-heading-row">
                <h2 id="connection-title">Conexión con Django</h2>
                <ConnectionStatus status={connectionStatus} />
              </div>
              <p>
                Comprobación real de <code>GET /api/health/</code> a través del
                proxy local.
              </p>
            </div>
            <Button
              aria-label="Comprobar conexión con Django"
              disabled={isChecking}
              onClick={onCheck}
              variant="outline"
            >
              {isChecking ? (
                <LoaderCircle aria-hidden="true" className="icon-spin" size={16} />
              ) : (
                <RefreshCw aria-hidden="true" size={15} />
              )}
              Comprobar
            </Button>
          </CardContent>
        </Card>
        {connectionStatus === 'unavailable' && (
          <p className="connection-help" role="note">
            El panel sigue disponible. Inicia Django en{' '}
            <code>127.0.0.1:8000</code> y vuelve a comprobar.
          </p>
        )}
      </section>

      <div aria-label="Alcance actual" className="scope-note" role="note">
        <Check aria-hidden="true" size={15} />
        <span>
          El perfil, las experiencias y la base de conocimiento se consultan y
          guardan mediante la API local protegida por sesión.
        </span>
      </div>
    </div>
  )
}

function App() {
  return (
    <BrowserRouter>
      <AppShell />
    </BrowserRouter>
  )
}

export default App
