FROM python:3.11-slim

WORKDIR /app

# Expose port
EXPOSE 8000

# Add project root to PYTHONPATH
ENV PYTHONPATH=/app
ENV OLLAMA_BASE_URL=http://host.docker.internal:11434

# Copy setup.py pyproject.toml from the project root
COPY setup.py pyproject.toml /app/

# Copy requirements.txt from the core/ directory
COPY core/requirements.txt /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the core/ directory into the container
COPY core/ /app/core/

# Install your package in editable mode
RUN pip install -e .

# Command to run the application
CMD ["python", "core/app.py"]
