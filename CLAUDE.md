# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Development (uv - Recommended)
```bash
# Install dependencies (modern Python package manager)
uv sync --dev

# Run the application
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Alternative: Use development script
./scripts/dev.sh run

# Install dependencies only
./scripts/dev.sh install

# Code formatting
./scripts/dev.sh format

# Linting
./scripts/dev.sh lint

# Run tests
./scripts/dev.sh test

# Run tests with coverage
./scripts/dev.sh test-cov
```

### Development (Traditional pip)
```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Test API endpoints
chmod +x scripts/test-api.sh
./scripts/test-api.sh

# Performance testing
python scripts/performance_test.py
```

### Database
```bash
# Initialize database
python scripts/init-database.sh

# Database migration (with uv)
uv run python scripts/migration_manager.py

# Database migration (Alembic)
uv run alembic upgrade head

# Create new migration
uv run alembic revision --autogenerate -m "Description"

# Test database connection
uv run python test_database_connection.py
```

### Deployment
```bash
# Deploy to MicroK8s
chmod +x scripts/deploy.sh
./scripts/deploy.sh

# Monitor system
chmod +x scripts/monitor.sh
./scripts/monitor.sh

# Backup database
chmod +x scripts/backup-database.sh
./scripts/backup-database.sh
```

### Testing

#### Local Testing (uv/pip)
```bash
# Run all tests with uv
uv run pytest tests/ -v

# Run specific test files
uv run python test_redis_connection.py
uv run python test_file_validation.py
uv run python test_ip_auth.py
uv run python test_metadata_service.py

# Integration tests
uv run python test_task6_integration.py

# Test with coverage
uv run pytest tests/ --cov=app --cov-report=html

# Run tests by category
uv run pytest tests/unit/ -v
uv run pytest tests/integration/ -v
```

#### Container-Based Testing (Recommended)
```bash
# Run all tests in containers with full service dependencies
./scripts/run-container-tests.sh

# Run specific test types
./scripts/run-container-tests.sh unit        # Unit tests only
./scripts/run-container-tests.sh integration # Integration tests only
./scripts/run-container-tests.sh api         # API tests only
./scripts/run-container-tests.sh pytest     # Full pytest suite

# Direct Docker Compose commands
docker-compose -f docker-compose.test.yml up -d  # Start test environment
docker-compose -f docker-compose.test.yml run --rm pytest-runner  # Run pytest
docker-compose -f docker-compose.test.yml run --rm api-test-runner /app/scripts/test-api.sh  # Run API tests
docker-compose -f docker-compose.test.yml down -v  # Clean up
```

## Configuration & Setup

### Environment Configuration
The project uses a sophisticated configuration system with `pydantic-settings`:

```bash
# Copy environment template
cp env.example .env

# Edit configuration (required)
nano .env  # or your preferred editor
```

**Key Configuration Categories:**
- **Storage Settings**: Flexible path mapping for host/container environments
- **Storage Types**: Local, S3, Azure Blob, Google Cloud Storage support
- **Storage Structures**: Date-based, UUID-based, or flat file organization
- **Database**: MariaDB container with connection pooling
- **Redis**: Caching with connection pool and failover support
- **Security**: IP authentication, RBAC, rate limiting, CORS policies

### Project Key Management
This project includes a project key management system for secure API access:

```bash
# Test project key functionality
python quick_test_keygen_upload.py

# Run integration tests with project keys
python test_keygen_upload_integration.py

# Test project key upload via curl
./test_keygen_upload_curl.sh
```

The project key system allows for authenticated file uploads and project-based access control.

## Architecture

