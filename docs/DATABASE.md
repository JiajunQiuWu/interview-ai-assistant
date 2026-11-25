# Base de datos

## SQLite

Django usa `data/db.sqlite3`. La ruta se calcula con `pathlib.Path` en
`backend/config/settings.py`, a partir de la ubicación del proyecto y no del
directorio actual. El directorio `data/` y las ubicaciones locales necesarias se
crean al cargar la configuración, antes de ejecutar migraciones. La base no se
versiona.

Aplica las migraciones con:

```powershell
.\.venv\Scripts\python.exe backend\manage.py migrate
```

## Base de conocimiento

La app `apps.knowledge_base` define:

- `Category`: nombre único para clasificar preguntas.
- `Question`: categoría obligatoria, texto de la pregunta, etiquetas
  (opcionales), experiencias profesionales relacionadas (opcionales) y fechas
  de creación y actualización.
- `Answer`: respuesta obligatoria perteneciente a una pregunta; una pregunta
  puede tener varias respuestas.
- `QuestionVariant`: enunciado alternativo obligatorio perteneciente a una
  pregunta; no se repite el mismo enunciado dentro de esa pregunta.
- `Tag`: nombre obligatorio y único, asociado opcionalmente a varias preguntas.
- `ProfessionalExperience`: cargo, empresa o proyecto, fechas opcionales,
  responsabilidades y logros. El fin no puede preceder al inicio cuando ambas
  fechas están informadas. Una experiencia puede vincularse a varias preguntas;
  eliminarla no elimina las preguntas.
- `CandidateProfile`: perfil local del único candidato, con nombre obligatorio
  y titular profesional, resumen, ubicación y enlaces a LinkedIn, GitHub y
  portafolio opcionales. No se asigna a un usuario de Django: la aplicación es
  local y de un solo candidato. La base permite como máximo un perfil y no crea
  uno automáticamente.

## Nulabilidad, restricciones y borrado

- Los textos y las claves foráneas requeridas son `NOT NULL`; las fechas de
  `ProfessionalExperience` sí admiten `NULL`. Respuestas, variantes y etiquetas
  no aceptan la cadena vacía.
- `Category.name` y `Tag.name` son únicos. Una variante no puede repetirse para
  la misma pregunta. Las respuestas no tienen restricción de unicidad.
- La categoría usa `PROTECT`: no se puede borrar mientras tenga preguntas.
  Borrar una pregunta borra sus respuestas y variantes (`CASCADE`) y sus filas
  de unión con etiquetas y experiencias; no borra las etiquetas ni las
  experiencias relacionadas.
- La relación Question–Tag es opcional y muchos-a-muchos. Borrar una etiqueta
  elimina sus uniones, no las preguntas. La relación Question–
  ProfessionalExperience sigue siendo opcional y muchos-a-muchos; borrar una
  experiencia no borra preguntas.
- El perfil no tiene relación de propietario con `User`; es un registro global
  singleton de la instalación local. Su clave de intercambio permite conservar
  su identidad en importaciones y exportaciones sin cambiar los datos existentes.

La migración inicial carga las categorías Recursos Humanos, Manager y Técnica.
La migración que introduce respuestas convierte el texto anterior de
`Question.answer` en una fila de `Answer` cuando no está vacío. Al revertirla al
esquema anterior, solo puede recuperarse la primera respuesta de cada pregunta,
porque el campo anterior admitía una sola.

## Grabaciones y transcripciones

La app `apps.transcriptions` define:

- `AudioRecording`: ruta absoluta del archivo de audio (única) y fecha de
  registro. El comando solo registra archivos que existen.
- `Transcription`: texto, idioma (`es`), identificador del modelo y fecha de
  transcripción. Tiene una clave foránea obligatoria a `AudioRecording`; una
  grabación puede tener varias transcripciones.

Eliminar un registro `AudioRecording` elimina sus transcripciones relacionadas
(`CASCADE`), pero no borra el archivo del disco. La ruta se guarda localmente y
no se transmite a servicios externos.

## Intercambio local: contrato v1

Los comandos de Django exportan e importan la base completa, incluidos
`CandidateProfile`, `ProfessionalExperience` y sus vínculos con preguntas. No
usan servicios externos ni APIs de IA. Ejecuta los comandos desde la raíz en PowerShell y
aplica primero las migraciones para crear las claves de intercambio:

```powershell
.\.venv\Scripts\python.exe backend\manage.py migrate
.\.venv\Scripts\python.exe backend\manage.py export_knowledge_base --format json --output data\imports\knowledge_base.json
.\.venv\Scripts\python.exe backend\manage.py import_knowledge_base --format json --input data\imports\knowledge_base.json --dry-run
.\.venv\Scripts\python.exe backend\manage.py import_knowledge_base --format json --input data\imports\knowledge_base.json
```

`export_knowledge_base` e `import_knowledge_base` aceptan `--format json`,
`--format csv` o `--format xlsx`, y `--database default` (alias opcional de
Django). Para CSV, `--output` y `--input` son directorios; la exportación exige
que el directorio no exista o esté vacío. Para JSON y XLSX son rutas de archivo.
Ejemplos:

