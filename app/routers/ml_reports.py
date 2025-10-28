# app/routers/ml_reports.py

from fastapi import APIRouter, Depends, HTTPException, Query
from supabase import Client
from ..db.supabase_client import get_supabase_client
from ..services import demand_prediction_service as demand_service # Importa tu servicio de predicción
import pandas as pd
import logging
from typing import List, Dict, Any

router = APIRouter(
    prefix="/reports", # Prefijo para todas las rutas de este módulo
    tags=["Reports & ML"], # Etiqueta para la documentación /docs
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Endpoints ---

@router.post("/demand-model/retrain", status_code=200)
async def trigger_demand_model_training(
    supabase: Client = Depends(get_supabase_client)
    # Aquí podrías añadir seguridad extra, ej. verificar si el usuario es admin
    # current_user: User = Depends(get_current_admin_user) # Necesitarías implementar esta dependencia
):
    """
    Endpoint para (re)entrenar el modelo de predicción de demanda.
    Obtiene datos históricos de Supabase, los preprocesa y entrena el modelo sklearn.
    """
    logging.info("Iniciando reentrenamiento del modelo de demanda...")
    try:
        # 1. Obtener datos históricos
        historical_data_df = await demand_service.get_historical_session_data(supabase)
        if historical_data_df.empty:
            logging.warning("No se encontraron datos históricos suficientes para el reentrenamiento.")
            raise HTTPException(status_code=404, detail="No hay suficientes datos históricos para entrenar el modelo.")

        # 2. Limpiar y Agregar Datos
        time_series = demand_service.clean_and_aggregate_data(historical_data_df)
        if time_series.empty or len(time_series) < 10: # Asegurar suficientes datos para sklearn
             logging.warning("Datos insuficientes después del preprocesamiento.")
             raise HTTPException(status_code=400, detail="Datos insuficientes después del preprocesamiento para entrenar.")

        # 3. Entrenar el Modelo (Usando la función del servicio)
        success = demand_service.train_demand_model(time_series)

        if success:
            logging.info("Modelo de demanda re-entrenado exitosamente.")
            return {"status": "success", "message": "Modelo de demanda re-entrenado exitosamente."}
        else:
             logging.error("Fallo durante la fase de entrenamiento del modelo.")
             raise HTTPException(status_code=500, detail="Fallo durante el entrenamiento del modelo. Revisa los logs del servidor.")

    except HTTPException as http_exc:
        # Re-lanzar excepciones HTTP ya manejadas (ej. 404 de get_historical_session_data)
        raise http_exc
    except Exception as e:
        # Capturar cualquier otro error inesperado
        logging.exception(f"Error inesperado en trigger_demand_model_training: {e}") # Log completo con traceback
        raise HTTPException(status_code=500, detail=f"Error interno del servidor durante el reentrenamiento: {e}")


@router.get("/demand-prediction", response_model=Dict[str, Any]) # O usa DemandPredictionResponse si lo defines
async def get_demand_prediction(
    hours_ahead: int = Query(24, ge=1, le=168, description="Número de horas futuras a predecir (1-168)."), # Parámetro con validación
    supabase: Client = Depends(get_supabase_client)
    # Aquí también podrías añadir seguridad (ej. solo admins pueden ver predicciones)
):
    """
    Obtiene la predicción de demanda de sesiones para las próximas N horas.
    Carga el modelo previamente entrenado.
    """
    logging.info(f"Solicitando predicción de demanda para {hours_ahead} horas.")
    try:
        # 1. Obtener el último timestamp conocido de los datos (necesario para generar features futuros)
        #    Esta es una forma simple, podrías guardar el último timestamp al entrenar
        response = await supabase.table('sessions') \
                           .select('start_time') \
                           .order('start_time', desc=True) \
                           .limit(1) \
                           .execute()

        if not response.data:
            logging.warning("No se encontraron datos de sesiones para determinar el último timestamp.")
            raise HTTPException(status_code=404, detail="No hay datos históricos para basar la predicción.")

        # Asegurarse que es un objeto datetime consciente de la zona horaria y tomar la hora base
        last_known_time = pd.to_datetime(response.data[0]['start_time']).floor('H')

        # 2. Llamar a la función de predicción del servicio
        predictions_df = demand_service.predict_future_demand(last_known_time, hours_ahead=hours_ahead)

        if predictions_df is None:
            logging.error("La función predict_future_demand devolvió None.")
            raise HTTPException(status_code=500, detail="No se pudo generar la predicción. Puede que el modelo no esté entrenado.")

        # 3. Formatear la respuesta para JSON
        # Convertir DataFrame a lista de diccionarios
        result = predictions_df.to_dict('records')
        # Convertir timestamps a string ISO 8601 (formato estándar)
        for item in result:
            if isinstance(item.get('time'), pd.Timestamp):
                 item['time'] = item['time'].isoformat()

        logging.info(f"Predicción generada exitosamente para {len(result)} puntos.")
        return {"status": "success", "predictions": result}

    except HTTPException as http_exc:
        raise http_exc
    except FileNotFoundError: # Captura específica si el modelo no existe
         logging.error(f"Archivo del modelo no encontrado: {demand_service.MODEL_FILE_PATH}")
         raise HTTPException(status_code=503, detail="El modelo de predicción aún no ha sido entrenado. Ejecute el reentrenamiento primero.")
    except Exception as e:
        logging.exception(f"Error inesperado en get_demand_prediction: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor al generar la predicción: {e}")
