# IoT Message Routing Platform

Production-grade Django REST API for routing messages between IoT devices based on group membership, network IDs (NID), and geographic proximity.

## System Overview

The platform provides centralized message routing for IoT devices using a deterministic 5-step filtering algorithm. Messages are stored in device-specific inbox queues for reliable delivery. The system supports both REST API access and web-based management interfaces.

### Core Functionality

- **Message Routing**: Automatic routing of messages from source devices to target devices using group membership, network ID (NID) filtering, and geographic distance calculations
- **Device Management**: Registration and management of IoT devices with hardware identifiers (HID), location data, webhook URLs, and user associations
- **User Management**: Owner/user accounts with group assignments, network IDs, and sub-user hierarchies
- **Inbox System**: Per-device inbox queues with status tracking (pending, delivered, acknowledged, failed)
- **Webhook Delivery**: Asynchronous webhook delivery via Celery with configurable retry logic and exponential backoff

## Architecture

### Components

- **Django Application**: Main web service handling HTTP requests, API endpoints, and frontend templates
- **Celery Worker**: Background task processor for webhook delivery
- **PostgreSQL + PostGIS**: Spatial database for geographic queries and device location storage
- **Redis**: Message broker and result backend for Celery

### Application Structure

```
iot_message_router/
├── accounts/          # User (Owner) models, authentication, registration
├── devices/           # Device models, registration, inbox management
├── messages/          # Message routing, inbox, groups, Celery tasks
├── api/               # Custom authentication and permissions
├── frontend/          # Web interface views and templates
└── iot_message_router/  # Django project settings, URLs, Celery config
```

## Tech Stack

- **Backend Framework**: Django 4.2.7, Django REST Framework 3.14.0
- **Database**: PostgreSQL 12+ with PostGIS extension (GeoDjango)
- **Task Queue**: Celery 5.3.4 with Redis 7
- **Authentication**: JWT (Simple JWT) for users, API keys (SHA-256 hashed) for devices
- **API Documentation**: drf-spectacular (OpenAPI/Swagger)
- **HTTP Client**: requests 2.31.0 (for webhook delivery)

## Routing Algorithm

The system uses a 5-step routing algorithm to determine target devices for each message:

1. **Group Filter**: Find all devices belonging to the sender's group type
   - Group types: Private, Exclusive, Open, Data-Logging, Enhanced, Location

2. **NID Filter**: Filter by Network ID (if group type requires it)
   - NID values normalized and matched (hex/decimal variants supported)
   - Broadcast NID (0xFFFFFFFF) supported for Location groups

3. **Distance Filter**: Filter by geographic distance using PostGIS (if group type requires it)
   - Uses device location (PointField, SRID 4326)
   - Radius specified in kilometers (owner-level or group-level)

4. **Exclusion**: Remove sender device from target list

5. **Inbox Population**: Create DeviceInbox entries for each target device
   - Status: PENDING → DELIVERED/ACKNOWLEDGED/FAILED
   - Webhook delivery triggered for devices with webhook_url configured

### Group Types

| Group Type | Uses NID | Uses Distance | Description |
|------------|----------|---------------|-------------|
| Private | Yes | No | Secure networks with network IDs |
| Exclusive | Yes | No | Exclusive device groups |
| Open | No | Yes | Public device networks (distance-based) |
| Data-Logging | Yes | No | Data collection from devices |
| Enhanced | Yes | Yes | Advanced routing with NID and distance |
| Location | Yes* | Yes | Location-based broadcast (*uses 0xFFFFFFFF for broadcast) |

## Authentication & Authorization

### JWT Authentication (Users/Owners)

- **Endpoint**: `POST /api/v1/auth/login/` (or `/api/auth/login/` for backward compatibility)
- **Request**: `{"username": "email@example.com", "password": "password"}`
- **Response**: `{"access": "...", "refresh": "..."}`
- **Usage**: Include in header: `Authorization: Bearer <access_token>`
- **Token Lifetime**: Access token 24 hours, refresh token 7 days
- **Blacklist**: Refresh tokens blacklisted on logout (requires token_blacklist app migrations)

