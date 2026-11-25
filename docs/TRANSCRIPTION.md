# Transcripción local

El proyecto usa Faster-Whisper con CTranslate2. El audio se procesa en el
equipo; no se envía a servicios externos. PyAV incluye las bibliotecas de
decodificación de audio, por lo que no hace falta instalar FFmpeg por separado.

## Instalar y preparar el modelo

Desde la raíz del proyecto, en PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe backend\manage.py migrate
```

La primera ejecución descarga el modelo `small` de Hugging Face a la caché local.
También se puede descargar y preparar antes de tener una grabación:

```powershell
.\.venv\Scripts\python.exe -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8')"
```

La descarga inicial requiere conexión a Internet. Las ejecuciones siguientes
reutilizan los archivos guardados en la caché de Hugging Face del usuario.

## Transcribir un archivo

```powershell
.\.venv\Scripts\python.exe backend\manage.py transcribe_audio "D:\ruta\entrevista.wav"
```

El comando detecta el archivo, transcribe en español y escribe el texto en la
salida estándar. Registra el archivo en `AudioRecording` y guarda el texto en
`Transcription`, relacionado con esa grabación. Si se vuelve a transcribir la
misma ruta, se añade una transcripción y se reutiliza el registro de audio.
Las rutas con espacios deben ir entre comillas.

Se puede escoger otro modelo o indicar una carpeta de modelo descargado:

```powershell
.\.venv\Scripts\python.exe backend\manage.py transcribe_audio "D:\ruta\entrevista.wav" --model tiny
.\.venv\Scripts\python.exe backend\manage.py transcribe_audio "D:\ruta\entrevista.wav" --model "D:\modelos\faster-whisper-small"
```

## Reutilizar el modelo sin conexión

Una vez descargado el modelo, se puede impedir cualquier consulta a Hugging
Face en la sesión actual de PowerShell:

```powershell
$env:HF_HUB_OFFLINE = "1"
.\.venv\Scripts\python.exe backend\manage.py transcribe_audio "D:\ruta\entrevista.wav"
Remove-Item Env:HF_HUB_OFFLINE
```

El modelo debe estar ya en la caché. Si se indicó una ruta local con `--model`,
esa carpeta debe permanecer disponible.

## Aceleración NVIDIA opcional

El dispositivo predeterminado es CPU y usa cuantización `int8`. Para usar CUDA:

```powershell
.\.venv\Scripts\python.exe backend\manage.py transcribe_audio "D:\ruta\entrevista.wav" --device cuda
```

La ejecución CUDA requiere bibliotecas compatibles de CUDA 12/cuBLAS y cuDNN 9
disponibles en `PATH`, además del controlador NVIDIA. El comando usa `float16`
en CUDA. La presencia de la GPU en `nvidia-smi` por sí sola no confirma que esas
bibliotecas estén instaladas.

## Compatibilidad verificada

La resolución binaria de `faster-whisper` 1.2.1 y sus dependencias se comprobó
con el entorno Windows y Python 3.14.7 del proyecto. Pip encontró ruedas
compatibles para CTranslate2, PyAV, Tokenizers y ONNX Runtime. La aceleración
CUDA requiere preparación adicional del sistema y es opcional; la ruta CPU no
depende del CUDA Toolkit.

En el entorno usado para esta implementación, Windows bloqueó la biblioteca
nativa de CTranslate2 con `WinError 4551` (Control de aplicaciones). La
compatibilidad de las ruedas no elimina esa política del sistema: la inferencia
real requiere que Windows permita cargar la biblioteca. El comando muestra un
error explícito y no registra una grabación ni una transcripción si el motor no
se puede cargar.
