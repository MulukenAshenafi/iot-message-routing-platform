# User Guide - IoT Message Routing System

## Who Can Use This Project?

### 🎯 Target Users

#### 1. **IoT Device Manufacturers**
- Companies building IoT devices that need message routing
- Device manufacturers requiring geographic-based message distribution
- Hardware companies needing device-to-device communication

#### 2. **IoT Platform Providers**
- Companies building IoT platforms and services
- Platform providers needing message routing infrastructure
- Service providers offering IoT connectivity solutions

#### 3. **System Integrators**
- Companies integrating IoT solutions for clients
- System integrators building custom IoT applications
- Consultants implementing IoT messaging systems

#### 4. **Developers & Engineers**
- Backend developers building IoT applications
- Full-stack developers creating IoT platforms
- DevOps engineers deploying IoT infrastructure
- Software engineers implementing message routing

#### 5. **Enterprises & Organizations**
- Companies with IoT device fleets
- Organizations needing device communication systems
- Businesses requiring geographic message distribution
- Companies managing multiple IoT devices

#### 6. **Startups & Entrepreneurs**
- Startups building IoT products
- Entrepreneurs creating IoT services
- Small businesses entering IoT market

---

## How This Project Helps

### 🚀 Key Benefits & Use Cases

#### 1. **Message Routing & Distribution**
**Problem Solved**: Need to route messages from one device to multiple devices based on various criteria.

**How It Helps**:
- Automatically routes messages to target devices
- Supports 6 different routing strategies (group types)
- Filters by network ID (NID) and geographic distance
- Ensures messages reach the right devices efficiently

**Use Cases**:
- Emergency alert systems (route alerts to nearby devices)
- Sensor data distribution (share sensor readings with nearby devices)
- Fleet management (communicate with vehicles in specific areas)
- Smart city applications (distribute information to devices in zones)

#### 2. **Geographic-Based Communication**
**Problem Solved**: Need to send messages only to devices within a specific geographic area.

**How It Helps**:
- Uses PostGIS for accurate distance calculations
- Filters devices by radius (kilometers)
- Supports location-based messaging
- Real-time location tracking and updates

**Use Cases**:
- Location-based alerts (notify devices within 5km radius)
- Geographic zone messaging (send to all devices in a city)
- Proximity-based communication (nearby device discovery)
- Regional notifications (country/state/city level)

#### 3. **Device Inbox System**
**Problem Solved**: Devices need a reliable way to receive messages even when offline.

**How It Helps**:
- Server-side message queue (database-backed)
- Devices can poll for messages at their convenience
- Messages stored until acknowledged
- No message loss even if device is temporarily offline

**Use Cases**:
- Offline device communication
- Reliable message delivery
- Message queuing for intermittent connectivity
- Command distribution to devices

#### 4. **Webhook Push Notifications**
**Problem Solved**: Need real-time push notifications to devices.

**How It Helps**:
- Async webhook delivery via Celery
- Configurable retry logic per device
- Exponential backoff for failed deliveries
- Real-time message push to device endpoints

**Use Cases**:
- Real-time alerts and notifications
- Instant message delivery
- Push notifications to device servers
- Webhook-based integrations

#### 5. **Multi-Device Management**
**Problem Solved**: Managing multiple IoT devices and their communication.

**How It Helps**:
- Centralized device management
- Owner-based device organization
- Group-based device organization
- Device registration and tracking

**Use Cases**:
- Fleet management (manage multiple vehicles)
- Smart home systems (manage multiple devices)
- Industrial IoT (manage factory equipment)
- Asset tracking (track multiple assets)

#### 6. **Secure Device Authentication**
**Problem Solved**: Need secure authentication for IoT devices.

**How It Helps**:
- API key authentication for devices
- Server-generated, hashed API keys
- Secure device-to-server communication
- JWT authentication for users

