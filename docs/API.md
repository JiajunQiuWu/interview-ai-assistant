# Contrato de la API local

Este documento describe la API REST local de Interview AI Assistant. Las rutas
marcadas **Implementado** están disponibles en Django; las marcadas
**Propuesta** aún no forman parte del backend. Django Admin continúa disponible
en `/admin/`.

La API gestiona la base local existente; no crea modelos paralelos ni expone las
claves de intercambio como identificadores normales de recursos. Los recursos
REST usan las claves primarias Django (`id`) para sus relaciones.
`exchange_key` se reserva para los formatos de importación y exportación.

## Alcance y supuestos

- La aplicación tiene un único operador local, con una cuenta Django activa y
  `is_staff=True`. Se creará o administrará desde Django Admin o con
  `createsuperuser`. No se propone registro público, cambio de contraseña ni
  administración de cuentas desde React.
- El perfil es global y singleton, no pertenece a un usuario Django. Las
  experiencias profesionales se relacionan con preguntas mediante una relación
  muchos-a-muchos opcional.
- Las respuestas y variantes pertenecen a una pregunta y se gestionan como
  recursos propios.
- La API solo servirá JSON, salvo las descargas de exportación. No se incluyen
  endpoints REST para grabaciones ni transcripciones en esta entrega.
- Los nombres y relaciones reflejan los modelos actuales de `knowledge_base`
  y `transcriptions`.

## Acceso local y sesiones

1. React enviará las credenciales de la única cuenta operadora a
   `POST /api/auth/login/`. El servidor validará con `django.contrib.auth`,
   iniciará una sesión con `django.contrib.auth.login()` y responderá con una
   cookie de sesión de Django. La contraseña solo se mantiene en el formulario
   durante el inicio de sesión.
2. La cookie de sesión será `HttpOnly`; React no intentará leerla. El navegador
   la adjuntará a las peticiones del mismo origen. Las llamadas usarán rutas
   relativas `/api/...` y `credentials: "same-origin"`.
3. Antes del inicio de sesión, React llamará a `GET /api/auth/csrf/`. La
   respuesta establecerá la cookie CSRF y devolverá un token utilizable. React
   mantendrá el token en memoria y lo enviará en `X-CSRFToken` en cada método
   inseguro (`POST`, `PUT`, `PATCH`, `DELETE`), incluido el inicio de sesión.
   No se guardará el token en `localStorage`.
4. Django rota el token CSRF al iniciar sesión; el token nuevo viene en la
   respuesta de login y el cliente lo conserva en memoria. Tras cerrar sesión,
   React consulta de nuevo `GET /api/auth/session/`. El token deja de
   conservarse en memoria y React vuelve a pedirlo con
   `GET /api/auth/csrf/` antes del próximo inicio de sesión.
5. `GET /api/auth/session/` no exige sesión: devuelve
   `{"authenticated": false, "user": null}` si no hay operador autenticado, o
   `{"authenticated": true, "user": {"username": "...", "is_operator": true}}`
   si el usuario autenticado es staff. Para una sesión válida no staff,
   `is_operator` será `false`; esa cuenta no podrá acceder a datos de negocio.
   Esta ruta permite inicializar la interfaz sin exponer perfil ni datos de
   entrevistas.
6. `POST /api/auth/logout/` cierra la sesión Django y requiere sesión y CSRF.

### Vite, origen y escucha

Vite está configurado para escuchar en `127.0.0.1:5173` y reenviar `/api/` a
`http://127.0.0.1:8000`, sin cambiar el encabezado `Origin`. Se admite también
arrancar Vite en el puerto alternativo `5174`; ambos orígenes están incluidos
en `CSRF_TRUSTED_ORIGINS`. Django debe arrancarse ligado explícitamente a
`127.0.0.1:8000`. React usa rutas relativas `/api/...` y no llama directamente
al puerto 8000. Se debe mantener el mismo host literal `127.0.0.1` en el
navegador, Vite y Django: `localhost` y `127.0.0.1` son orígenes y hosts de
cookie diferentes. No se ha habilitado CORS.

