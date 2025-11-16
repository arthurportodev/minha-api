import os
from mysql.connector import pooling, Error
from dotenv import load_dotenv
from pathlib import Path

# Carrega o .env da raiz do projeto
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Debug opcional
print("🔧 DEBUG - DB_HOST:", os.getenv("DB_HOST"))

# Configuração da conexão
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "charset": "utf8mb4",
    "autocommit": True
}

try:
    pool = pooling.MySQLConnectionPool(pool_name="main_pool", pool_size=5, **DB_CONFIG)
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
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                print("✅ Conexão bem-sucedida com o banco de dados!")
    except Error as e:
        print("❌ Falha no ping do banco:", e)