**Use Cases**:
- Secure device registration
- Authenticated device communication
- API access control
- Secure message sending

#### 7. **Role-Based Access Control**
**Problem Solved**: Different users need different levels of access.

**How It Helps**:
- Admin users: Full access to all devices/messages
- Regular users: Access only to their own devices
- Permission-based API access
- Secure multi-user system

**Use Cases**:
- Multi-tenant IoT platforms
- Enterprise device management
- Customer-specific device access
- Admin vs user separation

---

## How to Use This Project

### 📋 Prerequisites

Before using this project, ensure you have:
- Python 3.11 or higher
- PostgreSQL 12+ with PostGIS extension
- Redis (for Celery)
- Docker & Docker Compose (optional, recommended)
- GDAL library (for PostGIS support)

---

### 🚀 Quick Start Guide

#### Option 1: Using Docker (Recommended)

**Step 1: Clone the Repository**
```bash
git clone https://github.com/shome/restapi_django.git
cd restapi_django
```

**Step 2: Configure Environment**
```bash
cp .env.example .env
# Edit .env with your settings
```

**Step 3: Start Services**
```bash
docker compose up -d
```

**Step 4: Run Migrations**
```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

**Step 5: Access the Application**
- Frontend: http://localhost:8000
- API: http://localhost:8000/api/
- Admin: http://localhost:8000/admin/

#### Option 2: Manual Setup

**Step 1: Install Dependencies**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Step 2: Install GDAL**
```bash
# Ubuntu/Debian
sudo apt-get install gdal-bin libgdal-dev python3-gdal

# Or use provided script
sudo bash install_gdal.sh
```

**Step 3: Setup Database**
```bash
# Create PostgreSQL database
sudo -u postgres createdb iot_message_router
sudo -u postgres psql -d iot_message_router -c "CREATE EXTENSION postgis;"
```

**Step 4: Configure Settings**
```bash
# Edit .env file with database credentials
DB_NAME=iot_message_router
DB_USER=your_user
DB_PASSWORD=your_password
```

**Step 5: Run Migrations**
```bash
python manage.py migrate
python manage.py createsuperuser
```

**Step 6: Start Services**
```bash
# Terminal 1: Django server
python manage.py runserver

# Terminal 2: Celery worker
celery -A iot_message_router worker -l info
```

---

### 📖 Usage Examples

#### 1. **User Registration & Login**

**Register a New User:**
```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "password": "securepass123",
    "password_confirm": "securepass123"
  }'
```

**Login:**
```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john@example.com",
    "password": "securepass123"
  }'
```

**Response:**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

#### 2. **Create a Group**

```bash
curl -X POST http://localhost:8000/api/groups/ \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "group_type": "enhanced",
    "nid": "network-001",
    "radius": 10.0,
    "description": "Enhanced group with NID and distance"
  }'
```

#### 3. **Register a Device**

```bash
curl -X POST http://localhost:8000/api/devices/ \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "hid": "DEVICE-001",
    "group_id": 1,
    "nid": "network-001",
    "location_lat": 43.6532,
    "location_lon": -79.3832,
    "webhook_url": "https://your-device-server.com/webhook",
    "retry_limit": 3
  }'
```

**Response:**
```json
{
  "device_id": 1,
  "hid": "DEVICE-001",
  "api_key": "abc123xyz...",
  "location": {...},
  ...
}
```

**⚠️ Important**: Save the `api_key` - you'll need it for device authentication!

#### 4. **Send a Message (Device Authentication)**

```bash
curl -X POST http://localhost:8000/api/messages/hid/DEVICE-001/ \
  -H "X-API-Key: <device_api_key>" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "alert",
    "payload": {
      "type": "SENSOR",
      "nid": "network-001",
      "position": {
        "latitude": 43.6532,
        "longitude": -79.3832
      },
      "message": "Temperature reading: 25°C"
    }
  }'
