FROM python:3.12-slim

WORKDIR /app

# Instalar dependências de sistema (ex: psycopg2 precisa de bibliotecas C)
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Instalar dependências do python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o restante do código
COPY . .

# Comando padrão
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
