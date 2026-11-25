# Interview AI Assistant

Asistente personal de entrevistas para Windows 11, diseñado con privacidad
local como principio. El proyecto incluye una API Django mínima, transcripción
de audio local y un panel web React de primera versión. Todavía no incluye
captura, búsqueda de respuestas ni modelos de lenguaje.

## Requisitos

- Windows 11
- Python 3.12 o posterior

## Preparar el entorno (PowerShell)

Ejecuta estos comandos desde la raíz del proyecto:

```powershell
py -3.12 -m venv .venv
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe backend\manage.py migrate
.\.venv\Scripts\python.exe backend\manage.py check
.\.venv\Scripts\python.exe -m pytest
```

Si `.venv` ya existe, no es necesario recrearlo. Configura los valores locales en
`.env`; ese archivo no se versiona. `.env.example` solo contiene valores
ilustrativos.

## Arrancar el backend

```powershell
.\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000
```

El servidor queda disponible únicamente en localhost:

- Estado: <http://127.0.0.1:8000/api/health/>
- Administración de Django: <http://127.0.0.1:8000/admin/>

## Arrancar el panel web

En otra terminal de PowerShell, desde la raíz del proyecto:

```powershell
Set-Location .\frontend
npm.cmd ci
npm.cmd run dev
```

Abre <http://127.0.0.1:5173>. Vite escucha solo en `127.0.0.1:5173` y reenvía
`/api/` al backend local. Consulta [las instrucciones del frontend](frontend/README.md).

La base SQLite se encuentra en `data\db.sqlite3`. Django crea las carpetas
locales de datos necesarias al cargar la configuración.

Para crear un usuario administrador y acceder a Django Admin:

```powershell
.\.venv\Scripts\python.exe backend\manage.py createsuperuser
.\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000
```

## Comprobaciones de desarrollo

```powershell
.\.venv\Scripts\python.exe backend\manage.py check
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\ruff.exe check backend core tests
```

Consulta [la arquitectura](docs/ARCHITECTURE.md), [la base de datos](docs/DATABASE.md)
y [la hoja de ruta](docs/ROADMAP.md).

## Transcripción local

Instala las dependencias y aplica las migraciones:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe backend\manage.py migrate
```

Consulta [la guía de transcripción](docs/TRANSCRIPTION.md) para preparar el
modelo local, transcribir archivos y repetir el proceso sin conexión.