La configuración real usa `SessionAuthentication` y `IsAdminUser` por defecto,
con solo `JSONRenderer`. La cookie de sesión es HttpOnly y, en el desarrollo
HTTP local, se aplican los valores predeterminados de Django para cookies
(`SameSite=Lax`; CSRF legible por JavaScript). Los procesos deben permanecer
ligados a loopback, no a interfaces de red externas.

### Códigos HTTP verificados y permisos

Comportamiento comprobado y codificado:

- DRF autentica por `SessionAuthentication` únicamente; su permiso global es
  `IsAdminUser`.
- El acceso anónimo a datos privados y el acceso de usuario autenticado no
  staff producen **403**, no 401, porque `SessionAuthentication` no proporciona
  un desafío `WWW-Authenticate`.
- Una petición insegura con sesión y sin token CSRF produce **403**. El error
  normalizado devuelve `code: "csrf_failed"`.
- `GET /api/health/`, `GET /api/auth/csrf/`,
  `GET /api/auth/session/` y `POST /api/auth/login/` son accesibles sin sesión.
  Login está protegido explícitamente con `csrf_protect`, también para clientes
  anónimos. Logout requiere operador staff y CSRF.
- Las rutas de sesión privadas del negocio usan `IsAdminUser`. Solo una cuenta
  Django activa con `is_staff=True` puede consultar o modificar perfil,
  experiencias, preguntas, respuestas, variantes, categorías y etiquetas.
  El login rechaza cuentas que no sean staff.
- `GET /api/auth/session/` y los errores distinguen sesión anónima
  (`not_authenticated`) de permisos insuficientes (`permission_denied`). React
  no debe tratar todo 403 como una sesión caducada.

## Convenciones de recursos

### Paginación y filtros

Las colecciones REST implementadas devuelven el formato paginado:

```json
{
  "count": 42,
  "next": null,
  "previous": null,
  "results": []
}
```

Se pagina por número de página (`page`, `page_size`), tamaño predeterminado 20
y máximo 100. Las preguntas aceptan filtros `category`, `tag` y
`professional_experience`, y búsqueda `search` sobre pregunta, respuesta,
variante y nombre de etiqueta; las uniones no duplican preguntas. Las
experiencias aceptan `question`, `current=true` y `search`. Las consultas de
categorías y etiquetas no definen orden explícito; las preguntas se ordenan por
categoría, texto y clave primaria; las respuestas y variantes siguen su orden
de modelo/clave; experiencias por inicio descendente, cargo y clave primaria.
No se implementó el parámetro `ordering`.

### Campos y relaciones

- Una pregunta requiere `question` y `category_id`. `tag_ids` y
  `professional_experience_ids` son listas opcionales; una lista vacía elimina
  sus asociaciones. La salida incluirá la categoría, etiquetas, experiencias
  relacionadas, respuestas y variantes.
- Cada respuesta y variante requiere `question_id` y texto no vacío. No hay
  unicidad para el texto de respuestas. Una variante no se puede repetir dentro
  de la misma pregunta.
- Categoría y etiqueta requieren `name` único (máximo 100 caracteres).
- Una experiencia requiere `position`, `company_or_project`,
  `responsibilities` y `achievements`. `start_date` y `end_date` son opcionales
  (`null`); si ambas existen, `end_date` no puede ser anterior a `start_date`.
- El perfil requiere `name`; `professional_title`, `summary`, `location`,
  `linkedin_url`, `github_url` y `portfolio_url` pueden estar vacíos. Solo
  puede existir un perfil.
- Los campos de auditoría de pregunta (`created_at`, `updated_at`) serán de
  solo lectura. Los ids de relaciones serán claves primarias locales; el
  contrato de intercambio seguirá usando UUID `exchange_key`.

