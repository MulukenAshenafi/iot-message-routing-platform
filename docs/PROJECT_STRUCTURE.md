# Project Structure Guide

This document explains the clean, organized structure of the IoT Message Routing System.

## Directory Structure

### Core Applications

#### `accounts/` - User Management
- **Purpose**: Manages Owner (user) accounts and authentication
- **Key Files**:
  - `models.py`: Owner model (extends AbstractUser, email as USERNAME_FIELD)
  - `serializers.py`: Owner serializers for API
  - `views.py`: OwnerViewSet (CRUD operations)
  - `admin.py`: Django admin configuration

#### `devices/` - Device Management
- **Purpose**: Manages IoT devices, API keys, and device-user associations
- **Key Files**:
  - `models.py`: Device model with PostGIS PointField, MAX_USERS=6 validation
  - `serializers.py`: Device serializers with user_ids field
  - `views.py`: DeviceViewSet with inbox and acknowledgment endpoints
  - `admin.py`: Admin interface for devices

#### `messages/` - Message Routing & Inbox
- **Purpose**: Handles message creation, routing algorithm, and device inbox
- **Key Files**:
  - `models.py`: Message, DeviceInbox, Group models
  - `serializers.py`: Message and inbox serializers
  - `services.py`: MessageRoutingService - 5-step routing algorithm
  - `tasks.py`: Celery tasks for async webhook delivery
  - `views.py`: MessageViewSet, network queries
  - `admin.py`: Admin for messages and inbox

#### `api/` - API Utilities
- **Purpose**: Shared API components
- **Key Files**:
  - `permissions.py`: DeviceAPIKeyAuthentication class

#### `frontend/` - Web UI
- **Purpose**: Django template-based frontend interface
- **Key Files**:
  - `views.py`: Template views for all pages
  - `urls.py`: Frontend URL routing
  - `management/commands/create_sample_data.py`: Sample data generator

### Project Configuration

#### `iot_message_router/` - Django Settings
- **Purpose**: Main Django project configuration
- **Key Files**:
  - `settings.py`: Complete configuration (PostGIS, JWT, Celery, CORS, etc.)
  - `settings_production.py`: Production-specific overrides
  - `urls.py`: Root URL configuration (API + Frontend)
  - `celery.py`: Celery app configuration
  - `wsgi.py`: WSGI application entry point
  - `asgi.py`: ASGI application entry point

### Testing

#### `tests/` - Test Suite
- **Purpose**: Comprehensive test coverage
- **Key Files**:
  - `conftest.py`: Shared pytest fixtures
  - `test_phase0_requirements.py`: Phase 0 Technical Design compliance tests
  - `test_api_endpoints.py`: API endpoint integration tests
  - `test_requirements.py`: Original requirements verification
  - `test_models.py`: Model unit tests

**Test Categories:**
- `@pytest.mark.unit`: Unit tests for components
- `@pytest.mark.integration`: API endpoint integration tests
- `@pytest.mark.model`: Database model tests
- `@pytest.mark.routing`: Message routing logic tests
- `@pytest.mark.authentication`: Auth tests (JWT, API keys)
- `@pytest.mark.phase0`: Phase 0 requirement tests

### Documentation

#### `docs/` - Documentation
- **Purpose**: Project documentation
- **Files**:
  - `REQUIREMENTS_CHECKLIST.md`: Complete requirements tracking
  - `PHASE0_COMPLIANCE_REPORT.md`: Phase 0 compliance analysis
  - `IMPLEMENTATION_VERIFICATION.md`: Implementation verification
  - `PROJECT_STRUCTURE.md`: This file

### Static & Templates

#### `static/` - Static Files (Source)
- CSS, JavaScript, images
- Organized by app: `static/frontend/`

#### `templates/` - Django Templates
- HTML templates organized by app
- Base templates: `base.html`, `base_dashboard.html`
- Page templates: Login, Register, Dashboard, Studio, Inbox, etc.

### Scripts

#### `scripts/` - Utility Scripts
- `run_tests.sh`: Comprehensive test runner
- `verify_system.py`: System health verification

## File Organization Principles

1. **Separation of Concerns**: Each app handles one domain (accounts, devices, messages)
2. **Testability**: All components are easily testable with clear test structure
3. **Documentation**: Requirements and compliance clearly documented
4. **Clean Structure**: No temporary files, proper .gitignore
5. **Configuration Management**: Settings separated (dev/production)

## Key Design Decisions

### Models
- **Device.users**: ManyToManyField with MAX_USERS=6 validation (Phase 0 requirement)
- **Location**: PostGIS PointField for geographic queries
- **API Keys**: Hashed storage for security

### Routing
- **Service Layer**: `MessageRoutingService` separates routing logic from views
- **5-Step Algorithm**: Clearly defined in `services.py`

### Authentication
- **Dual Auth**: JWT for users, API keys for devices
- **Permission Classes**: Custom `DeviceAPIKeyAuthentication`

### Testing
- **Comprehensive Coverage**: Unit, integration, and requirement tests
- **Pytest Fixtures**: Reusable test data in `conftest.py`
- **Markers**: Test categorization for selective running

## Adding New Features

### Add New Model
1. Create model in appropriate app (`models.py`)
2. Create serializer (`serializers.py`)
3. Create ViewSet (`views.py`)
4. Register in admin (`admin.py`)
5. Create migration: `python manage.py makemigrations`
6. Add tests (`tests/test_models.py`)

### Add New API Endpoint
1. Add to ViewSet (`views.py`)
2. Add URL route (auto-registered via DRF router)
3. Add serializer if needed
4. Add integration test (`tests/test_api_endpoints.py`)
5. Update API documentation

### Add New Test
1. Add to appropriate test file or create new one
2. Use fixtures from `conftest.py`
3. Mark with appropriate pytest markers
4. Ensure it passes: `pytest tests/your_test.py -v`

## Maintenance

### Code Quality
- Run linters: `flake8`, `pylint` (add to CI/CD)
- Type hints: Add gradually for better IDE support
- Documentation: Keep docstrings updated

### Dependencies
- Update `requirements.txt` when adding packages
- Pin versions for production stability
- Review and update regularly for security

### Database
- Migrations: Always create migrations for model changes
- Backups: Regular database backups in production
- PostGIS: Ensure extension is enabled in all environments

