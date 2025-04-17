# Newsagent - Fact Checking Application

## Overview

Newsagent is a fact-checking application that uses AI and various tools to verify claims. The system leverages multiple sources including web search, Wikipedia, calculator, and Wolfram Alpha to provide accurate verdicts on user queries.

The project consists of three main components:
1. A Django web application for user authentication and search interface
2. A backend for processing and analyzing claims accessible via API
3. A MySQL database for storage

## Docker Compose Setup

The project is containerized using Docker Compose with three services:
- Django web application
- FastAPI backend
- MySQL database

### Prerequisites

- Docker and Docker Compose installed on your system
- Git (to clone the repository)

### Getting Started

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd newsagent
   ```

2. Start the Docker containers:
   ```bash
   docker-compose up -d
   ```

3. Create a superuser for the Django admin (optional):
   ```bash
   docker-compose exec django python manage.py createsuperuser
   ```

4. Access the application:
   - Django web interface: http://localhost:8000
   - FastAPI backend: http://localhost:8001
   - FastAPI documentation: http://localhost:8001/docs

### Services

#### Django Web Application (port 8000)
- Provides user authentication (signup, signin, logout)
- Search interface for fact-checking claims
- Communicates with the FastAPI backend for claim analysis

#### FastAPI Backend (port 8001)
- Processes claims using various agent components
- Provides a `/query` endpoint for claim analysis
- Returns analysis results to the Django frontend

#### MySQL Database
- Stores user information and application data
- Accessible within the Docker network

### Environment Variables

The application uses environment variables for configuration. You can set these by:

1. Edit the `.env` file in the project root

The following environment variables are available:

- Database configuration:
  - `MYSQL_ROOT_PASSWORD`: Database root (default: `password`) - **Change this!**
  - `MYSQL_DATABASE`: Database name (default: `fakenews_db`)
  - `MYSQL_USER`: Database username (default: `fakenews_user`)
  - `MYSQL_PASSWORD`: Database password (default: `password`) - **Change this!**

- Django configuration:
  - `DB_HOST`: Database hostname (default: `db`)
  - `DB_NAME`: Database name (default: `fakenews_db`)
  - `DB_USER`: Database username (default: `fakenews_user`)
  - `DB_PASSWORD`: Database password (default: `password`) - **Change this!**

- API configuration:
  - `API_URL`: URL for the FastAPI service (default: `http://localhost:8001`)

- Email configuration:
  - `EMAIL_HOST`: SMTP server hostname
  - `EMAIL_PORT`: SMTP server port (default: `465`)
  - `EMAIL_USE_TLS`: Whether to use TLS (default: `True`)
  - `EMAIL_HOST_USER`: Email username/address
  - `EMAIL_HOST_PASSWORD`: Email password
  - `EMAIL_VERIFICATION_ENABLED`: Toggle email verification (default: `True`). Set to `False` for local development to bypass email verification.

**Important**: For security, make sure to change the default passwords in your `.env` file before deploying to production.

### Database Initialization

The database is initialized automatically in two steps:

1. The MySQL container creates the database and user based on environment variables
2. Django's migration system (`python manage.py migrate`) creates all necessary tables when the Django container starts

This approach ensures that the database schema is properly managed by Django's migration system, which handles table creation, relationships, and any future schema changes.

### LLM Configuration

The application can use various language models:

- **Ollama Integration**: The system supports running LLMs locally via Ollama. By default, it connects to Ollama at `http://localhost:11434`. You can override this by setting the `OLLAMA_BASE_URL` environment variable.

- **Supported Models**:
  - OpenAI: `gpt-4o-mini`
  - Anthropic: `claude-3-opus-20240229`, `claude-3-sonnet-20240229`, `claude-3-haiku-20240307`, `claude-2.0`, `claude-2.1`
  - Ollama (local): `llama3`, `llama3:8b`, `llama3:70b`, `mistral-nemo`, `mistral:7b`, `mixtral`, `phi3`, `qwq`

- **Agent Model Configuration**: The application uses different models for different components of the fact-checking pipeline. These can be configured in the `core/.env` file:
  - `CLAIM_DECOMPOSER_MODEL`: Model used for breaking down claims (default: `mistral-nemo`)
  - `RESEARCH_AGENT_MODEL`: Model used for research (default: `mistral-nemo`)
  - `REASONING_AGENT_MODEL`: Model used for reasoning (default: `mistral-nemo`)
  - `VERDICT_AGENT_MODEL`: Model used for final verdict (default: `mistral-nemo`)

### API Keys Configuration

The core backend requires several API keys to function properly. These should be configured in the `core/.env` file:

- `WOLFRAM_APP_ID`: API key for Wolfram Alpha integration
- `TAVILY_API_KEY`: API key for Tavily search engine
- `OPENAI_API_KEY`: API key for OpenAI services (if using OpenAI models)
- `LANGCHAIN_API_KEY`: API key for LangChain integration
- `LANGCHAIN_PROJECT`: LangChain project name
- `LANGCHAIN_TRACING_V2`: Enable LangChain tracing (set to `true` or `false`)

### Development

For development purposes, the application code is mounted as volumes in the containers, so changes to the code will be reflected without rebuilding the containers.

To rebuild the containers after making changes to the Dockerfiles:
```bash
docker compose build
docker compose up -d
```

### Custom Tools

The application supports creating custom tools to extend its capabilities. These tools allow you to connect to external APIs without writing backend code. See `core/README_CUSTOM_TOOLS.md` for detailed instructions on creating and using custom tools.

### User Authentication

The application includes a complete user authentication system with:

- User registration with email verification
- Password reset functionality
- API key management for programmatic access
- User-specific tool preferences and history

### Troubleshooting

- If you encounter database connection issues, ensure the MySQL container is running and healthy:
  ```bash
  docker compose ps
  ```

- To view logs for a specific service:
  ```bash
  docker compose logs django
  docker compose logs api
  docker compose logs db
  ```

- To restart a specific service:
  ```bash
  docker-compose restart django
  ```

- If email verification is causing issues during local development, you can disable it by setting `EMAIL_VERIFICATION_ENABLED=False` in your `.env` file.

### API Usage

The application provides a REST API for programmatic access. You can:

1. Create API keys through the web interface
2. Use these keys to authenticate API requests
3. Submit queries for fact-checking
4. Create and manage custom tools

See the API documentation at `http://localhost:8001/docs` when the application is running.
