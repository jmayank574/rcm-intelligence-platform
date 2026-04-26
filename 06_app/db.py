import logging
import os
import threading

import pandas as pd
import streamlit as st
from databricks import sql
from dotenv import load_dotenv

load_dotenv()

_thread_local = threading.local()


def _get_connection():
    """One Databricks connection per thread — safe for concurrent ThreadPoolExecutor use."""
    if not hasattr(_thread_local, 'conn'):
        host         = os.getenv("DATABRICKS_HOST")
        token        = os.getenv("DATABRICKS_TOKEN")
        warehouse_id = os.getenv("DATABRICKS_WAREHOUSE_ID", "87fec7c67121429d")
        http_path    = os.getenv("DATABRICKS_HTTP_PATH",
                                 f"/sql/1.0/warehouses/{warehouse_id}")
        if not host or not token:
            raise ValueError("Missing DATABRICKS_HOST or DATABRICKS_TOKEN")
        _thread_local.conn = sql.connect(
            server_hostname=host,
            http_path=http_path,
            access_token=token,
        )
    return _thread_local.conn


@st.cache_data(ttl=3600)
def run_query(query: str) -> pd.DataFrame:
    try:
        conn = _get_connection()
        with conn.cursor() as cursor:
            cursor.execute(query)
            result  = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return pd.DataFrame(result, columns=columns)
    except Exception as e:
        logging.error("Databricks query failed: %s | query: %.200s", e, query)
        return pd.DataFrame()
