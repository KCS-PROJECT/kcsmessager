# KCS Messenger - Organized Project Structure

## 📁 Directory Structure

```
kcsmessager/
│
├── 🖥️ client/                      # All client-side applications
│   ├── standalone/                 # Standalone chat (no server needed)
│   │   └── standalone_chat.py     # Main standalone application
│   │
│   ├── realtime/                   # Real-time chat client
│   │   └── chat_client.py         # Network-enabled chat client
│   │
│   ├── launcher/                   # GUI launcher
│   │   └── chat_launcher.py       # Manages server & multiple clients
│   │
│   └── ui/                        # Shared UI components
│       └── (future UI modules)
│
├── 🌐 server/                      # All server-side applications
│   ├── chat/                      # Chat server
│   │   └── chat_server.py        # TCP socket server
│   │
│   └── core/                      # Core server modules
│       └── async_server.py       # Async server implementation
│
├── 🧪 tests/                       # Test suite
│   ├── test_installation.py      # Dependency checker
│   ├── test_all_versions.py      # Version tester
│   └── test_real_chat_fixes.py   # Real chat verification
│
├── 📚 docs/                        # Documentation
│   ├── README.md
│   ├── INSTALLATION.md
│   ├── QUICKSTART.md
│   ├── REAL_CHAT_GUIDE.md
│   └── DEVELOPMENT_ROADMAP.md
│
├── 🔧 scripts/                     # Launch scripts
│   └── (batch files moved here)
│
└── 📦 Root files
    ├── run_organized.bat          # Main launcher (new structure)
    ├── requirements.txt           # Python dependencies
    └── docker-compose.yml         # Docker configuration
```

## 🚀 Quick Start Guide

### 1. Standalone Chat (No Server Required)
```bash
# Direct run
python client/standalone/standalone_chat.py

# Using batch file
run_organized.bat → Option 1
```

### 2. Real-Time Chat System
```bash
# Terminal 1: Start server
python server/chat/chat_server.py

# Terminal 2: Start client
python client/realtime/chat_client.py

# Or use batch file for both
run_organized.bat → Option 2
```

### 3. GUI Launcher (Easiest)
```bash
python client/launcher/chat_launcher.py
# or
run_organized.bat → Option 3
```

## 📋 Component Description

### Client Components

#### `/client/standalone/`
- **standalone_chat.py**: Complete chat UI that works without server
- Features: Message simulation, Korean UI, bubble tails
- Use case: Demo, testing, offline usage

#### `/client/realtime/`
- **chat_client.py**: Network-enabled chat client
- Features: Real-time messaging, multi-user support
- Requires: chat_server.py running

#### `/client/launcher/`
- **chat_launcher.py**: GUI for managing chat system
- Features: Start/stop server, launch multiple clients
- Use case: Easy management of chat system

### Server Components

#### `/server/chat/`
- **chat_server.py**: TCP socket server
- Features: Message routing, user management
- Protocol: JSON over TCP
- Port: 5555 (default)

#### `/server/core/`
- **async_server.py**: Async implementation (future)
- Features: WebSocket support, scalability

## 🔄 Migration from Old Structure

### Old → New Path Mapping
```
simple_chat_server.py      → server/chat/chat_server.py
kakaotalk_real_chat.py    → client/realtime/chat_client.py
kakaotalk_fixed.py        → client/standalone/standalone_chat.py
launch_real_chat.py       → client/launcher/chat_launcher.py
test_*.py                 → tests/*.py
*.md                      → docs/*.md
```

## 💡 Development Guidelines

### Adding New Features

1. **Client features**: Add to appropriate `/client/` subdirectory
2. **Server features**: Add to `/server/chat/` or create new module
3. **Shared UI**: Place in `/client/ui/` for reuse
4. **Tests**: Always add corresponding tests in `/tests/`

### Import Convention
```python
# From client code
from ..ui import shared_component  # Relative import

# From server code
import sys
sys.path.append('..')  # If needed
```

## 🛠️ Technology Stack

- **Language**: Python 3.8+
- **GUI Framework**: PyQt5
- **Networking**: Socket (TCP)
- **Protocol**: JSON
- **Encoding**: UTF-8

## 📝 Important Notes

1. **Always use the organized structure** for new development
2. **Legacy files** in root are kept for backward compatibility
3. **Test files** should be in `/tests/` directory
4. **Documentation** should be in `/docs/` directory
5. **Server and client** are clearly separated

## 🎯 Future Enhancements

- WebSocket support in `/server/websocket/`
- Web client in `/client/web/`
- Mobile client in `/client/mobile/`
- Database integration in `/server/database/`
- API gateway in `/server/api/`