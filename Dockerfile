# Usa una imagen ligera de Python
FROM python:3.12-slim

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia el archivo principal del sistema distribuido al contenedor
COPY distributed_fs.py .

# Comando base (este será sobrescrito por docker-compose)
CMD ["python", "distributed_fs.py"]