### Rate Limiting

- **Anonymous Users**: 100 requests per hour
- **Authenticated Users**: 1000 requests per hour
- **Configurable**: Via `DEFAULT_THROTTLE_RATES` in settings

### API Key Authentication (Devices)

- **Header**: `X-API-Key: <device_api_key>`
- **Storage**: API keys stored as SHA-256 hashes in database
- **Verification**: Hash comparison on authentication
- **Generation**: Auto-generated on device creation (32-byte URL-safe token)

### Registration Flow

- **User Registration**: `POST /api/v1/auth/register/` returns user data with API key (only at creation) and JWT tokens
- **Device Registration**: `POST /api/v1/devices/` returns device data with API key (only at creation)

### Authorization Rules

- **Device Access**: Owner, associated users (M2M), or staff
- **Sub-users**: Cannot register devices or manage other users
- **API Keys**: Returned only at creation time; never exposed in subsequent responses

## Webhook Delivery Flow

1. **Message Creation**: Device sends message via API
2. **Routing**: MessageRoutingService routes to target devices
3. **Inbox Creation**: DeviceInbox entries created with status PENDING
4. **Task Queue**: Celery task `deliver_webhook` queued for devices with webhook_url
5. **Delivery**: HTTP POST to webhook_url with message payload
6. **Retry Logic**: Failed deliveries retried with exponential backoff (2^n seconds)
7. **Status Update**: Inbox status updated to DELIVERED/FAILED based on outcome

### Webhook Payload Format

```json
{
  "message_id": 123,
  "type": "alert",
  "alert_type": "sensor",
  "payload": {...},
  "timestamp": "2025-02-18T12:00:00Z",
  "source_device_hid": "DEVICE-001",
  "user": "user@example.com"
}
```

## Running with Docker

### Prerequisites

- Docker and Docker Compose installed

### Quick Start

```bash
# Clone repository
git clone <repository-url>
cd restapi_django_ssd-main

# Copy environment file
cp .env.example .env

# Set required environment variables
# SECRET_KEY=<generate-random-secret-key>
# ALLOWED_HOSTS=localhost,127.0.0.1

# Start all services
docker compose up -d
```

### Docker Services

- **db**: PostgreSQL + PostGIS (port 5432, internal only)
- **redis**: Redis server (port 6379, internal only)
- **web**: Django application (port 8080 → 8000)
- **celery**: Celery worker for background tasks

### Service Dependencies

- `web` and `celery` depend on `db` and `redis` health checks
- Migrations run automatically on `web` service startup
- Static files collected automatically on `web` service startup

### Access Points

- **Web Interface**: http://localhost:8080/
- **API v1 Root**: http://localhost:8080/api/v1/
- **API Documentation**: http://localhost:8080/api/docs/
- **OpenAPI Schema**: http://localhost:8080/api/schema/
- **Health Check**: http://localhost:8080/api/health/
- **Admin Panel**: http://localhost:8080/django-admin/

## Environment Variables

### Required Variables

- `SECRET_KEY`: Django secret key (must be set, raises error if missing)
- `ALLOWED_HOSTS`: Comma-separated list of allowed hostnames (must be set, raises error if empty)

### Database Configuration

- `DB_HOST`: Database host (default: `db` for Docker)
- `DB_NAME`: Database name (default: `iot_message_router`)
- `DB_USER`: Database user (default: `iot_user`)
- `DB_PASSWORD`: Database password (default: `iot_password`)
- `DB_PORT`: Database port (default: `5432`)

### Celery Configuration

- `CELERY_BROKER_URL`: Redis broker URL (default: `redis://redis:6379/0`)
- `CELERY_RESULT_BACKEND`: Redis result backend (default: `redis://redis:6379/0`)

### Optional Variables

