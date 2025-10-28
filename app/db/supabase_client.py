# app/db/supabase_client.py
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv() # Carga variables de .env desde la raíz del proyecto

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_KEY")

supabase_client: Client = None # Renombrado para claridad
try:
    if url and key:
         supabase_client = create_client(url, key)
         print("Cliente Supabase inicializado correctamente desde supabase_client.py.")
    else:
         print("Error: SUPABASE_URL o SUPABASE_SERVICE_KEY no encontradas en .env.")
except Exception as e:
    print(f"Error al inicializar Supabase en supabase_client.py: {e}")

# Función para obtener el cliente (útil para tests o manejo avanzado)
def get_supabase_client() -> Client:
    if supabase_client is None:
         raise Exception("Cliente Supabase no inicializado. Verifica la configuración.")
    return supabase_client