from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel, EmailStr
from ..db.supabase_client import get_supabase_client
from supabase import Client # Importa el cliente


router = APIRouter(
    prefix="/auth", # Prefijo para todas las rutas en este archivo
    tags=["Authentication"], # Etiqueta para la documentación de la API
)

# --- Modelos Pydantic para Validación ---
class UserCredentials(BaseModel):
    email: EmailStr
    password: str

class SignUpResponse(BaseModel):
    user_id: str
    email: EmailStr

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    user_id: str
    email: EmailStr


# --- Endpoints ---

@router.post("/signup", response_model=SignUpResponse, status_code=201)
async def signup_user(credentials: UserCredentials = Body(...), supabase: Client = Depends(get_supabase_client)):
    """
    Registra un nuevo usuario en Supabase Auth.
    """

    try:
        res = supabase.auth.sign_up({
            "email": credentials.email,
            "password": credentials.password,
        })

        # Verifica si hay datos y si el usuario se creó (puede requerir confirmación por email)
        if res.user and res.user.id:
             # Importante: Supabase puede devolver un usuario aunque requiera confirmación.
             # La tabla 'profiles' necesitará crearse, quizás con un trigger o aquí mismo.
            print(f"Usuario creado (puede requerir confirmación): {res.user.id}")
            return SignUpResponse(user_id=str(res.user.id), email=res.user.email)
        elif res.error:
             raise HTTPException(status_code=400, detail=res.error.message)
        else:
             # Caso raro, sign_up no devolvió ni usuario ni error claro
             raise HTTPException(status_code=500, detail="Respuesta inesperada de Supabase durante el registro.")

    except HTTPException as http_exc:
        raise http_exc # Re-lanzar excepciones HTTP ya manejadas
    except Exception as e:
        # Captura otros posibles errores de Supabase o de red
        print(f"Error en signup: {e}") # Log del error real
        raise HTTPException(status_code=500, detail=f"Error interno del servidor durante el registro: {e}")


@router.post("/login", response_model=LoginResponse)
async def login_user(credentials: UserCredentials = Body(...), supabase: Client = Depends(get_supabase_client)):
    """
    Inicia sesión de un usuario con email y contraseña.
    """
    try:
        res = supabase.auth.sign_in_with_password({
            "email": credentials.email,
            "password": credentials.password,
        })

        # Verifica si la sesión se inició correctamente
        if res.session and res.session.access_token and res.user:
            print(f"Usuario logueado: {res.user.id}")
            return LoginResponse(
                access_token=res.session.access_token,
                refresh_token=res.session.refresh_token,
                user_id=str(res.user.id),
                email=res.user.email
            )
        elif res.error:
             raise HTTPException(status_code=401, detail=res.error.message) # 401 para credenciales inválidas
        else:
            raise HTTPException(status_code=500, detail="Respuesta inesperada de Supabase durante el login.")

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Error en login: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor durante el login: {e}")
