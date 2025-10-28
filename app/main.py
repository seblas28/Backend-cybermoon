import os
from fastapi import FastAPI
from .routers import auth, ml_reports
from .db.supabase_client import get_supabase_client

# Crear la instancia de la aplicación FastAPI
app = FastAPI(title="Cybercafe Backend API")

# Endpoint raíz de ejemplo
@app.get("/")
async def read_root():
    return {"message": "Bienvenido a la API del Cibercafé"}

app.include_router(auth.router)
app.include_router(ml_reports.router)

# (Aquí añadirás más routers y endpoints después)

# (Opcional) Puedes añadir un endpoint para probar la conexión a Supabase
@app.get("/test-supabase")
async def test_supabase_connection():
    try:
        client = get_supabase_client() # Obtiene el cliente
        # Intenta una operación simple si quieres verificar más a fondo
        # response = client.table('computers').select('computer_id', count='exact').limit(1).execute()
        return {"status": "ok", "message": "Cliente Supabase parece estar configurado."}
    except Exception as e:
        return {"status": "error", "message": f"Error al interactuar con Supabase: {e}"}