# Hoja de ruta

1. **Configuración inicial:** estructura modular, Django 5.2 LTS, API REST mínima,
   SQLite local, variables de entorno, documentación y pruebas.
2. **Captura de audio y vídeo:** grabación local, controles de sesión y almacenamiento de archivos en `data/`.
3. **Transcripción local:** Faster-Whisper se ejecuta en el equipo y el comando
   `transcribe_audio` guarda cada transcripción en español vinculada al archivo
   de audio local. El modelo se reutiliza desde la caché local.
4. **Búsqueda de respuestas:** importar y editar preguntas y respuestas, preparar índices locales y recuperar resultados pertinentes.
5. **Modelo local:** integrar un modelo de lenguaje que se ejecute en el equipo y genere respuestas basadas en el contenido local.
6. **Interfaz de escritorio:** construir la aplicación para Windows e integrar la captura y los servicios locales.

Cada fase posterior requiere validación propia. En esta fase no se instalan
Ollama, Whisper, ChromaDB ni dependencias multimedia. La aplicación no enviará
audio, vídeo, transcripciones ni contenido personal a servicios externos.
