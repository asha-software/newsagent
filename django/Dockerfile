FROM python:3.11-slim

WORKDIR /app

# Configure apt to avoid Hash Sum mismatch
RUN echo "Acquire::http::Pipeline-Depth 0;" > /etc/apt/apt.conf.d/99custom && \
    echo "Acquire::http::No-Cache true;" >> /etc/apt/apt.conf.d/99custom && \
    echo "Acquire::BrokenProxy    true;" >> /etc/apt/apt.conf.d/99custom

# Install system dependencies
RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Django and MySQL client
RUN pip install --no-cache-dir django mysqlclient

# Copy Django project
COPY . .

# Expose port
EXPOSE 8000

# Create a startup script
RUN echo '#!/bin/bash\n\
echo "Waiting for database to be ready..."\n\
while ! python django/manage.py check --database default 2>&1; do\n\
  sleep 2\n\
  echo "Waiting for database connection..."\n\
done\n\
echo "Database is ready!"\n\
\n\
echo "Applying database migrations..."\n\
python django/manage.py migrate\n\
\n\
echo "Starting Django server..."\n\
python django/manage.py runserver 0.0.0.0:8000\n\
' > /app/start.sh

RUN chmod +x /app/start.sh

# Command to run the application
CMD ["/app/start.sh"]