## Endpoints

Las rutas de sesión, conocimiento, perfil y experiencias están **Implementadas**.
Estadísticas e intercambio HTTP siguen siendo **Propuestas**.

| Estado | Ruta | Método | Permiso | Entrada principal | Salida y códigos previstos |
|---|---|---|---|---|---|
| Implementado | `/api/health/` | GET | Público (`AllowAny`) | Ninguna | `{"status":"ok"}`; 200. Es una respuesta estática: no verifica SQLite ni la transcripción. |
| Implementado | `/api/auth/csrf/` | GET | Público | Ninguna | Establece cookie CSRF y devuelve `csrfToken`; 200. |
| Implementado | `/api/auth/session/` | GET | Público | Ninguna | `authenticated` y usuario mínimo (`username`, `is_operator`) o `user: null`; 200. |
| Implementado | `/api/auth/login/` | POST | Público, con CSRF explícito | `username`, `password` | Sesión iniciada y token rotado; 200. Credenciales inválidas o no staff: 400 genérico; JSON/campos inválidos: 400; CSRF inválido: 403. |
| Implementado | `/api/auth/logout/` | POST | Operador staff y CSRF | Sin campos | Sesión cerrada; 204. Sin sesión o permisos: 403; CSRF inválido: 403. |
| Implementado | `/api/questions/` | GET | Operador staff | `category`, `tag`, `professional_experience`, `search`, `page`, `page_size` | Lista paginada; 200, 403. |
| Implementado | `/api/questions/` | POST | Operador staff y CSRF | `question`, `category_id`, opcionalmente `tag_ids`, `professional_experience_ids` | Pregunta creada con sus relaciones; 201, 400, 403. |
| Implementado | `/api/questions/{id}/` | GET | Operador staff | Ninguna | Pregunta y relaciones; 200, 403, 404. |
| Implementado | `/api/questions/{id}/` | PATCH | Operador staff y CSRF | Campos editables anteriores | Pregunta actualizada; 200, 400, 403, 404. |
| Implementado | `/api/questions/{id}/` | DELETE | Operador staff y CSRF | Ninguna | 204; elimina respuestas y variantes por cascada; 403, 404. |
| Implementado | `/api/questions/{question_id}/answers/` | GET, POST | GET: operador; POST: operador y CSRF | POST: `text` | Lista paginada o respuesta creada; 200, 201, 400, 403, 404. |
| Implementado | `/api/answers/{id}/` | GET, PATCH, DELETE | Operador; escrituras con CSRF | PATCH: `text` | Respuesta; 200, 400, 403, 404; DELETE: 204. |
| Implementado | `/api/questions/{question_id}/variants/` | GET, POST | GET: operador; POST: operador y CSRF | POST: `text` | Lista paginada o variante creada; 200, 201, 400, 403, 404. |
| Implementado | `/api/variants/{id}/` | GET, PATCH, DELETE | Operador; escrituras con CSRF | PATCH: `text` | Variante; 200, 400, 403, 404; DELETE: 204. Texto duplicado dentro de la pregunta: 400. |
| Implementado | `/api/categories/` | GET, POST | GET: operador; POST: operador y CSRF | POST: `name` | Lista paginada o categoría creada; 200, 201, 400, 403. |
| Implementado | `/api/categories/{id}/` | GET, PATCH, DELETE | GET: operador; escrituras: operador y CSRF | PATCH: `name` | Categoría; 200, 400, 403, 404; DELETE: 204 o 409 si tiene preguntas. |
| Implementado | `/api/tags/` | GET, POST | GET: operador; POST: operador y CSRF | POST: `name` | Lista paginada o etiqueta creada; 200, 201, 400, 403. |
| Implementado | `/api/tags/{id}/` | GET, PATCH, DELETE | GET: operador; escrituras: operador y CSRF | PATCH: `name` | Etiqueta; 200, 400, 403, 404; DELETE: 204 y conserva las preguntas. |
| Implementado | `/api/profile/` | GET, POST, PATCH | Operador; escrituras con CSRF | Campos del perfil | GET devuelve perfil 200 o `not_found` 404; POST crea 201 o 409 si ya existe; PATCH actualiza 200, 400, 403. No hay DELETE. |
| Implementado | `/api/experiences/` | GET, POST | GET: operador; POST: operador y CSRF | `position`, `company_or_project`, fechas opcionales, `responsibilities`, `achievements`, opcional `question_ids`; filtros `question`, `current`, `search` | Lista paginada o experiencia creada; 200, 201, 400, 403. |
| Implementado | `/api/experiences/{id}/` | GET, PATCH, DELETE | GET: operador; escrituras: operador y CSRF | Campos de experiencia | Experiencia; 200, 400, 403, 404; DELETE: 204 y elimina asociaciones, no preguntas. |
| Propuesta | `/api/stats/` | GET | Operador staff | Ninguna | Conteos reales; aún no implementado. |
| Propuesta | `/api/exchange/export/?format=json\|csv\|xlsx` | GET | Operador staff | `format` obligatorio | Descarga JSON o XLSX; CSV se descarga como ZIP del directorio CSV; 200, 400, 403. |
| Propuesta | `/api/exchange/import/` | POST | Operador staff y CSRF | `format`, archivo(s), `dry_run` opcional | Resumen de filas y resultado; 200 en simulación o importación merge exitosa; 400 en archivo/contrato inválido; 403; 413 si se supera el límite de tamaño que se configure. |