### Core Structure
- **FastAPI Application**: `app/main.py` - Main application entry point with dual upload APIs
- **API Layer**: `app/api/v1/` - V1 API endpoints (files, projects, health, IP auth)
- **Database Models**: `app/models/` - ORM models, API models, file models, and Swagger models
- **Services Layer**: `app/services/` - 20+ business logic services (file storage, metadata, caching, rate limiting, RBAC)
- **Routers**: `app/routers/` - Legacy API route handlers (being migrated to `app/api/v1/`)
- **Middleware**: `app/middleware/` - Security headers, CORS, audit logging, request ID, metrics
- **Dependencies**: `app/dependencies/` - Dependency injection for auth, database, Redis, settings
- **Repositories**: `app/repositories/` - Data access layer abstraction
- **Utils**: `app/utils/` - Utility functions for database, security, performance analysis
- **Validators**: `app/validators/` - File validation logic

### Key Services (20+ Service Modules)
**Core File Services:**
- **FileStorageService**: Handles file uploads with SHA-256 deduplication and flexible storage backends
- **MetadataService**: Manages file metadata with database persistence and tagging
- **FileValidationService**: Enhanced validation with magic number detection and malware patterns
- **ThumbnailService**: Automatic thumbnail generation for image files

**Caching & Performance:**
- **CacheService**: Redis-based caching with dynamic TTL policies
- **CacheInvalidationService**: Intelligent cache invalidation strategies
- **CacheMonitoringService**: Cache performance monitoring and analytics
- **CacheFallbackService**: Database fallback when Redis unavailable

**Security & Access Control:**
- **RBACService**: Role-based access control with audit logging
- **IPAuthService**: IP-based authentication and access control
- **RateLimiterService**: Redis-backed rate limiting (hourly/daily)
- **ErrorHandlerService**: Centralized error handling with metrics

**Infrastructure Services:**
- **RedisConnectionManager**: Advanced Redis connection pooling with circuit breaker
- **SchedulerService**: Background task scheduling (file cleanup, maintenance)
- **StatisticsService**: File usage analytics and reporting
- **ProjectKeyService**: Project-based authentication and key management
- **BackgroundTaskService**: Async background processing
- **HealthCheckService**: System health monitoring

### Database Design
- **SQLAlchemy ORM**: Database models in `app/models/orm_models.py`
- **Alembic Migrations**: Database versioning in `alembic/versions/`
- **Performance Optimizations**: Indexed queries, connection pooling, ACID transactions
- **Database Helpers**: Utility functions in `app/utils/database_helpers.py`

### Storage Architecture
**Flexible Storage System:**
- **Storage Types**: Local, S3, Azure Blob, Google Cloud Storage
- **Storage Structures**: Date-based (`YYYY/MM/DD`), UUID-based hierarchical, or flat structure
- **Path Mapping**: Host OS ↔ Container path mapping for Docker/Kubernetes
- **Deduplication**: SHA-256 based to prevent duplicate storage
- **Thumbnails**: Generated for image files in `uploads/thumbnails/`
- **Background Processing**: Hash calculation and metadata extraction

**Storage Configuration Examples:**
```bash
# Date-based structure (production recommended)
STORAGE_STRUCTURE=date
STORAGE_DATE_FORMAT=%Y/%m/%d

# UUID-based hierarchical (development)
STORAGE_STRUCTURE=uuid  
STORAGE_UUID_DEPTH=2  # /ab/cd/abcd1234-...

# Flat structure (simple setups)
STORAGE_STRUCTURE=flat
```

### Security Features
- **Security Headers**: Comprehensive security headers middleware
- **CORS Policy**: Configurable allowed origins
- **File Validation**: Magic number validation, extension checking, malware patterns
- **Rate Limiting**: IP-based with Redis persistence
- **Audit Logging**: RBAC-based access logging
- **IP Authentication**: Configurable IP-based access control

### Monitoring & Metrics
- **Prometheus Integration**: Custom metrics for uploads, downloads, errors
- **Health Checks**: Database, Redis, and storage health monitoring
- **Performance Monitoring**: Request duration, active connections, cache hits/misses
- **Error Tracking**: Categorized error metrics and statistics

