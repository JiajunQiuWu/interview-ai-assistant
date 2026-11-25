
# Interview AI Assistant - Project Instructions

## Project objective

Build a privacy-first, local AI interview assistant for Windows 11.

The application must support:
- Real-time audio capture.
- Local speech-to-text transcription.
- Interview question detection.
- Retrieval of personal knowledge.
- AI-generated response suggestions.
- Authorized audio and video recording.
- Interview history and practice sessions.

## Hardware

- CPU: AMD Ryzen 5 9600X.
- GPU: NVIDIA RTX 5060.
- RAM: 32 GB.
- OS: Windows 11.

## Technology stack

- Python 3.12.
- Django 5.2 LTS.
- Django REST Framework.
- SQLite.
- ChromaDB.
- Ollama.
- Faster-Whisper.
- PySide6.
- FFmpeg.
- Pytest.

## Architecture

Use a modular monolith.

Separate responsibilities into:
- backend: persistence, administration and API.
- core: audio, video, speech, LLM and RAG.
- desktop: graphical user interface.
- data: private local application data.
- tests: automated tests.
- docs: technical documentation.

## Development rules

- Follow SOLID principles where appropriate.
- Use type hints.
- Follow PEP 8.
- Prefer simple and maintainable solutions.
- Avoid unnecessary abstractions.
- Write automated tests for new functionality.
- Handle exceptions explicitly.
- Use pathlib for filesystem operations.
- Keep business logic separate from UI.
- Never install unnecessary dependencies.
- Document architectural decisions.
- Do not implement future phases prematurely.

## Privacy and security

- All AI inference must run locally.
- Never send interview recordings to external services.
- Never send personal knowledge to external AI APIs.
- Never commit credentials or private data.
- Bind local services to localhost by default.
- Recording requires explicit user activation.
- Display a visible recording indicator.
- Support deleting recordings and interview data.
- Use the assistant for practice and permitted interviews.
- Never fabricate professional experience.

## Agent workflow

Before modifying code:
1. Inspect the existing project.
2. Explain the implementation plan.
3. Identify affected files.
4. Implement only the requested scope.
5. Run relevant automated tests.
6. Report changes and unresolved issues.

Ask for approval before major architectural changes.

## Language

- Source code and identifiers: English.
- User-facing explanations: Spanish.
- Documentation: Spanish.
