import os
from mysql.connector import pooling, Error
from dotenv import load_dotenv
from pathlib import Path

# Carrega .env só como fallback local (não sobrescreve env do container)
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path, override=False)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "mysql_mysql"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "leads_user"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "projeto_automacao"),
    "charset": "utf8mb4",
    "autocommit": True,
}

try:
    pool = pooling.MySQLConnectionPool(
        pool_name="main_pool",
        pool_size=5,
        pool_reset_session=True,
        **DB_CONFIG
    )
except Error as e:
    print("❌ Erro ao criar pool de conexões:", e)
    raise

def get_conn():
    try:
        return pool.get_connection()
    except Error as e:
        print("❌ Erro ao obter conexão do pool:", e)
        raise

def ping():
    try:
        with get_conn() as conn:
            with conn.cursor(buffered=True) as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        print("✅ Conexão bem-sucedida com o banco de dados!")
        return True
    except Error as e:
        print("❌ Falha no ping do banco:", e)
        return False
