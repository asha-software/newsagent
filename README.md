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
- [Ollama](https://ollama.com/download) installed for local LLM deployment (follow the [Ollama installation instructions](https://ollama.com/download))
- Install `mistral-nemo` using `ollama pull mistral-nemo`

### Getting Started

1. Clone the repository:
   ```bash
   git clone https://github.com/asha-software/newsagent.git
   cd newsagent
   ```

2. Make sure Ollama is running in the background (this is required for the LLM functionality)

3. Start the Docker containers:
   ```bash
   docker compose up
   ```

4. Create a superuser for the Django admin (optional):
   ```bash
   docker compose exec django python manage.py createsuperuser
   ```

5. Access the application:
   - Django web interface: http://localhost:8000
   - FastAPI backend: http://localhost:8001
   - FastAPI documentation: http://localhost:8001/docs

### Services

#### Django Web Application (port 8000)
- Provides user authentication (signup, signin, logout)
- Search interface for fact-checking claims
- Communicates with the FastAPI backend for claim analysis
- Create and manage API Keys
- Create and manage custom tools

#### FastAPI Backend (port 8001)
- Processes claims using various agent components
- Provides a `/query` endpoint for claim analysis
- Returns analysis results to the Django frontend

#### MySQL Database
- Stores user information, api keys, custom tools, and application data
- Accessible within the Docker network

### Environment Variables

The application uses environment variables for configuration. For local development with default settings, you don't need to create any additional files as the docker-compose.yml provides sensible defaults.

**For production or custom configurations**, create a `.env` file in the project root with any of the following variables:

- Database configuration:
  - `MYSQL_ROOT_PASSWORD`: Database root (default: `password`) - **Change this for production!**
  - `MYSQL_DATABASE`: Database name (default: `fakenews_db`)
  - `MYSQL_USER`: Database username (default: `fakenews_user`)
  - `MYSQL_PASSWORD`: Database password (default: `password`) - **Change this for production!**

- Django configuration:
  - `DB_HOST`: Database hostname (default: `db`)
  - `DB_NAME`: Database name (default: `fakenews_db`)
  - `DB_USER`: Database username (default: `fakenews_user`)
  - `DB_PASSWORD`: Database password (default: `password`) - **Change this for production!**

- API configuration:
  - `API_URL`: URL for the FastAPI service (default: `http://api:8000`)

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

The application uses Ollama to run language models locally:

- **Setup (Already done in Prerequisites)**: 
  1. Install [Ollama](https://ollama.com/download)
  2. Pull the mistral-nemo model: `ollama pull mistral-nemo`
  3. Ensure Ollama is running

- **Default Configuration**: 
  The application is pre-configured to use `mistral-nemo` for all components. If you've completed the Prerequisites section, no further configuration is needed.

- **Advanced Configuration (Optional)**:
  If you want to use different models, you can modify the `core/.env` file:
  - `CLAIM_DECOMPOSER_MODEL`: Model for breaking down claims
  - `RESEARCH_AGENT_MODEL`: Model for research (must support tool usage)
  - `REASONING_AGENT_MODEL`: Model for reasoning
  - `VERDICT_AGENT_MODEL`: Model for final verdict

  You can find more models with tool support at: `https://ollama.com/search?c=tools`

### API Keys Configuration

The core backend requires several API keys to function properly. These should be configured in the `core/.env` file:

- `WOLFRAM_APP_ID`: API key for Wolfram Alpha integration
- `TAVILY_API_KEY`: API key for Tavily search engine
- `OPENAI_API_KEY`: API key for OpenAI services (if using OpenAI models)
- `LANGCHAIN_API_KEY`: API key for LangChain integration
- `LANGCHAIN_PROJECT`: LangChain project name
- `LANGCHAIN_TRACING_V2`: Enable LangChain tracing (set to `true` or `false`)

You can obtain these API keys from their respective services:
- Wolfram Alpha: [https://developer.wolframalpha.com/portal/myapps/](https://developer.wolframalpha.com/portal/myapps/)
- Tavily: [https://tavily.com/](https://tavily.com/)
- OpenAI: [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
- LangChain: [https://smith.langchain.com/](https://smith.langchain.com/)

### Development

For development purposes, the application code is mounted as volumes in the containers, so changes to the code will be reflected without rebuilding the containers.

To rebuild the containers after making changes to the Dockerfiles:
```bash
docker compose build
docker compose up
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
  docker compose restart django
  ```

- If email verification is causing issues during local development, you can disable it by setting `EMAIL_VERIFICATION_ENABLED=False` in your `.env` file.

- If you encounter LLM-related issues:
  1. Ensure Ollama is running: Check if the Ollama application is running in the background
  2. Verify the mistral-nemo model is installed: Run `ollama list` to see installed models
  3. If needed, reinstall the model: `ollama pull mistral-nemo`
  4. Check Ollama logs for any errors

### API Usage

The application provides a REST API for programmatic access. You can:

1. Create API keys through the web interface
2. Use these keys to authenticate API requests
3. Submit queries for fact-checking
4. Create and manage custom tools

See the API documentation at `http://localhost:8001/docs` when the application is running.
