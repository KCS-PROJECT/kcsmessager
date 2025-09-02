# 🚀 KCS Messenger - Quick Start Guide

## 📋 Prerequisites

- Python 3.8 or higher
- Docker & Docker Compose
- Git
- 4GB+ RAM available

## 🛠️ Installation

### 1. Clone Repository
```bash
git clone https://github.com/your-org/kcs-messenger.git
cd kcs-messenger
```

### 2. Setup Python Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Start Infrastructure Services
```bash
# Start all services with Docker Compose
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

### 4. Initialize Database
```bash
# Run database migrations
python -m alembic upgrade head

# Create initial admin user
python scripts/create_admin.py
```

## 🏃 Running the Application

### Start Server (Development Mode)
```bash
# Run async server
python server/core/async_server.py

# Or with auto-reload
uvicorn server.core.async_server:app --reload --port 8000
```

### Start Desktop Client
```bash
# Run PyQt5 desktop client
python client/desktop/main_window.py
```

### Access Web Interface
- API Documentation: http://localhost:8000/docs
- WebSocket Test: http://localhost:8000/ws-test
- MinIO Console: http://localhost:9001 (admin/kcs_minio_2024)
- Grafana Dashboard: http://localhost:3000 (admin/kcs_grafana_2024)

## 🧪 Testing

### Run Unit Tests
```bash
pytest tests/unit -v
```

### Run Integration Tests
```bash
pytest tests/integration -v
```

### Run Load Tests
```bash
# Start test server
python tests/load/test_server.py

# Run load test (1000 concurrent users)
locust -f tests/load/locustfile.py --host=http://localhost:8000
```

## 📊 Architecture Overview

```
┌─────────────────────────────┐
│     Desktop Client (PyQt5)   │
└──────────┬──────────────────┘
           │ WebSocket
           ▼
┌─────────────────────────────┐
│    Async Server (FastAPI)    │
├─────────────────────────────┤
│  - WebSocket Handler         │
│  - REST API                  │
│  - Authentication            │
└──────────┬──────────────────┘
           │
    ┌──────┴──────┬──────────┬────────┐
    ▼             ▼          ▼        ▼
PostgreSQL    Redis    Elasticsearch  MinIO
(Main DB)    (Cache)    (Search)     (Files)
```

## 🔑 Key Features Implemented

### Phase 1 - Core Infrastructure ✅
- [x] Asyncio-based server with WebSocket support
- [x] PostgreSQL database with optimized schema
- [x] Redis caching layer
- [x] Docker Compose setup

### Phase 2 - Messaging Features 🚧
- [x] Real-time message delivery
- [x] Read receipts
- [x] Typing indicators
- [ ] Message reactions
- [ ] Reply/Quote functionality

### Phase 3 - GUI Components ✅
- [x] Modern PyQt5 interface
- [x] KakaoTalk-style message bubbles
- [x] Chat list with unread counters
- [x] User presence indicators

## 🔧 Configuration

### Environment Variables (.env)
```env
# Database
DATABASE_URL=postgresql://kcs_user:kcs_pass_2024@localhost:5432/kcs_messenger

# Redis
REDIS_URL=redis://:kcs_redis_2024@localhost:6379

# Security
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRY_HOURS=24

# File Storage
MAX_FILE_SIZE_MB=100
ALLOWED_FILE_TYPES=image/*,video/*,audio/*,application/pdf

# Performance
MAX_CONCURRENT_USERS=10000
MESSAGE_BATCH_SIZE=50
CACHE_TTL_SECONDS=3600
```

## 📝 Development Workflow

### 1. Create Feature Branch
```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes
- Follow Python PEP 8 style guide
- Add type hints
- Write unit tests
- Update documentation

### 3. Run Quality Checks
```bash
# Format code
black server/ client/

# Lint
flake8 server/ client/

# Type check
mypy server/ client/

# Run tests
pytest -v
```

### 4. Commit Changes
```bash
git add .
git commit -m "feat: add your feature description"
git push origin feature/your-feature-name
```

## 🐛 Troubleshooting

### Common Issues

#### Port Already in Use
```bash
# Find process using port 8000
netstat -ano | findstr :8000

# Kill process
taskkill /PID <process_id> /F
```

#### Database Connection Failed
```bash
# Check PostgreSQL status
docker-compose ps postgres

# View PostgreSQL logs
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres
```

#### Redis Connection Failed
```bash
# Test Redis connection
docker exec -it kcs_redis redis-cli -a kcs_redis_2024 ping
```

#### WebSocket Connection Issues
- Check firewall settings
- Ensure ports 8000 and 8001 are open
- Verify CORS settings in async_server.py

## 📚 Documentation

- [System Design](docs/SYSTEM_DESIGN.md)
- [API Documentation](http://localhost:8000/docs)
- [Database Schema](docs/schema.sql)
- [WebSocket Events](docs/websocket_events.md)

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 License

MIT License - see LICENSE file for details

## 🆘 Support

- GitHub Issues: https://github.com/your-org/kcs-messenger/issues
- Email: support@kcs-messenger.com
- Discord: https://discord.gg/kcs-messenger

---

**Happy Messaging! 🚀**