# Dockerfile

FROM python:3.11-slim

WORKDIR /app

# Instala dependências do sistema (para SQLite, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copia requirements e instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código
COPY . .

# Cria diretório para logs e instância (SQLite)
RUN mkdir -p logs instance

# Expõe a porta padrão do Flask
EXPOSE 5000

# Define variáveis de ambiente
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Comando de inicialização
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
