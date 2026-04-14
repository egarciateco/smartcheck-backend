FROM python:3.11-slim

WORKDIR /app

# Copiar archivos de requisitos e instalar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .

# Comando para arrancar el servidor
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]