- `DEBUG`: Debug mode (default: `False`, cannot be `True` in production settings)
- `CORS_ALLOWED_ORIGINS`: Comma-separated CORS origins
- `CSRF_TRUSTED_ORIGINS`: Comma-separated CSRF trusted origins
- `INTERNAL_API_BASE_URL`: Internal API base URL for server-side calls (default: empty)
- `SENTRY_DSN`: Sentry error tracking DSN (optional, requires sentry-sdk package)
- `ENVIRONMENT`: Environment name for Sentry (default: `production`)

### Production Settings

Set `DJANGO_SETTINGS_MODULE=iot_message_router.settings_production` to enable:
- `DEBUG=False`
- SSL redirect and HSTS headers
- Secure cookies
- File logging with rotation
- Strict SECRET_KEY validation

## API Documentation

### OpenAPI/Swagger

- **Interactive Documentation**: `/api/docs/`
- **OpenAPI Schema**: `/api/schema/`
- **API Versioning**: All endpoints available under `/api/v1/` prefix
- **Backward Compatibility**: Legacy `/api/` endpoints still supported

### Health Check Endpoint

- **Endpoint**: `GET /api/health/`
- **Purpose**: System health monitoring and load balancer checks
- **Response Codes**:
  - `200 OK`: All systems operational
  - `503 Service Unavailable`: One or more systems unhealthy
- **Checks**: Database connectivity, Redis connectivity, Celery worker status
- **Response Format**:
  ```json
  {
    "status": "healthy",
    "version": "1.0.0",
    "checks": {
      "database": {"status": "healthy", "error": null},
      "redis": {"status": "healthy", "error": null},
      "celery": {"status": "healthy", "workers": ["celery@hostname"], "error": null}
    }
  }
  ```

### Main Endpoints

**Note**: All endpoints are available under `/api/v1/` prefix. Legacy `/api/` paths remain for backward compatibility.

#### Authentication

- `POST /api/v1/auth/register/` - User registration
- `POST /api/v1/auth/login/` - JWT token obtain
- `POST /api/v1/auth/refresh/` - Refresh access token
- `POST /api/v1/auth/logout/` - Logout (blacklist refresh token)
- `GET /api/v1/info/` - API information and endpoint list

#### Owners

- `GET /api/v1/owners/` - List owners
- `POST /api/v1/owners/` - Create owner
- `GET /api/v1/owners/{id}/` - Get owner
- `PATCH /api/v1/owners/{id}/` - Update owner
- `DELETE /api/v1/owners/{id}/` - Delete owner
- `GET /api/v1/owners/me/` - Current user profile
- `GET /api/v1/owners/{id}/devices/` - Owner's devices

#### Devices

- `GET /api/v1/devices/` - List devices (filtered by ownership/association)
- `POST /api/v1/devices/` - Register device (returns API key at creation)
- `GET /api/v1/devices/{id}/` - Get device
- `PATCH /api/v1/devices/{id}/` - Update device
- `DELETE /api/v1/devices/{id}/` - Delete device
- `GET /api/v1/devices/hid/{hid}/` - Get device by HID
- `GET /api/v1/devices/{id}/inbox/` - Get device inbox
- `POST /api/v1/devices/{id}/inbox/{message_id}/ack/` - Acknowledge message

#### Messages

