# En app/services/demand_prediction_service.py

import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import joblib
from datetime import datetime, timedelta
import logging
from supabase import Client
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def get_historical_session_data(supabase: Client) -> pd.DataFrame:
    """
    Obtiene los datos históricos relevantes de la tabla 'sessions' desde Supabase.
    Devuelve un DataFrame de Pandas.
    """
    try:
        # Selecciona solo las columnas necesarias y quizás filtra por un rango de fechas
        # Ajusta el rango según sea necesario (ej. últimos 6 meses)
        six_months_ago = datetime.now() - timedelta(days=180)
        response = await supabase.table('sessions') \
                           .select('session_id, start_time, end_time, duration_minutes') \
                           .gte('start_time', six_months_ago.isoformat()) \
                           .order('start_time', desc=False) \
                           .execute()

        data = getattr(response, 'data', None)

        if data:
            df = pd.DataFrame(response.data)
            logging.info(f"Datos históricos obtenidos de Supabase: {len(df)} sesiones.")
            return df
        else:
            logging.warning("No se encontraron datos históricos de sesiones en Supabase.")
            error_details = getattr(response, 'error', 'No data returned')
            logging.warning(f"Detalles de Supabase: {error_details}")
            return pd.DataFrame() # Devuelve DataFrame vacío si no hay datos

    except Exception as e:
        logging.error(f"Error al obtener datos de Supabase: {e}", exc_info=True)
        return pd.DataFrame()


def clean_and_aggregate_data(df: pd.DataFrame) -> pd.Series:
    """
    Limpia los datos y los agrega en una serie de tiempo horaria
    (contando sesiones iniciadas por hora).
    """
    if df.empty:
        logging.warning("DataFrame vacío, no se puede limpiar ni agregar.")
        return pd.Series(dtype='int')

    # Convertir a datetime y manejar errores/faltantes
    df['start_time'] = pd.to_datetime(df['start_time'], errors='coerce')
    # Eliminar filas donde start_time no pudo ser convertido
    df.dropna(subset=['start_time'], inplace=True)

    if df.empty:
        logging.warning("No quedan datos válidos después de limpiar start_time.")
        return pd.Series(dtype='int')

    # Establecer start_time como índice para re-muestreo
    df.set_index('start_time', inplace=True)

    # Re-muestrear por hora y contar el número de sesiones iniciadas
    hourly_counts = df.resample('H').size() # 'H' es para frecuencia horaria

    # Asegurar un índice completo (rellenar horas sin sesiones con 0)
    if not hourly_counts.empty:
        min_time = hourly_counts.index.min()
        max_time = hourly_counts.index.max()
        full_hourly_index = pd.date_range(start=min_time, end=max_time, freq='H', tz=hourly_counts.index.tz)
        hourly_counts = hourly_counts.reindex(full_hourly_index, fill_value=0)
    else:
        logging.warning("No se generaron conteos horarios.")
        return pd.Series(dtype='int')


    logging.info(f"Datos agregados: {len(hourly_counts)} registros horarios.")
    return hourly_counts


def create_time_features(series: pd.Series) -> pd.DataFrame:
    """
    Crea características basadas en el tiempo (hora, día de la semana, etc.)
    a partir del índice DatetimeIndex de la serie de tiempo.
    """
    if series.empty or not isinstance(series.index, pd.DatetimeIndex):
         logging.warning("Serie de tiempo vacía o índice no es DatetimeIndex, no se pueden crear características.")
         return pd.DataFrame()

    df_features = pd.DataFrame(index=series.index)
    df_features['hour'] = series.index.hour
    df_features['dayofweek'] = series.index.dayofweek # Lunes=0, Domingo=6
    df_features['month'] = series.index.month
    df_features['dayofyear'] = series.index.dayofyear
    df_features['quarter'] = series.index.quarter


    logging.info(f"Características de tiempo creadas para {len(df_features)} registros.")
    return df_features

def train_demand_model(time_series_data: pd.Series) -> bool:
    """
    Entrena un modelo de regresión de scikit-learn usando características de tiempo.
    Guarda el modelo entrenado en MODEL_FILE_PATH.
    Devuelve True si el entrenamiento fue exitoso, False en caso contrario.
    """
    if time_series_data.empty or len(time_series_data) < 10: # Modelo necesita suficientes datos
        logging.error("Datos insuficientes para entrenar el modelo.")
        return False
    
    try:
        # 1. Crear características (X) y el objetivo (y)
        X = create_time_features(time_series_data)
        y = time_series_data

        if X.empty:
            logging.error("No se pudieron crear las características para el entrenamiento.")
            return False
        
        # 2. Instanciar y entrenar el modelo
        model = LinearRegression()
        logging.info("Iniciando el entrenamiento del modelo de regresión lineal.")
        model.fit(X, y)
        logging.info("Modelo entrenado exitosamente.")

        logging.info(f"Guardando el modelo entrenado en {MODEL_FILE_PATH}.")
        joblib.dump(model, MODEL_FILE_PATH)
        logging.info("Modelo guardado exitosamente.")
        return True
    except Exception as e:
        logging.error(f"Error durante el entrenamiento del modelo: {e}", exc_info=True)
        return False

def predict_future_demand(last_known_time: pd.Timestamp, hours_ahead: int = 24) -> pd.DataFrame | None:
    """
    Carga el modelo entrenado y predice la demanda futura creando características de tiempo futuras.
    Devuelve un DataFrame con columnas 'time' y 'predicted_sessions', o None si falla.
    """

    if not isinstance(last_known_time, pd.Timestamp):
        logging.error("last_known_time debe ser un objeto pandas Timestamp.")
        return None
    
    try:
        # 1. Cargar el modelo
        logging.info(f"Cargando modelo desde: {MODEL_FILE_PATH}")
        model = joblib.load(MODEL_FILE_PATH)
        logging.info(f"Modelo cargado exitosamente.")

        # 2. Crear timestamps futuros (asegura que tengan la misma zona horaria si aplica)
        future_index = pd.date_range(
            start=last_known_time + timedelta(hours=1),
            periods=hours_ahead,
            freq='H',
            tz=last_known_time.tz # Heredar zona horaria
        )

        # 3. Crear características para los timestamps futuros
        logging.info("Creando características para timestamps futuros...")
        X_future = create_time_features(pd.Series(index=future_index, dtype=float)) # dtype no importa aquí

        if X_future.empty:
            logging.error("No se pudieron crear características futuras.")
            return None
        
        # 4. Hacer predicciones
        logging.info("Realizando predicciones...")
        predictions_raw = model.predict(X_future)

        # 5. Formatear salida (evitar negativos, redondear a entero)
        predictions_clean = np.round(np.maximum(0, predictions_raw)).astype(int)
        logging.info(f"Predicciones crudas: {predictions_raw[:5]}...") # Muestra algunas predicciones
        logging.info(f"Predicciones limpias: {predictions_clean[:5]}...")

        # Crear DataFrame con resultados
        results = pd.DataFrame({
            'time': future_index,
            'predicted_sessions': predictions_clean
        })

        logging.info(f"Predicciones generadas exitosamente para las próximas {hours_ahead} horas.")
        return results

    except FileNotFoundError:
        logging.error(f"Error crítico: No se encontró el archivo del modelo entrenado en {MODEL_FILE_PATH}. Ejecuta el reentrenamiento.")
        return None
    except Exception as e:
        logging.error(f"Error durante la predicción: {e}", exc_info=True)
        return None