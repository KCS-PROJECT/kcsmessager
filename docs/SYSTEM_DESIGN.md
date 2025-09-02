# 🏗️ KCS Messenger System Design Document

## 📋 Executive Summary

### Project Overview
- **Name**: KCS Enterprise Messenger
- **Version**: 2.0
- **Tech Stack**: Python 3.8+, asyncio, PyQt5, PostgreSQL, Redis, WebSocket
- **Target**: 10,000+ concurrent users
- **Architecture**: Event-driven microservices-ready monolith

## 🎯 Design Goals

### Functional Requirements
- Real-time messaging with <100ms latency
- File sharing up to 100MB
- Voice/Video calls (P2P)
- Group chats up to 500 members
- Message history and search
- End-to-end encryption (optional)

### Non-Functional Requirements
- **Performance**: 10,000 concurrent connections
- **Availability**: 99.9% uptime
- **Scalability**: Horizontal scaling ready
- **Security**: TLS 1.3, JWT authentication
- **Compatibility**: Windows, macOS, Linux

## 🏛️ System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Client Layer                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │Desktop   │  │  Web     │  │ Mobile   │  │   CLI    │   │
│  │(PyQt5)   │  │(React)   │  │(Flutter) │  │(Python)  │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       └──────────────┴──────────────┴──────────────┘        │
└───────────────────────────┬─────────────────────────────────┘
                            │
                ┌───────────▼────────────┐
                │    Load Balancer       │
                │    (Nginx/HAProxy)     │
                └───────────┬────────────┘
                            │
┌───────────────────────────┴─────────────────────────────────┐
│                      Application Layer                       │
│  ┌────────────────────────────────────────────────────┐     │
│  │              API Gateway (FastAPI)                  │     │
│  └──────┬──────────┬──────────┬──────────┬───────────┘     │
│         │          │          │          │                  │
│    ┌────▼────┐┌───▼────┐┌───▼────┐┌────▼────┐            │
│    │Auth     ││Chat    ││Media   ││Presence │            │
│    │Service  ││Service ││Service ││Service  │            │
│    └────┬────┘└───┬────┘└───┬────┘└────┬────┘            │
│         └──────────┴──────────┴──────────┘                 │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                      Data Layer                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │PostgreSQL│  │  Redis   │  │   S3     │  │Elastic   │   │
│  │(Primary) │  │ (Cache)  │  │ (Files)  │  │(Search)  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└──────────────────────────────────────────────────────────────┘
```

### Component Architecture

```python
# Core Services Structure
kcs_messenger/
├── server/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── app.py              # FastAPI application
│   │   ├── config.py           # Configuration management
│   │   └── exceptions.py       # Custom exceptions
│   │
│   ├── services/
│   │   ├── auth/
│   │   │   ├── authentication.py
│   │   │   ├── authorization.py
│   │   │   └── jwt_handler.py
│   │   │
│   │   ├── chat/
│   │   │   ├── message_handler.py
│   │   │   ├── room_manager.py
│   │   │   └── websocket_manager.py
│   │   │
│   │   ├── media/
│   │   │   ├── file_handler.py
│   │   │   ├── image_processor.py
│   │   │   └── video_streamer.py
│   │   │
│   │   └── presence/
│   │       ├── status_manager.py
│   │       └── activity_tracker.py
│   │
│   ├── models/
│   │   ├── user.py
│   │   ├── message.py
│   │   ├── room.py
│   │   └── file.py
│   │
│   ├── api/
│   │   ├── v1/
│   │   │   ├── auth_routes.py
│   │   │   ├── chat_routes.py
│   │   │   ├── media_routes.py
│   │   │   └── user_routes.py
│   │   └── websocket/
│   │       ├── connection_manager.py
│   │       └── event_handlers.py
│   │
│   └── infrastructure/
│       ├── database/
│       │   ├── connection.py
│       │   ├── migrations/
│       │   └── repositories/
│       ├── cache/
│       │   └── redis_client.py
│       └── storage/
│           └── s3_client.py
│
├── client/
│   ├── desktop/         # PyQt5 Desktop Client
│   ├── web/            # React Web Client
│   └── cli/            # Command Line Interface
│
└── shared/
    ├── protocols/      # Communication protocols
    ├── utils/         # Shared utilities
    └── constants/     # Shared constants
