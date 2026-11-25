# Arquitectura inicial

El proyecto sigue un monolito modular y separa responsabilidades:

- **`backend/`** contiene Django, Django REST Framework y la configuración de SQLite. `config/` define settings, URLs y entradas ASGI/WSGI; `apps/` contiene la API, `knowledge_base` y `transcriptions`. Esta última conserva las rutas locales de audio y las transcripciones asociadas.
- **`core/`** separa la lógica de voz: `core/speech` ejecuta Faster-Whisper localmente. Los paquetes de captura de audio, vídeo, modelos de lenguaje y recuperación de información (RAG) siguen reservados para fases posteriores.
- **`desktop/`** reserva componentes, servicios y ventanas de la futura aplicación Windows.
- **`data/`** contiene SQLite y directorios locales para importaciones, grabaciones y almacén vectorial. Los datos personales y generados se excluyen del control de versiones.
- **`tests/`** contiene pruebas automatizadas con pytest y pytest-django.
- **`docs/`** documenta decisiones técnicas y fases.

El endpoint `GET /api/health/` devuelve `{"status": "ok"}`. El backend se ejecuta
en `127.0.0.1` por defecto. La transcripción y sus datos permanecen locales;
esta fase no integra servicios externos ni captura de audio.
