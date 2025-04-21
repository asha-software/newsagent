FROM python:3.11-slim

WORKDIR /app

# Expose port
EXPOSE 8000

# NOTE: docker-compose.yml api is going to set core/.env vars in the environment as well

# Add project root to PYTHONPATH
ENV PYTHONPATH=/app

# Set base url for Ollama running in docker
ENV OLLAMA_BASE_URL=http://host.docker.internal:11434

# Copy setup.py pyproject.toml from the project root
COPY setup.py pyproject.toml /app/

# Copy requirements.txt from the core/ directory
COPY core/requirements.txt /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the core/ directory into the container
COPY core/ /app/core/
# Copy tests into the container
COPY tests/ /app/tests/
# Install test dependencies
RUN pip install coverage pytest-cov pytest

# Install your package in editable mode
RUN pip install -e .

# Command to run the application
CMD ["python", "core/app.py"]