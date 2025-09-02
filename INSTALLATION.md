# 📦 KCS Messenger Installation Guide

## 🚀 Quick Installation

### Windows
```batch
# 1. Install Python (3.8+)
# Download from https://www.python.org/downloads/

# 2. Install required packages
pip install PyQt5 python-socketio aiohttp aioredis pillow

# 3. Install PostgreSQL and Redis (using Docker)
docker-compose up -d postgres redis

# 4. Run the application
python client/desktop/kakaotalk_integrated.py
```

### macOS/Linux
```bash
# 1. Install Python
sudo apt-get install python3 python3-pip  # Ubuntu/Debian
brew install python3  # macOS

# 2. Install PyQt5 and dependencies
pip3 install PyQt5 python-socketio aiohttp aioredis pillow

# 3. Start services
docker-compose up -d

# 4. Run the application
python3 client/desktop/kakaotalk_integrated.py
```

## 📋 Detailed Installation Steps

### Step 1: System Requirements
- Python 3.8 or higher
- 4GB RAM minimum
- 2GB free disk space
- Windows 10/11, macOS 10.14+, or Linux (Ubuntu 18.04+)

### Step 2: Python Environment Setup

#### Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

#### Install Core Dependencies
```bash
# GUI Framework
pip install PyQt5==5.15.9

# Async Support
pip install qasync==0.23.0
pip install python-socketio==5.7.2
pip install aiohttp==3.8.4

# Database
pip install aioredis==2.0.1
pip install asyncpg==0.27.0

# Media Processing
pip install Pillow==9.5.0

# Utilities
pip install python-dateutil==2.8.2
```

### Step 3: Database Setup

#### Option A: Using Docker (Recommended)
```bash
# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Verify services are running
docker ps
```

#### Option B: Manual Installation
```bash
# PostgreSQL
# Download from https://www.postgresql.org/download/

# Redis
# Download from https://redis.io/download/

# Create database
psql -U postgres
CREATE DATABASE kcs_messenger;
```

### Step 4: Configuration

Create `.env` file in project root:
```env
# Server Configuration
SERVER_HOST=localhost
SERVER_PORT=8000

# Database
DATABASE_URL=postgresql://kcs_user:kcs_pass@localhost:5432/kcs_messenger
REDIS_URL=redis://localhost:6379

# Client Settings
DEFAULT_USERNAME=user
DEFAULT_ROOM=general
```

## 🔧 Troubleshooting

### PyQt5 Installation Issues

#### Windows Error: "Microsoft Visual C++ 14.0 is required"
```bash
# Solution: Install Visual Studio Build Tools
# Download from: https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022

# Or use pre-compiled wheel
pip install PyQt5 --only-binary :all:
```

#### macOS Error: "No module named 'PyQt5'"
```bash
# Solution: Use homebrew
brew install pyqt5
pip install PyQt5
```

#### Linux Error: "Could not find Qt5"
```bash
# Ubuntu/Debian
sudo apt-get install python3-pyqt5

# Fedora
sudo dnf install python3-qt5

# Arch
sudo pacman -S python-pyqt5
```

### Socket Connection Issues

#### Error: "Connection refused"
```bash
# Check if server is running
netstat -an | grep 8000

# Start server manually
python server/core/async_server.py
```

#### Error: "WebSocket connection failed"
```bash
# Check firewall settings
# Windows: Allow port 8000 in Windows Defender
# Linux: sudo ufw allow 8000
```

### Database Connection Issues

#### PostgreSQL Connection Error
```bash
# Check PostgreSQL status
docker-compose ps postgres

# View logs
docker-compose logs postgres

# Restart service
docker-compose restart postgres
```

#### Redis Connection Error
```bash
# Test connection
docker exec -it kcs_redis redis-cli ping

# Check Redis logs
docker-compose logs redis
```

## ✅ Verification

### Test Installation
```bash
# Run test script
python test_installation.py

# Expected output:
# [OK] Python version: 3.x.x
# [OK] PyQt5 installed
# [OK] AsyncIO support available
# [OK] Database connection successful
# [OK] Redis connection successful
# [OK] All dependencies installed
```

### Run Sample Application
```bash
# Start server
python server/core/async_server.py

# In another terminal, start client
python client/desktop/kakaotalk_integrated.py
```

## 📱 Platform-Specific Notes

### Windows
- Run as Administrator for first installation
- Add Python to PATH during installation
- Use PowerShell or Command Prompt, not Git Bash

### macOS
- Install Xcode Command Line Tools: `xcode-select --install`
- Grant accessibility permissions for screen capture
- Use Terminal.app or iTerm2

### Linux
- Install development headers: `sudo apt-get install python3-dev`
- May need to install additional Qt dependencies
- Use system Python or pyenv

## 🆘 Getting Help

If you encounter issues:

1. Check the [Troubleshooting](#troubleshooting) section
2. View application logs in `logs/` directory
3. Run diagnostic script: `python scripts/diagnose.py`
4. Open an issue on GitHub with error details

## 📚 Next Steps

After successful installation:

1. Read [QUICKSTART.md](QUICKSTART.md) for usage guide
2. Review [KAKAOTALK_UI_GUIDE.md](docs/KAKAOTALK_UI_GUIDE.md) for UI documentation
3. Check [SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md) for architecture details

---
**Installation complete! 🎉 Enjoy your KCS Messenger!**