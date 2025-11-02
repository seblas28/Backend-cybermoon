Backend Cybermoon (API de Cibercafé)
Este proyecto es el backend para una aplicación de gestión de cibercafé, construido con FastAPI. Proporciona autenticación de usuarios y un módulo de Machine Learning para la predicción de demanda de sesiones.

Tecnologías Principales
El stack principal de este proyecto incluye:

FastAPI: Framework web para construir la API.

Uvicorn: Servidor ASGI para ejecutar FastAPI.

Supabase: Utilizado como base de datos (PostgreSQL) y para la autenticación de usuarios.

Pydantic: Para la validación de datos y emails.

Scikit-learn: Para construir el modelo de predicción de demanda (Regresión Lineal).

Pandas y Numpy: Para la manipulación y procesamiento de datos para el modelo de ML.

Joblib: Para guardar y cargar el modelo de ML entrenado.

Configuración y Puesta en Marcha
Sigue estos pasos para levantar el entorno de desarrollo local:

1. Clonar el repositorio (Si aún no lo has hecho).

2. Crear y activar un entorno virtual:
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   
3. Instalar dependencias: Asegúrate de tener todas las librerías listadas en requirements.txt.
   pip install -r requirements.txt

4. Configurar variables de entorno: Crea un archivo .env en la raíz del proyecto. Este archivo es ignorado por git (excepto .env.example). Debe contener tus credenciales de Supabase, que son cargadas por supabase_client.py.
.env

SUPABASE_URL="https://tu_url_de_supabase.supabase.co"
SUPABASE_SERVICE_KEY="tu_llave_de_servicio_de_supabase"

Ejecutar la Aplicación
Una vez configurado el entorno, puedes iniciar el servidor Uvicorn desde el directorio raíz:

uvicorn app.main:app --reload

La API estará disponible localmente en http://127.0.0.1:8000. Puedes acceder a la documentación interactiva (generada por FastAPI) en http://127.0.0.1:8000/docs.

Estructura del Proyecto

Backend-cybermoon/
├── app/
│   ├── db/
│   │   └── supabase_client.py  # Inicializa y provee el cliente de Supabase
│   ├── routers/
│   │   ├── auth.py             # Endpoints para /signup y /login
│   │   └── ml_reports.py       # Endpoints para /reports (predicción y reentrenamiento)
│   ├── services/
│   │   └── demand_prediction_service.py # Lógica de negocio para el ML (obtener datos, entrenar, predecir)
│   └── main.py                 # Punto de entrada de FastAPI, incluye los routers
├── .gitignore                  # Archivos ignorados (logs, venv, modelos .joblib, .h5)
└── requirements.txt            # Dependencias del proyecto

Endpoints de la API
La aplicación principal (main.py) incluye los siguientes routers:

Raíz
  - GET /: Mensaje de bienvenida a la API.

  - GET /test-supabase: Endpoint de prueba para verificar que el cliente de Supabase esté configurado.

Autenticación (/auth)
Rutas gestionadas en app/routers/auth.py:

- POST /auth/signup

  - Descripción: Registra un nuevo usuario en Supabase Auth.

  - Body: {"email": "user@example.com", "password": "your_password"}

  - Respuesta (201): {"user_id": "...", "email": "..."}

- POST /auth/login

  - Descripción: Inicia sesión de un usuario existente.

  - Body: {"email": "user@example.com", "password": "your_password"}

  - Respuesta (200): {"access_token": "...", "refresh_token": "...", "user_id": "...", "email": "..."}
 
Reportes y Machine Learning (/reports)
Rutas gestionadas en app/routers/ml_reports.py:

- POST /reports/demand-model/retrain

  - Descripción: Inicia el proceso de reentrenamiento del modelo de predicción de demanda. Este endpoint:

    1. Obtiene datos históricos de sesiones desde Supabase (tabla sessions).

    2. Limpia y agrega los datos por hora.

    3. Crea características basadas en el tiempo (hora, día de la semana, mes).

    4. Entrena un modelo de Regresión Lineal y lo guarda en un archivo (usando joblib).

  - Respuesta (200): {"status": "success", "message": "Modelo de demanda re-entrenado exitosamente."}

- GET /reports/demand-prediction

  - Descripción: Obtiene la predicción de demanda de sesiones para las próximas N horas. Carga el modelo .joblib previamente entrenado.

  - Parámetro Query: hours_ahead (int, default: 24).

  - Respuesta (200):
{
  "status": "success",
  "predictions": [
    { "time": "2025-11-02T22:00:00Z", "predicted_sessions": 5 },
    { "time": "2025-11-02T23:00:00Z", "predicted_sessions": 3 },
    // ...
  ]
}