### Redis Integration
- **Connection Management**: Pool-based Redis connections with failover
- **Caching Strategy**: File metadata, rate limiting counters, session management
- **Monitoring**: Redis performance monitoring and alerting
- **Fallback**: Database fallback when Redis is unavailable

### Kubernetes Deployment
- **Namespace**: `filewallball`
- **Auto-scaling**: HPA based on CPU (70%) and memory (80%) thresholds
- **Storage**: PersistentVolume for file storage
- **Services**: MariaDB, Redis, and application services
- **Monitoring**: Prometheus metrics collection

### API Endpoints
**Legacy Endpoints (app/routers/):**
- **Upload**: `/upload` - Basic file upload with Redis caching
- **File Operations**: `/files/{id}`, `/download/{id}`, `/view/{id}`
- **Health**: `/health` - Basic health check

**V1 API Endpoints (app/api/v1/):**
- **Files**: `/api/v1/files/` - Enhanced file operations with validation and metadata
- **Projects**: `/api/v1/projects/` - Project key management and authentication
- **Health**: `/api/v1/health/` - Detailed health monitoring
- **IP Auth**: `/api/v1/ip-auth/` - IP-based authentication management

**System Endpoints:**
- **Metrics**: `/metrics` - Prometheus metrics endpoint
- **Documentation**: `/docs` - Swagger UI, `/redoc` - ReDoc documentation

## Important Implementation Details

### Core Patterns
- **Dual API Architecture**: Legacy endpoints (`/upload`, `/files/`) and modern V1 API (`/api/v1/`) 
- **Project-Based Authentication**: Project key system for secure API access with granular permissions
- **Service-Oriented Architecture**: 20+ specialized services with clear separation of concerns
- **Repository Pattern**: Data access layer abstraction in `app/repositories/`
- **Dependency Injection**: Comprehensive DI system in `app/dependencies/` for testability
- **Middleware Stack**: Security headers, CORS, audit logging, request tracking, metrics
- **Background Processing**: AsyncIO tasks for hash calculation, thumbnail generation, cleanup
- **Async/Await Pattern**: Fully async application with async database and Redis clients

### Database & Storage
- **MariaDB Container**: Production-ready MariaDB running in container with Alembic migrations
- **File Deduplication**: SHA-256 hashing prevents duplicate storage across all storage backends
- **Flexible Storage**: Local, S3, Azure, GCS with configurable directory structures
- **ACID Transactions**: Database operations use proper transaction management

### Caching Strategy
- **Dynamic TTL**: Cache TTL varies based on file size, access frequency, and file type
- **Cache Warming**: Preloading popular files into cache
- **Circuit Breaker**: Redis connection management with automatic failover to database
- **Cache Invalidation**: Intelligent invalidation strategies for data consistency

### Security & Monitoring
- **Multi-Layer Security**: IP authentication, RBAC, rate limiting, file validation with magic numbers
- **Audit Logging**: All operations logged with RBAC-based access control
- **Rate Limiting**: Redis-backed limiting with persistence across restarts
- **Prometheus Integration**: Custom metrics for uploads, downloads, errors, cache performance
- **Health Checks**: Comprehensive health monitoring for all system components

### Configuration Management
- **Environment-Based**: Pydantic settings with comprehensive validation
- **Container-Aware**: Automatic path mapping for Docker/Kubernetes deployments
- **Multi-Cloud Ready**: Support for major cloud storage providers out of the box
- **Configuration Files**: `pyproject.toml` for Python project config, `env.example` for environment template
- **Development Tools**: Black, isort, flake8, mypy, pytest configurations in `pyproject.toml`

### Development Guidelines
This codebase includes Cursor rules for consistency:

- **Code Quality**: Follow patterns in `.cursor/rules/cursor_rules.mdc`
- **Self-Improvement**: Continuous rule improvement based on `.cursor/rules/self_improve.mdc`
- **Consistent Standards**: Use bullet points, actionable requirements, and clear examples
- **Rule Maintenance**: Update rules when new patterns emerge, reference actual code examples