Las salidas implementadas de preguntas contienen `id`, `question`, `category`,
`tags`, `professional_experiences`, `answers`, `variants`, `created_at` y
`updated_at`. Las relaciones incluirán al menos sus `id` y campos visibles
(`name`, `position` o `text`). `Answer` y `QuestionVariant` expondrán
`id`, `question_id` y `text`. El perfil y la experiencia devolverán los campos
editables descritos arriba más `id`; `is_singleton` y `exchange_key` no serán
editables ni parte del CRUD público.

## Importación y exportación

Los comandos actuales son `import_knowledge_base` y
`export_knowledge_base`. La lógica reutilizable está en
`apps.knowledge_base.exchange`: `read_exchange`, `import_exchange`,
`export_exchange` y `build_payload`. Se reutilizarán esa validación y ese
servicio; la API no duplicará el formato ni implementará otra ruta de
persistencia. Los comandos seguirán disponibles.

Se admiten los formatos existentes: JSON v1, XLSX y CSV. JSON contiene
`format`, `version` y `tables`; XLSX usa una hoja por tabla; CSV es un directorio
con `manifest.json` y archivos por tabla. Para la futura API:

- JSON y XLSX se reciben como un archivo multipart `file`.
- CSV se recibe como varios archivos multipart `files`, incluido
  `manifest.json`; el adaptador los materializará en un directorio temporal
  validando nombres y evitando rutas fuera de ese directorio. La exportación
  CSV empaquetará el directorio generado como ZIP. Esta adaptación HTTP todavía
  no existe.
- `dry_run=true` valida el formato, las claves, las relaciones y conflictos sin
  escribir; no se ofrecerá como respuesta exitosa una importación parcial.
- La importación existente es de tipo *merge*, idempotente y transaccional:
  no borra filas ausentes del archivo y una violación de integridad revierte la
  transacción completa. Los fallos identificarán tabla/fila o ubicación del
  error.
- Las validaciones existentes incluyen versión, cabeceras, claves UUID,
  referencias, fechas, URLs de perfil, duplicados y conflictos con la base.
  Los límites de tamaño y cantidad de archivos de la API quedan pendientes de
  fijar antes de implementarla.
- La exportación existente escribe a una ruta local; el adaptador HTTP usará un
  directorio temporal y devolverá el archivo. No se añadirá persistencia de
  exportaciones ni dependencia de servicios externos.

