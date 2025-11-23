FROM python:3.11-slim

WORKDIR /app

# Evita cache pesado e deixa logs mais claros
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instala dependências do sistema (mysqlclient etc. se precisar)
RUN apt-get update && apt-get install -y \
    build-essential \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# Instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o projeto
COPY . .

# Porta padrão da FastAPI/Uvicorn
EXPOSE 8000

# Sobe a API
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
