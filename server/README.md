# Blacklight Server

A production-ready Flask server boilerplate with PostgreSQL, Redis, Alembic migrations, and Docker support.

## Features

- 🚀 **Production-Ready**: Configured with Gunicorn, Nginx, and proper error handling
- 🐘 **PostgreSQL**: Full relational database support with SQLAlchemy ORM
- 🔄 **Alembic Migrations**: Database version control and schema management
- 🔴 **Redis**: Caching, sessions, and rate limiting support
- 🐳 **Docker**: Complete Docker and Docker Compose setup for local development and production
- ✅ **Testing**: Comprehensive pytest setup with fixtures and coverage reporting
- 📝 **Pydantic**: Request/response validation and settings management
- 🔐 **Security**: CORS, secure headers, password hashing, and input validation
- 📊 **Logging**: Structured JSON logging for production environments
- 📚 **RESTful API**: Complete user management API with audit logging

## Tech Stack

### Core Framework
- **Flask** - Micro web framework
- **Flask-SQLAlchemy** - ORM integration
- **Flask-CORS** - CORS handling
- **Pydantic** - Data validation

### Database
- **PostgreSQL** - Production database
- **SQLAlchemy** - ORM
- **Alembic** - Database migrations

### Caching & Sessions
- **Redis** - Cache and session storage
- **redis-py** - Python Redis client

### Production
- **Gunicorn** - WSGI HTTP server
- **Nginx** - Reverse proxy
- **Docker** - Containerization

### Testing
- **pytest** - Testing framework
- **pytest-flask** - Flask testing utilities
- **pytest-cov** - Coverage reporting

## Quick Start

### Prerequisites

- Python 3.8+
- Docker and Docker Compose
- PostgreSQL (if running without Docker)
- Redis (if running without Docker)

### Local Development with Docker

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd server
   ```

2. **Start services**
   ```bash
   docker-compose up -d
   ```

   This will start:
   - Flask app on `http://localhost:5000`
   - PostgreSQL on `localhost:5432`
   - Redis on `localhost:6379`
   - pgAdmin on `http://localhost:5050`
   - Redis Commander on `http://localhost:8081`

3. **Check application health**
   ```bash
   curl http://localhost:5000/api/health
   ```

### Local Development (Native)

1. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements-dev.txt
   ```

3. **Setup environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Initialize database**
   ```bash
   python manage.py init
   python manage.py seed
   ```

5. **Run development server**
   ```bash
   flask run
   ```

   Server will be available at `http://localhost:5000`

## Project Structure

```
server/
├── app/                          # Application package
│   ├── __init__.py              # App factory
│   ├── models/                  # SQLAlchemy models
│   ├── routes/                  # API blueprints
│   ├── schemas/                 # Pydantic validation schemas
│   ├── services/                # Business logic
│   ├── middleware/              # Custom middleware
│   └── utils/                   # Utility functions and Redis client
├── config/                       # Configuration
│   ├── base.py                  # Base configuration
│   ├── development.py           # Development config
│   ├── production.py            # Production config
│   ├── testing.py               # Testing config
│   └── settings.py              # Pydantic settings
├── migrations/                   # Alembic migrations
├── tests/                        # Test suite
│   ├── conftest.py              # Pytest fixtures
│   ├── test_health.py           # Health check tests
│   └── integration/             # Integration tests
├── docker/                       # Docker configuration
│   ├── Dockerfile               # Multi-stage build
│   └── nginx/                   # Nginx configuration
├── wsgi.py                       # Production entry point
├── manage.py                     # Management CLI
├── requirements.txt              # Production dependencies
├── requirements-dev.txt          # Development dependencies
├── docker-compose.yml            # Local development stack
├── docker-compose.prod.yml       # Production stack
├── alembic.ini                   # Alembic configuration
└── README.md                     # This file
```

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Flask
FLASK_APP=wsgi.py
FLASK_ENV=development
SECRET_KEY=your-secret-key

# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/blacklight

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_CACHE_URL=redis://localhost:6379/1

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# CORS
CORS_ORIGINS=*
```

### Configuration Classes

- **Development**: `config.development.DevelopmentConfig`
- **Production**: `config.production.ProductionConfig`
- **Testing**: `config.testing.TestingConfig`

Configuration is loaded automatically based on the `ENVIRONMENT` variable.

## API Endpoints

### Health & Info
- `GET /api/health` - Health check
- `GET /api/info` - Application information
- `GET /api/` - API root

### User Management
- `GET /api/users` - List users (paginated)
- `GET /api/users/<id>` - Get user by ID
- `POST /api/users` - Create user
- `PUT /api/users/<id>` - Update user
- `DELETE /api/users/<id>` - Delete user

### Request/Response Format

All endpoints accept and return JSON.

**Success Response (2xx)**
```json
{
  "id": 1,
  "username": "user",
  "email": "user@example.com",
  "is_active": true,
  "created_at": "2023-10-20T10:30:00",
  "updated_at": "2023-10-20T10:30:00"
}
```

**Error Response (4xx/5xx)**
```json
{
  "error": "Error",
  "message": "Error description",
  "status": 400,
  "details": {}
}
```

## Database Management

### Initialize Database
```bash
python manage.py init
```

### Create Sample Data
```bash
python manage.py seed
```

### Run Migrations
```bash
python manage.py migrate
```

### Create New Migration
```bash
python manage.py create-migration "Add new column"
```

### Drop All Tables
```bash
python manage.py drop
```

## Testing

### Run All Tests
```bash
pytest
```

### Run Specific Test File
```bash
pytest tests/test_health.py
```

### Run Tests with Coverage
```bash
pytest --cov=app --cov-report=html
```

### Run Only Unit Tests
```bash
pytest -m unit
```

### Run Only Integration Tests
```bash
pytest -m integration
```

### Test Markers
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.slow` - Slow tests (run without `-m "not slow"`)

## Docker

### Build Images
```bash
docker-compose build
```

### Start Services
```bash
docker-compose up -d
```

### Stop Services
```bash
docker-compose down
```

### View Logs
```bash
docker-compose logs app
docker-compose logs postgres
docker-compose logs redis
```

### Production Deployment

1. **Configure environment variables**
   ```bash
   cp .env.example .env.prod
   # Edit .env.prod with production values
   ```

2. **Start production stack**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

3. **Run migrations**
   ```bash
   docker-compose -f docker-compose.prod.yml exec app python manage.py migrate
   ```

## Development Workflow

### Code Quality

**Format code with Black**
```bash
black app/ tests/
```

**Check code style with Flake8**
```bash
flake8 app/ tests/
```

**Import sorting with isort**
```bash
isort app/ tests/
```

**Type checking with mypy**
```bash
mypy app/
```

### Making Changes

1. Create feature branch
2. Make changes with tests
3. Run quality checks
4. Submit pull request

## Production Considerations

### Security
- ✅ CORS configured per environment
- ✅ Secure headers set (X-Frame-Options, X-Content-Type-Options, etc.)
- ✅ Password hashing with SHA-256
- ✅ Input validation with Pydantic
- ✅ Rate limiting ready (Nginx)
- ✅ HTTPS ready (Nginx SSL configuration)

### Performance
- ✅ Database connection pooling
- ✅ Redis caching support
- ✅ Gunicorn with multiple workers
- ✅ Gzip compression (Nginx)
- ✅ Request logging and monitoring

### Monitoring
- ✅ Health check endpoint
- ✅ Structured JSON logging
- ✅ Container health checks
- ✅ Audit logging for user actions

## Troubleshooting

### Database Connection Issues
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check database URL format
# postgresql://user:password@host:port/database
```

### Redis Connection Issues
```bash
# Check Redis is running
docker-compose ps redis

# Test connection
redis-cli ping
```

### Port Already in Use
```bash
# Find and kill process using port
lsof -i :5000
kill -9 <PID>
```

### Database Migration Issues
```bash
# Upgrade to latest
python manage.py migrate

# Check current version
alembic current
```

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Make changes with tests
4. Run quality checks: `pytest`, `black`, `flake8`
5. Commit: `git commit -m 'Add amazing feature'`
6. Push: `git push origin feature/amazing-feature`
7. Submit Pull Request

## License

This project is licensed under the MIT License - see LICENSE file for details.

## Support

For issues, questions, or suggestions, please open an issue on the repository.

## Roadmap

- [ ] JWT authentication
- [ ] OpenAPI/Swagger documentation
- [ ] Celery task queue
- [ ] Email notifications
- [ ] Database backups automation
- [ ] Prometheus metrics
- [ ] Sentry error tracking integration
- [ ] API documentation with auto-generated schemas