## Formato de errores

Las rutas REST implementadas devuelven este formato para errores JSON:

```json
{
  "detail": "Hay campos que deben corregirse.",
  "code": "validation_error",
  "errors": {
    "category_id": ["La categoría indicada no existe."]
  }
}
```

Para un error general:

```json
{
  "detail": "No se puede eliminar una categoría que tiene preguntas.",
  "code": "conflict",
  "errors": {}
}
```

Los códigos implementados incluyen `not_authenticated`, `permission_denied`,
`csrf_failed`, `validation_error`, `not_found` y `conflict`. Los errores de
validación usan listas de mensajes por campo; una validación general puede
usar `errors.non_field_errors`. La vista de fallo CSRF del middleware también
devuelve el objeto normalizado. El health check devuelve `{"status":"ok"}` en
caso de éxito; los errores HTTP no JSON de infraestructura quedan fuera del
contrato de la aplicación.

## Matriz de pruebas

| Caso | Petición/condición | Resultado esperado |
|---|---|---|
| Health anónimo | GET `/api/health/` sin sesión | 200 con `{"status":"ok"}`; no incluye datos de usuario. |
| Datos anónimos | GET preguntas, perfil o experiencias sin sesión | 403 con `code: not_authenticated`; no devuelve datos personales. |
| Bootstrap CSRF | GET `/api/auth/csrf/` sin sesión | 200, token y cookie CSRF; no requiere autenticación. |
| Estado anónimo | GET `/api/auth/session/` sin sesión | 200 con `authenticated:false` y `user:null`. |
| Login sin CSRF | POST login con credenciales, pero sin token válido | 403 con `code: csrf_failed`; no inicia sesión. |
| Login válido | POST login con CSRF y credenciales correctas | 200, cookie de sesión y estado autenticado; token rotado. |
| Login inválido | POST login con CSRF y credenciales incorrectas o cuenta no staff | 400 genérico; no revela existencia de la cuenta. |
| Permiso insuficiente | GET de datos como usuario Django no staff | 403 con `code: permission_denied`. |
| Lectura autenticada | GET de datos con sesión del operador staff | 200; no requiere token CSRF por ser método seguro. |
| Escritura sin CSRF | POST/PATCH/DELETE con sesión, sin token o token incorrecto | 403 con `code: csrf_failed`; ningún cambio persistido. |
| Escritura válida | POST/PATCH/DELETE con sesión staff y token CSRF válido | Código definido para el recurso; cambios persistidos. |
| Logout | POST sin sesión, sin CSRF y con sesión+CSRF | 403, 403 y 204; sesión invalidada en el último caso. |
| Relaciones inválidas | Crear pregunta con categoría o ids relacionados inexistentes | 400 con error por campo; no se guarda la pregunta ni relaciones. |
| Validación de fechas | Experiencia con fecha fin anterior a inicio | 400 con error `end_date`; no se guarda. |
| Borrados relacionados | Eliminar pregunta, categoría protegida, etiqueta o experiencia | La pregunta elimina respuestas/variantes; categoría vinculada responde 409; etiqueta/experiencia no eliminan preguntas. |
| Perfil singleton | Crear perfil ausente y volver a crearlo | 201 en la primera creación; 409 en la segunda. |
| Intercambio HTTP | No hay ruta implementada | No aplicable hasta implementar importación/exportación REST. |

## Pendientes

- `/api/stats/` y las rutas REST de importación/exportación siguen propuestas;
  su alcance y respuesta se definirán antes de implementarlas.
- Fijar límites de tamaño y cantidad de archivos antes de aceptar intercambio
  por HTTP. Los comandos locales de intercambio sí están implementados.
- El health check es estático y no informa del estado de SQLite u otros
  servicios; una comprobación más detallada requiere acordar sus dependencias.
- Para desarrollo se usa el proxy Vite local. El despliegue empaquetado del
  frontend/API no forma parte de esta integración.