```

**Response:**
```json
{
  "message_id": 1,
  "status": "routed",
  "target_devices": 5,
  "inbox_entries": [1, 2, 3, 4, 5]
}
```

#### 5. **Poll Device Inbox**

```bash
curl -X GET http://localhost:8000/api/devices/1/inbox/ \
  -H "Authorization: Bearer <your_jwt_token>"
```

**Response:**
```json
[
  {
    "id": 1,
    "message": {
      "message_id": 1,
      "type": "alert",
      "payload": {...},
      "timestamp": "2024-01-15T10:30:00Z"
    },
    "status": "pending",
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

#### 6. **Acknowledge Message**

```bash
curl -X POST http://localhost:8000/api/devices/1/inbox/1/ack/ \
  -H "Authorization: Bearer <your_jwt_token>"
```

---

### 🖥️ Using the Web Interface

#### 1. **Access the Frontend**
Navigate to: `http://localhost:8000`

#### 2. **Login**
- Use your registered email/username and password
- Or register a new account

#### 3. **Dashboard**
- View your devices
- See system statistics
- Access quick actions

#### 4. **Studio (Message Testing)**
- Select a device
- API key auto-fills
- Compose and send messages
- View device inbox in real-time

#### 5. **Inbox**
- View all messages
- Filter by device
- See message details

#### 6. **Device Management**
- Register new devices
- View device details
- Manage device settings

#### 7. **Settings**
- Update your profile
- Change account information

---

### 🔧 Common Use Cases & Workflows

#### Use Case 1: Emergency Alert System

**Scenario**: Send emergency alerts to all devices within 5km radius.

**Steps**:
1. Create an "Open" group with radius = 5.0 km
2. Register devices with locations
3. Send alert message with location
4. System routes to all devices within 5km

**Example**:
```bash
# Create Open group
POST /api/groups/
{
  "group_type": "open",
  "radius": 5.0
}

# Send emergency alert
POST /api/messages/hid/DEVICE-001/
{
  "type": "alarm",
  "payload": {
    "position": {"latitude": 43.6532, "longitude": -79.3832},
    "message": "Emergency: Evacuate area immediately!"
  }
}
```

#### Use Case 2: Network-Based Communication

**Scenario**: Devices in same network (NID) communicate with each other.

**Steps**:
1. Create a "Private" group
2. Register devices with same NID
3. Send messages - only devices with same NID receive them

**Example**:
```bash
# Create Private group
POST /api/groups/
{
  "group_type": "private",
  "nid": "building-001"
}

# Register devices with same NID
POST /api/devices/
{
  "hid": "DEVICE-001",
  "group_id": 1,
  "nid": "building-001"
}
```

#### Use Case 3: Hybrid Routing (NID + Distance)

**Scenario**: Send messages to devices with same NID AND within 10km.

**Steps**:
1. Create an "Enhanced" group with NID and radius
2. Register devices with locations and NID
3. Send messages - filtered by both criteria

**Example**:
```bash
# Create Enhanced group
POST /api/groups/
{
  "group_type": "enhanced",
  "nid": "city-001",
  "radius": 10.0
}
```

---

### 📱 Integration Examples

#### Python Client Example

```python
import requests

# Login
response = requests.post('http://localhost:8000/api/auth/login/', json={
    'username': 'user@example.com',
    'password': 'password123'
})
token = response.json()['access']

# Register device
headers = {'Authorization': f'Bearer {token}'}
device = requests.post('http://localhost:8000/api/devices/', 
    headers=headers,
    json={
        'hid': 'PYTHON-DEVICE-001',
        'group_id': 1,
        'location_lat': 43.6532,
        'location_lon': -79.3832
    }
).json()

api_key = device['api_key']

# Send message
message = requests.post(
    f'http://localhost:8000/api/messages/hid/{device["hid"]}/',
    headers={'X-API-Key': api_key},
    json={
        'type': 'alert',
        'payload': {
            'message': 'Hello from Python!',
            'position': {'latitude': 43.6532, 'longitude': -79.3832}
        }
    }
).json()

print(f"Message sent! Routed to {message['target_devices']} devices")
```

#### JavaScript/Node.js Example

```javascript
const axios = require('axios');

// Login
const loginResponse = await axios.post('http://localhost:8000/api/auth/login/', {
    username: 'user@example.com',
    password: 'password123'
});
const token = loginResponse.data.access;

// Register device
const deviceResponse = await axios.post('http://localhost:8000/api/devices/', {
    hid: 'NODE-DEVICE-001',
    group_id: 1,
    location_lat: 43.6532,
    location_lon: -79.3832
}, {
    headers: { Authorization: `Bearer ${token}` }
});

const apiKey = deviceResponse.data.api_key;

// Send message
const messageResponse = await axios.post(
    `http://localhost:8000/api/messages/hid/${deviceResponse.data.hid}/`,
    {
        type: 'alert',
        payload: {
            message: 'Hello from Node.js!',
            position: { latitude: 43.6532, longitude: -79.3832 }
        }
    },
    {
        headers: { 'X-API-Key': apiKey }
    }
);

console.log(`Message sent! Routed to ${messageResponse.data.target_devices} devices`);
```

---

### 🎯 Best Practices

#### 1. **Security**
- Never expose API keys in frontend code
- Use HTTPS in production
- Rotate API keys periodically
- Use strong passwords
- Enable CSRF protection

#### 2. **Performance**
- Use webhooks for real-time delivery
- Poll inbox at reasonable intervals (not too frequent)
- Use appropriate group types for your use case
- Index frequently queried fields

#### 3. **Reliability**
- Configure appropriate retry limits
- Monitor webhook delivery status
- Handle offline devices gracefully
- Use message acknowledgment

#### 4. **Scalability**
- Use Celery for async processing
- Configure Redis for message broker
- Use database connection pooling
- Monitor system resources

---

### 🐛 Troubleshooting

#### Issue: "PostGIS not found"
**Solution**: Install PostGIS extension in PostgreSQL
```bash
sudo -u postgres psql -d iot_message_router -c "CREATE EXTENSION postgis;"
```

#### Issue: "GDAL not found"
**Solution**: Install GDAL library
```bash
sudo apt-get install gdal-bin libgdal-dev python3-gdal
```

#### Issue: "Celery not working"
**Solution**: Check Redis is running
```bash
redis-cli ping
# Should return: PONG
```

#### Issue: "Token expired"
**Solution**: Refresh token or login again
```bash
POST /api/auth/refresh/
{
  "refresh": "<your_refresh_token>"
}
```

---

### 📚 Additional Resources

- **API Documentation**: http://localhost:8000/api/ (Browsable API)
- **Admin Panel**: http://localhost:8000/admin/
- **README.md**: Complete setup guide
- **REQUIREMENTS_VERIFICATION.md**: Feature verification
- **SYSTEM_VERIFICATION.md**: System health check

---

## Summary

### Who Should Use This?
- IoT device manufacturers
- IoT platform providers
- System integrators
- Developers building IoT applications
- Enterprises with IoT device fleets
- Startups in IoT space

### How It Helps?
- ✅ Automatic message routing
- ✅ Geographic-based communication
- ✅ Reliable message delivery
- ✅ Real-time webhook push
- ✅ Secure device authentication
- ✅ Multi-device management
- ✅ Role-based access control

### How to Use?
1. **Setup**: Docker or manual installation
2. **Register**: Create user account
3. **Configure**: Create groups and register devices
4. **Send Messages**: Use API or web interface
5. **Receive Messages**: Poll inbox or use webhooks
6. **Manage**: Use web interface for management

---

**Ready to get started?** Follow the Quick Start Guide above!

**Need help?** Check the troubleshooting section or review the documentation files.

