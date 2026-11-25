# Frontend local

## Requisitos

- Node.js 20.19 o posterior y npm.
- Backend Django disponible en `127.0.0.1:8000` para mostrar el estado de API.
  El panel se puede abrir aunque el backend esté apagado.

## Arrancar en PowerShell

Desde la raíz del proyecto:

```powershell
Set-Location .\frontend
npm.cmd ci
npm.cmd run dev
```

Abre <http://127.0.0.1:5173>. Vite escucha solo en `127.0.0.1` y reenvía las
peticiones `/api/` a Django en `http://127.0.0.1:8000`.

En otra terminal, desde la raíz del proyecto, arranca el backend:

```powershell
.\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000
```

La comprobación de conexión usa el endpoint implementado
`GET /api/health/`. Las secciones de conocimiento, perfil y experiencias
permanecen en estado de integración pendiente hasta que existan sus endpoints.

## Build

```powershell
Set-Location .\frontend
npm.cmd ci
npm.cmd run build
```