- `GET /api/v1/messages/` - List messages (filtered by user's devices)
- `POST /api/v1/messages/` - Create message
- `GET /api/v1/messages/{id}/` - Get message
- `GET /api/v1/messages/hid/{hid}/` - Get messages for device (paginated: startIndex, size)
- `POST /api/v1/messages/hid/{hid}/` - Send message from device (API key or JWT)
- `GET /api/v1/messages/hid/{hid}/{message_id}/` - Get specific message
- `PATCH /api/v1/messages/hid/{hid}/{message_id}/` - Update message
- `DELETE /api/v1/messages/hid/{hid}/{message_id}/` - Delete message

#### Groups

- `GET /api/v1/groups/` - List groups
- `POST /api/v1/groups/` - Create group
- `GET /api/v1/groups/{id}/` - Get group
- `PATCH /api/v1/groups/{id}/` - Update group
- `DELETE /api/v1/groups/{id}/` - Delete group

#### Network Queries

- `GET /api/v1/network/hid/{hid}/` - Get devices within network range
- `GET /api/v1/network/owners/{owner_id}/` - Get owners within network range

## Security & Logging

### Authentication & Authorization

- JWT tokens use HS256 algorithm with SECRET_KEY
- Refresh tokens blacklisted on logout (requires token_blacklist app migrations)
- Device API keys hashed with SHA-256 before storage
- API keys returned only at creation time, never in subsequent responses
- Rate limiting: 100/hour (anonymous), 1000/hour (authenticated)

### Authorization

- Default permission: `IsAuthenticated` for all API endpoints
- Device access: Owner or associated users (M2M relationship) or staff
- Sub-users cannot register devices or manage other users

### Data Protection

- SECRET_KEY must be set via environment variable (raises error if missing)
- DEBUG defaults to False (cannot be True in production settings)
- ALLOWED_HOSTS must be explicitly set (raises error if empty)
- CSRF protection enabled for frontend forms
- CORS configured with explicit allowed origins
- Password hashing: Django default (PBKDF2)

### Logging

- **Directory**: `logs/` (auto-created if missing)
- **File Handler**: Rotating file handler (10 MB max, 5 backups)
- **Log Files**: `logs/django.log` (Django and application logs)
- **Log Levels**: INFO+ in production (DEBUG disabled)
- **Celery Logs**: Included in rotation, separate logger configured
- **Format**: Verbose format with process/thread IDs, timestamps
- **Error Tracking**: Optional Sentry integration (set `SENTRY_DSN` environment variable)

### Production Hardening

- SSL redirect and HSTS headers (production settings)
- Secure cookies (HTTPS only in production)
- Logging to file with rotation (10 MB, 5 backups)
- No debug-level logs in production
- Static files served via collectstatic (use CDN/static server in production)
- Health check endpoint for monitoring
- Celery worker healthcheck in Docker
- Strict environment variable validation

## Production Notes

### Database Migrations

Run migrations before starting services:

```bash
docker compose exec web python manage.py migrate
```

Or migrations run automatically via docker-entrypoint.sh for `web` service.

### Static Files

Collect static files:

```bash
docker compose exec web python manage.py collectstatic --noinput
```

Or collected automatically on `web` service startup.

### Celery Worker

Celery worker runs as separate service (`celery`) with healthcheck. Automatically starts with `docker compose up`:

```bash
docker compose up -d celery
```

Healthcheck verifies worker is responsive. Check status:

```bash
docker compose ps celery
docker compose logs celery
```

### Logging

Logs written to `logs/django.log` (created automatically). Log rotation: 10 MB max, 5 backups. Celery logs included in rotation.

### Monitoring

- Monitor Celery worker logs: `docker compose logs -f celery`
- Monitor web service logs: `docker compose logs -f web`
- Monitor database health: `docker compose ps db`

### Scaling

- Run multiple Celery workers: `docker compose up -d --scale celery=3`
- Use load balancer for `web` service
- Use Redis Sentinel for high availability
- Use PostgreSQL replication for database redundancy

### Backup

- Backup PostgreSQL database regularly
- Backup Redis data if using persistent storage
- Backup static/media files if using local storage

## Development

### Local Development (Without Docker)

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install GDAL (system dependency)
# Ubuntu/Debian: sudo apt-get install gdal-bin libgdal-dev python3-gdal
# macOS: brew install gdal

# Set environment variables
export SECRET_KEY=<your-secret-key>
export ALLOWED_HOSTS=localhost,127.0.0.1
export DB_HOST=localhost
export DB_NAME=iot_message_router
export DB_USER=iot_user
export DB_PASSWORD=iot_password

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Start development server
python manage.py runserver

# Start Celery worker (separate terminal)
celery -A iot_message_router worker -l info
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html --cov-report=xml

# Coverage reports written to logs/coverage/
# HTML report: logs/coverage/index.html
# XML report: logs/coverage/coverage.xml

# Run specific test file
pytest tests/test_api_endpoints.py

# Run with markers
pytest -m integration
pytest -m unit
```

## License

See LICENSE file for details.