```

## 💾 Database Design

### Entity Relationship Diagram

```sql
-- Core Tables Structure

-- Users Table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    avatar_url VARCHAR(500),
    status VARCHAR(20) DEFAULT 'offline',
    status_message VARCHAR(200),
    last_seen TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Rooms Table (Channels/Groups)
CREATE TABLE rooms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    type VARCHAR(20) NOT NULL, -- 'direct', 'group', 'channel'
    description TEXT,
    avatar_url VARCHAR(500),
    created_by UUID REFERENCES users(id),
    is_encrypted BOOLEAN DEFAULT false,
    max_members INTEGER DEFAULT 500,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Messages Table (Partitioned by month)
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    room_id UUID REFERENCES rooms(id) ON DELETE CASCADE,
    sender_id UUID REFERENCES users(id),
    content TEXT,
    type VARCHAR(20) DEFAULT 'text', -- 'text', 'image', 'file', 'system'
    reply_to UUID REFERENCES messages(id),
    is_edited BOOLEAN DEFAULT false,
    is_deleted BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) PARTITION BY RANGE (created_at);

-- Read Receipts Table
CREATE TABLE read_receipts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID REFERENCES messages(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    read_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(message_id, user_id)
);

-- Room Members Table
CREATE TABLE room_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    room_id UUID REFERENCES rooms(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(20) DEFAULT 'member', -- 'owner', 'admin', 'member'
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_read_message_id UUID REFERENCES messages(id),
    notifications_enabled BOOLEAN DEFAULT true,
    UNIQUE(room_id, user_id)
);