```powershell
.\.venv\Scripts\python.exe backend\manage.py export_knowledge_base --format csv --output data\imports\knowledge_base_csv
.\.venv\Scripts\python.exe backend\manage.py import_knowledge_base --format csv --input data\imports\knowledge_base_csv --dry-run
.\.venv\Scripts\python.exe backend\manage.py export_knowledge_base --format xlsx --output data\imports\knowledge_base.xlsx
.\.venv\Scripts\python.exe backend\manage.py import_knowledge_base --format xlsx --input data\imports\knowledge_base.xlsx
```

`--dry-run` valida el contrato, las claves, las referencias y los conflictos
con la base elegida, informa cuántas filas se importarían y no escribe en ella.
Una importación real se ejecuta en una única transacción: un error revierte toda
la operación. Los errores identifican una ruta JSON (`$.tables.questions[0]`),
un archivo y fila CSV, o una hoja y fila XLSX.

### Identidad y reimportación

Cada entidad tiene `exchange_key`, un UUID persistido y único, independiente
del PK local. Las referencias del archivo usan esos UUID. Categorías y etiquetas
con nombre único pueden reconciliarse por nombre exacto al importar en una base
recién creada; se conserva el registro local y se adopta la clave del archivo.
Una clave existente actualiza ese mismo registro. Las filas de relación se
añaden sin duplicarse. Es una importación tipo merge: las entidades y los
vínculos ausentes del archivo quedan intactos; el archivo no elimina datos.
Por ello, reimportar el mismo documento es idempotente.

El contrato común usa `format: "interview-ai-assistant-knowledge-base"` y
`version: 1`. Sus tablas y cabeceras exactas son:

| Tabla | Columnas |
|---|---|
| `categories` | `key`, `name` |
| `questions` | `key`, `category_key`, `question` |
| `answers` | `key`, `question_key`, `text` |
| `question_variants` | `key`, `question_key`, `text` |
| `tags` | `key`, `name` |
| `professional_experiences` | `key`, `position`, `company_or_project`, `start_date`, `end_date`, `responsibilities`, `achievements` |
| `candidate_profiles` | `key`, `name`, `professional_title`, `summary`, `location`, `linkedin_url`, `github_url`, `portfolio_url` |
| `question_tags` | `question_key`, `tag_key` |
| `question_experiences` | `question_key`, `professional_experience_key` |

- El perfil es una tabla opcional al importar documentos v1 anteriores. Si falta
  la hoja XLSX, el archivo CSV o la tabla JSON, se interpreta como vacía y no se
  borra un perfil que ya exista en la base destino. Las exportaciones nuevas
  siempre incluyen la tabla. El contrato solo permite cero o un perfil.
- **JSON:** un objeto con `format`, `version` y `tables`; cada tabla es una
  lista de filas con las columnas anteriores.
- **XLSX:** libro con hoja `manifest` (cabeceras `format`, `version`) y una hoja
  por tabla. Las cabeceras de cada hoja son las indicadas en la tabla. Los
  valores de texto se escriben como texto, no como fórmulas.
- **CSV:** directorio UTF-8 con `manifest.json` (solo `format` y `version`) y un
  archivo `<tabla>.csv` por cada tabla, con las cabeceras indicadas. CSV escapa
  de forma reversible los textos que Excel podría ejecutar como fórmulas:
  antepone `'` si el texto empieza (tras espacios) con `=`, `+`, `-` o `@`, y
  duplica una `'` inicial. La importación del comando revierte ese escape. Los
  archivos CSV son datos de intercambio; no se deben editar mediante
  aplicaciones que transformen automáticamente sus celdas.

Al importar XLSX, las celdas de fórmula se leen como su texto literal y nunca
se evalúan. Al exportar XLSX, todos los campos de texto se escriben como texto.

Los textos se conservan en UTF-8, incluidos acentos, saltos de línea y
contenidos que empiezan por `=`, `+`, `-` o `@`. Las fechas de experiencia usan
`YYYY-MM-DD`; fechas ausentes son `null` en JSON y celdas vacías en CSV/XLSX.
Los campos de perfil, excepto `name`, pueden estar vacíos; los enlaces deben ser
URLs válidas. Las importaciones son merge: un perfil entrante actualiza el
singleton local, y una tabla de perfil ausente no modifica el existente.
Los timestamps locales de creación/actualización no forman parte del contrato.

La dependencia XLSX es `openpyxl` (declarada en `pyproject.toml` y
`requirements.txt`). La gestión de importación/exportación se ofrece por CLI;
no se añade una interfaz de importación en Django Admin.

## Edición desde Django Admin

1. Inicia sesión en `/admin/` con un usuario administrador y abre **Perfil del
   candidato**. Crea el único perfil; después, edita ese registro desde su
   ficha. Solo el nombre es obligatorio.
2. Abre **Experiencias profesionales** y crea una experiencia. La fecha de fin
   puede dejarse vacía para una experiencia actual o sin fecha conocida; si se
   informan ambas fechas, el fin no puede preceder al inicio.
3. En **Preguntas**, abre la pregunta y selecciona una o varias experiencias
   en **Experiencias profesionales**. La relación es muchos-a-muchos y también
   se puede vincular una misma experiencia con varias preguntas.
