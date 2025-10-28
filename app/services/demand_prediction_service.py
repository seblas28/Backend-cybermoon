# En app/services/demand_prediction_service.py

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from supabase import Client

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

        if response.data:
            df = pd.DataFrame(response.data)
            logging.info(f"Datos históricos obtenidos de Supabase: {len(df)} sesiones.")
            return df
        else:
            logging.warning("No se encontraron datos históricos de sesiones en Supabase.")
            return pd.DataFrame() # Devuelve DataFrame vacío si no hay datos

    except Exception as e:
        logging.error(f"Error al obtener datos de Supabase: {e}")
        # En una API real, podrías querer lanzar una HTTPException aquí
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
    if series.empty:
         logging.warning("Serie de tiempo vacía, no se pueden crear características.")
         return pd.DataFrame()

    df_features = pd.DataFrame(index=series.index)
    df_features['hour'] = series.index.hour
    df_features['dayofweek'] = series.index.dayofweek # Lunes=0, Domingo=6
    df_features['month'] = series.index.month
    df_features['dayofyear'] = series.index.dayofyear
    df_features['quarter'] = series.index.quarter


    logging.info(f"Características de tiempo creadas para {len(df_features)} registros.")
    return df_features

# --- Las funciones de entrenamiento y predicción irían aquí después ---
# def train_demand_model(time_series_data: pd.Series): ...
# def predict_future_demand(last_known_time: pd.Timestamp, hours_ahead: int = 24): ...