-- Files Table
CREATE TABLE files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID REFERENCES messages(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    file_size BIGINT,
    mime_type VARCHAR(100),
    storage_path VARCHAR(500),
    thumbnail_path VARCHAR(500),
    checksum VARCHAR(64),
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Reactions Table
CREATE TABLE reactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID REFERENCES messages(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    emoji VARCHAR(10) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(message_id, user_id, emoji)
);

-- Indexes for Performance
CREATE INDEX idx_messages_room_created ON messages(room_id, created_at DESC);
CREATE INDEX idx_messages_sender ON messages(sender_id);
CREATE INDEX idx_read_receipts_user ON read_receipts(user_id);
CREATE INDEX idx_room_members_user ON room_members(user_id);
CREATE INDEX idx_files_message ON files(message_id);
```

### Redis Cache Schema

```python
# Redis Key Patterns

# User Sessions
"session:{user_id}" -> {
    "token": "jwt_token",
    "device_id": "device_uuid",
    "last_activity": timestamp
}

# User Presence
"presence:{user_id}" -> {
    "status": "online|away|busy|offline",
    "last_seen": timestamp,
    "active_room": "room_id"
}

# Room Active Users
"room:{room_id}:users" -> Set of user_ids

# Typing Indicators
"typing:{room_id}" -> {
    "user_id": timestamp,  # Expires after 3 seconds
}

# Unread Counts
"unread:{user_id}:{room_id}" -> count

# Message Cache (Recent 100 messages per room)
"messages:{room_id}" -> List of message objects
```

## 🔌 API Design

### WebSocket Events

```python
# Client -> Server Events
{
    "event": "message.send",
    "data": {
        "room_id": "uuid",
        "content": "Hello World",
        "type": "text",
        "reply_to": "message_uuid"  # optional
    }
}

{
    "event": "typing.start",
    "data": {
        "room_id": "uuid"
    }
}

{
    "event": "message.read",
    "data": {
        "message_id": "uuid"
    }
}

{
    "event": "reaction.add",
    "data": {
        "message_id": "uuid",
        "emoji": "👍"
    }
}

# Server -> Client Events
{
    "event": "message.new",
    "data": {
        "id": "uuid",
        "room_id": "uuid",
        "sender": {...},
        "content": "Hello World",
        "created_at": "2024-01-01T00:00:00Z"
    }
}

{
    "event": "typing.update",
    "data": {
        "room_id": "uuid",
        "users": ["user1", "user2"]
    }
}

{
    "event": "presence.update",
    "data": {
        "user_id": "uuid",
        "status": "online",
        "last_seen": "2024-01-01T00:00:00Z"
    }
}
```

### REST API Endpoints

```yaml
# Authentication
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh
POST   /api/v1/auth/logout

# Users
GET    /api/v1/users/me
PUT    /api/v1/users/me
GET    /api/v1/users/{user_id}
GET    /api/v1/users/search?q=keyword

# Rooms
GET    /api/v1/rooms
POST   /api/v1/rooms
GET    /api/v1/rooms/{room_id}
PUT    /api/v1/rooms/{room_id}
DELETE /api/v1/rooms/{room_id}
POST   /api/v1/rooms/{room_id}/join
POST   /api/v1/rooms/{room_id}/leave

# Messages
GET    /api/v1/rooms/{room_id}/messages?limit=50&before=uuid
POST   /api/v1/messages/{message_id}/edit
DELETE /api/v1/messages/{message_id}

# Files
POST   /api/v1/files/upload
GET    /api/v1/files/{file_id}
GET    /api/v1/files/{file_id}/download

# Search
GET    /api/v1/search/messages?q=keyword&room_id=uuid
GET    /api/v1/search/files?type=image&room_id=uuid
```

## 🎨 GUI Component Design

### Desktop Client Architecture (PyQt5)

```python
# Main Window Structure
class MainWindow(QMainWindow):
    def __init__(self):
        # Layout Structure
        """
        ┌─────────────────────────────────────┐
        │  MenuBar (File, Edit, View, Help)   │
        ├──────────┬──────────────────────────┤
        │          │                          │
        │  Sidebar │    Chat Area             │
        │          │                          │
        │  - Chats │  ┌──────────────────┐   │
        │  - Users │  │  Messages List   │   │
        │  - Files │  │                  │   │
        │          │  └──────────────────┘   │
        │          │  ┌──────────────────┐   │
        │          │  │  Input Area      │   │
        │          │  └──────────────────┘   │
        └──────────┴──────────────────────────┘
        """
```

### Component Hierarchy

```python
MainWindow
├── MenuBar
│   ├── FileMenu
│   ├── EditMenu
│   ├── ViewMenu
│   └── HelpMenu
│
├── Sidebar (QDockWidget)
│   ├── UserProfile
│   ├── SearchBar
│   └── NavigationTabs
│       ├── ChatsTab
│       │   └── ChatList
│       │       └── ChatItem
│       ├── UsersTab
│       │   └── UserList
│       │       └── UserItem
│       └── FilesTab
│           └── FileList
│               └── FileItem
│
└── CentralWidget
    ├── ChatHeader
    │   ├── RoomInfo
    │   ├── SearchButton
    │   └── CallButtons
    │
    ├── MessageArea
    │   ├── MessageList (QListWidget with custom delegate)
    │   │   └── MessageBubble
    │   │       ├── Avatar
    │   │       ├── Content
    │   │       ├── Timestamp
    │   │       ├── ReadReceipt
    │   │       └── ReactionBar
    │   └── ScrollControls
    │
    └── InputArea
        ├── AttachButton
        ├── MessageInput (QTextEdit)
        ├── EmojiButton
        └── SendButton
```

## 🔒 Security Architecture

### Authentication Flow

```
┌──────────┐     1. Login Request      ┌──────────┐
│  Client  │ ────────────────────────> │   Auth   │
│          │                            │  Service │
│          │ <──────────────────────── │          │
└──────────┘     2. JWT Token          └──────────┘
     │                                       │
     │ 3. WebSocket Connect                 │
     │    with JWT                          │
     ▼                                       ▼
┌──────────┐     4. Validate Token     ┌──────────┐
│WebSocket │ ────────────────────────> │  Redis   │
│ Gateway  │ <──────────────────────── │  Cache   │
└──────────┘     5. User Session       └──────────┘
```

### Security Measures

```python
# Security Configuration
SECURITY_CONFIG = {
    # Encryption
    "tls_version": "1.3",
    "cipher_suites": ["TLS_AES_256_GCM_SHA384"],
    
    # Authentication
    "jwt_algorithm": "RS256",
    "jwt_expiry": 3600,  # 1 hour
    "refresh_token_expiry": 604800,  # 7 days
    
    # Rate Limiting
    "rate_limits": {
        "login": "5/minute",
        "message": "30/minute",
        "file_upload": "10/hour"
    },
    
    # Password Policy
    "password_min_length": 8,
    "password_require_special": True,
    "password_require_number": True,
    
    # Session Management
    "max_sessions_per_user": 5,
    "session_timeout": 1800,  # 30 minutes
    
    # File Security
    "max_file_size": 104857600,  # 100MB
    "allowed_file_types": ["image/*", "video/*", "audio/*", "application/pdf"],
    "virus_scan_enabled": True
}
```

## 🚀 Deployment Architecture

### Container Architecture

```yaml
# docker-compose.yml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - app

  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/kcs_messenger
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:14
    environment:
      - POSTGRES_DB=kcs_messenger
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

  elasticsearch:
    image: elasticsearch:8.5.0
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    volumes:
      - elastic_data:/usr/share/elasticsearch/data

volumes:
  postgres_data:
  redis_data:
  elastic_data:
```

### Kubernetes Architecture (Future)

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kcs-messenger
spec:
  replicas: 3
  selector:
    matchLabels:
      app: kcs-messenger
  template:
    metadata:
      labels:
        app: kcs-messenger
    spec:
      containers:
      - name: app
        image: kcs-messenger:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

## 📊 Performance Targets

### Scalability Metrics

```python
PERFORMANCE_TARGETS = {
    # Concurrent Users
    "max_concurrent_users": 10000,
    "max_users_per_room": 500,
    
    # Message Performance
    "message_latency_p50": 50,   # ms
    "message_latency_p99": 100,  # ms
    "messages_per_second": 10000,
    
    # File Transfer
    "max_file_size": 100 * 1024 * 1024,  # 100MB
    "file_upload_speed": 10 * 1024 * 1024,  # 10MB/s
    
    # Database Performance
    "db_connection_pool": 100,
    "db_query_timeout": 1000,  # ms
    
    # Cache Performance
    "cache_hit_ratio": 0.9,  # 90%
    "cache_ttl": 3600,  # 1 hour
    
    # System Resources
    "max_memory_usage": 4096,  # MB
    "max_cpu_usage": 80,  # percent
}
```

## 🔄 Migration Strategy

### Phase 1: Core Migration (Weeks 1-2)
```python
# Current: Threading + Socket
# Target: Asyncio + WebSocket

1. Create parallel asyncio server
2. Implement WebSocket handler
3. Migrate authentication system
4. Test with 100 concurrent users
```

### Phase 2: Database Migration (Weeks 3-4)
```python
# Current: SQLite
# Target: PostgreSQL + Redis

1. Design PostgreSQL schema
2. Create migration scripts
3. Implement dual-write pattern
4. Gradual cutover with fallback
```

### Phase 3: GUI Enhancement (Weeks 5-8)
```python
# Current: Tkinter
# Target: PyQt5

1. Create PyQt5 prototype
2. Implement component library
3. Parallel development approach
4. User acceptance testing
```

## ✅ Design Validation Checklist

### Architecture Validation
- [ ] Supports 10,000 concurrent users
- [ ] Message latency <100ms
- [ ] Horizontal scaling capability
- [ ] Microservices migration path
- [ ] Database sharding ready

### Security Validation
- [ ] End-to-end encryption design
- [ ] Authentication/Authorization complete
- [ ] Rate limiting implemented
- [ ] Input validation comprehensive
- [ ] OWASP compliance checked

### Performance Validation
- [ ] Load testing scenarios defined
- [ ] Caching strategy optimized
- [ ] Database indexes optimized
- [ ] Network protocol efficient
- [ ] Resource limits defined

### Usability Validation
- [ ] UI/UX mockups approved
- [ ] Accessibility standards met
- [ ] Cross-platform compatibility
- [ ] Offline mode considered
- [ ] Mobile responsiveness planned

## 📚 References

- [System Design Primer](https://github.com/donnemartin/system-design-primer)
- [Python Asyncio Documentation](https://docs.python.org/3/library/asyncio.html)
- [PyQt5 Documentation](https://doc.qt.io/qtforpython/)
- [PostgreSQL Best Practices](https://wiki.postgresql.org/wiki/Main_Page)
- [Redis Design Patterns](https://redis.io/docs/manual/patterns/)

---
*Document Version: 1.0*
*Last Updated: 2024*
*Author: KCS Messenger Architecture Team*