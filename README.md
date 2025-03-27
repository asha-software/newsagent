# Newsagent - Fact Checking Application

The project consists of two main components:
1. A Django web application for user authentication and search interface
2. A FastAPI backend for processing and analyzing claims

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
  - `API_URL`: URL for the FastAPI service (default: `http://api:8000`)

**Important**: For security, make sure to change the default passwords in your `.env` file before deploying to production.

### Database Initialization

The database is initialized automatically in two steps:

1. The MySQL container creates the database and user based on environment variables
2. Django's migration system (`python manage.py migrate`) creates all necessary tables when the Django container starts

This approach ensures that the database schema is properly managed by Django's migration system, which handles table creation, relationships, and any future schema changes.

### Development

For development purposes, the application code is mounted as volumes in the containers, so changes to the code will be reflected without rebuilding the containers.

To rebuild the containers after making changes to the Dockerfiles:
```bash
docker-compose build
docker-compose up -d
```

### Troubleshooting

- If you encounter database connection issues, ensure the MySQL container is running and healthy:
  ```bash
  docker-compose ps
  ```

- To view logs for a specific service:
  ```bash
  docker-compose logs django
  docker-compose logs api
  docker-compose logs db
  ```

- To restart a specific service:
  ```bash
  docker-compose restart django
  ```
