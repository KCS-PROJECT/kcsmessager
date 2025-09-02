"""
KCS Messenger - Async Server Core
High-performance asyncio-based messaging server
"""

import asyncio
import json
import logging
import signal
import sys
import uuid
from datetime import datetime
from typing import Dict, Set, Optional
from dataclasses import dataclass, asdict

import aioredis
from aiohttp import web
import socketio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class User:
    """User model"""
    id: str
    username: str
    status: str = 'online'
    last_seen: Optional[datetime] = None
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'status': self.status,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None
        }


@dataclass
class Message:
    """Message model"""
    id: str
    room_id: str
    sender_id: str
    content: str
    type: str = 'text'
    created_at: datetime = None
    reply_to: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def to_dict(self):
        return {
            'id': self.id,
            'room_id': self.room_id,
            'sender_id': self.sender_id,
            'content': self.content,
            'type': self.type,
            'created_at': self.created_at.isoformat(),
            'reply_to': self.reply_to
        }


class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[str]] = {}  # room_id -> set of session_ids
        self.user_sessions: Dict[str, str] = {}  # session_id -> user_id
        self.user_rooms: Dict[str, Set[str]] = {}  # user_id -> set of room_ids
        
    async def connect(self, session_id: str, user_id: str):
        """Register new connection"""
        self.user_sessions[session_id] = user_id
        if user_id not in self.user_rooms:
            self.user_rooms[user_id] = set()
        logger.info(f"User {user_id} connected with session {session_id}")
        
    async def disconnect(self, session_id: str):
        """Remove connection"""
        user_id = self.user_sessions.get(session_id)
        if user_id:
            # Remove from all rooms
            for room_id in self.user_rooms.get(user_id, set()).copy():
                await self.leave_room(session_id, room_id)
            
            # Clean up session
            del self.user_sessions[session_id]
            if user_id in self.user_rooms:
                del self.user_rooms[user_id]
            
            logger.info(f"User {user_id} disconnected")
    
    async def join_room(self, session_id: str, room_id: str):
        """Join user to room"""
        if room_id not in self.active_connections:
            self.active_connections[room_id] = set()
        
        self.active_connections[room_id].add(session_id)
        
        user_id = self.user_sessions.get(session_id)
        if user_id:
            self.user_rooms[user_id].add(room_id)
            logger.info(f"User {user_id} joined room {room_id}")
    
    async def leave_room(self, session_id: str, room_id: str):
        """Remove user from room"""
        if room_id in self.active_connections:
            self.active_connections[room_id].discard(session_id)
            
            # Clean up empty rooms
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]
        
        user_id = self.user_sessions.get(session_id)
        if user_id and user_id in self.user_rooms:
            self.user_rooms[user_id].discard(room_id)
            logger.info(f"User {user_id} left room {room_id}")
    
    def get_room_sessions(self, room_id: str) -> Set[str]:
        """Get all sessions in a room"""
        return self.active_connections.get(room_id, set())
    
    def get_user_rooms(self, user_id: str) -> Set[str]:
        """Get all rooms for a user"""
        return self.user_rooms.get(user_id, set())


class MessageQueue:
    """Manages message queue with Redis"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.message_buffer = {}  # room_id -> list of messages
        
    async def add_message(self, message: Message):
        """Add message to queue"""
        # Store in Redis
        key = f"messages:{message.room_id}"
        await self.redis.lpush(key, json.dumps(message.to_dict()))
        await self.redis.ltrim(key, 0, 999)  # Keep last 1000 messages
        
        # Store in memory buffer
        if message.room_id not in self.message_buffer:
            self.message_buffer[message.room_id] = []
        
        self.message_buffer[message.room_id].append(message)
        
        # Trim buffer
        if len(self.message_buffer[message.room_id]) > 100:
            self.message_buffer[message.room_id] = self.message_buffer[message.room_id][-100:]
    
    async def get_messages(self, room_id: str, limit: int = 50) -> list:
        """Get recent messages from room"""
        # Try memory buffer first
        if room_id in self.message_buffer:
            return self.message_buffer[room_id][-limit:]
        
        # Fallback to Redis
        key = f"messages:{room_id}"
        messages = await self.redis.lrange(key, 0, limit - 1)
        return [json.loads(msg) for msg in messages]


class PresenceManager:
    """Manages user presence and status"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.user_status = {}  # user_id -> status
        
    async def update_presence(self, user_id: str, status: str):
        """Update user presence"""
        self.user_status[user_id] = status
        
        # Store in Redis
        key = f"presence:{user_id}"
        await self.redis.hset(key, mapping={
            'status': status,
            'last_seen': datetime.utcnow().isoformat()
        })
        await self.redis.expire(key, 300)  # 5 minutes TTL
        
        logger.info(f"Updated presence for {user_id}: {status}")
    
    async def get_presence(self, user_id: str) -> dict:
        """Get user presence"""
        # Try memory first
        if user_id in self.user_status:
            return {'status': self.user_status[user_id]}
        
        # Fallback to Redis
        key = f"presence:{user_id}"
        data = await self.redis.hgetall(key)
        return data if data else {'status': 'offline'}
    
    async def set_typing(self, user_id: str, room_id: str):
        """Set typing indicator"""
        key = f"typing:{room_id}"
        await self.redis.hset(key, user_id, datetime.utcnow().isoformat())
        await self.redis.expire(key, 3)  # 3 seconds TTL
    
    async def get_typing_users(self, room_id: str) -> list:
        """Get users currently typing in room"""
        key = f"typing:{room_id}"
        typing_data = await self.redis.hgetall(key)
        return list(typing_data.keys())


class KCSMessengerServer:
    """Main server class"""
    
    def __init__(self, redis_url: str = 'redis://localhost:6379'):
        # Initialize Socket.IO server
        self.sio = socketio.AsyncServer(
            async_mode='aiohttp',
            cors_allowed_origins='*',
            ping_timeout=60,
            ping_interval=25
        )
        
        # Initialize aiohttp app
        self.app = web.Application()
        self.sio.attach(self.app)
        
        # Initialize managers
        self.connection_mgr = ConnectionManager()
        self.redis_url = redis_url
        self.redis_client = None
        self.message_queue = None
        self.presence_mgr = None
        
        # Setup routes
        self.setup_routes()
        
        # Setup Socket.IO event handlers
        self.setup_socketio_handlers()
        
    def setup_routes(self):
        """Setup HTTP routes"""
        self.app.router.add_get('/', self.index)
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_get('/metrics', self.metrics)
        
    async def index(self, request):
        """Root endpoint"""
        return web.json_response({
            'name': 'KCS Messenger Server',
            'version': '2.0',
            'status': 'running'
        })
    
    async def health_check(self, request):
        """Health check endpoint"""
        return web.json_response({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat()
        })
    
    async def metrics(self, request):
        """Metrics endpoint"""
        return web.json_response({
            'active_connections': len(self.connection_mgr.user_sessions),
            'active_rooms': len(self.connection_mgr.active_connections),
            'timestamp': datetime.utcnow().isoformat()
        })
    
    def setup_socketio_handlers(self):
        """Setup Socket.IO event handlers"""
        
        @self.sio.event
        async def connect(sid, environ):
            """Handle new connection"""
            logger.info(f"New connection: {sid}")
            return True
        
        @self.sio.event
        async def disconnect(sid):
            """Handle disconnection"""
            await self.connection_mgr.disconnect(sid)
            logger.info(f"Disconnected: {sid}")
        
        @self.sio.event
        async def authenticate(sid, data):
            """Handle authentication"""
            user_id = data.get('user_id')
            token = data.get('token')
            
            # TODO: Validate JWT token
            
            if user_id:
                await self.connection_mgr.connect(sid, user_id)
                await self.presence_mgr.update_presence(user_id, 'online')
                
                # Send success response
                await self.sio.emit('authenticated', {
                    'success': True,
                    'user_id': user_id
                }, room=sid)
                
                logger.info(f"Authenticated: {user_id}")
                return {'success': True}
            
            return {'success': False, 'error': 'Invalid credentials'}
        
        @self.sio.event
        async def join_room(sid, data):
            """Handle room join"""
            room_id = data.get('room_id')
            
            if room_id:
                await self.connection_mgr.join_room(sid, room_id)
                await self.sio.enter_room(sid, room_id)
                
                # Notify room members
                user_id = self.connection_mgr.user_sessions.get(sid)
                await self.sio.emit('user_joined', {
                    'room_id': room_id,
                    'user_id': user_id
                }, room=room_id, skip_sid=sid)
                
                # Send recent messages
                messages = await self.message_queue.get_messages(room_id)
                await self.sio.emit('message_history', {
                    'room_id': room_id,
                    'messages': messages
                }, room=sid)
                
                return {'success': True}
            
            return {'success': False, 'error': 'Invalid room'}
        
        @self.sio.event
        async def leave_room(sid, data):
            """Handle room leave"""
            room_id = data.get('room_id')
            
            if room_id:
                await self.connection_mgr.leave_room(sid, room_id)
                await self.sio.leave_room(sid, room_id)
                
                # Notify room members
                user_id = self.connection_mgr.user_sessions.get(sid)
                await self.sio.emit('user_left', {
                    'room_id': room_id,
                    'user_id': user_id
                }, room=room_id)
                
                return {'success': True}
            
            return {'success': False, 'error': 'Invalid room'}
        
        @self.sio.event
        async def send_message(sid, data):
            """Handle message send"""
            room_id = data.get('room_id')
            content = data.get('content')
            msg_type = data.get('type', 'text')
            reply_to = data.get('reply_to')
            
            user_id = self.connection_mgr.user_sessions.get(sid)
            
            if user_id and room_id and content:
                # Create message
                message = Message(
                    id=str(uuid.uuid4()),
                    room_id=room_id,
                    sender_id=user_id,
                    content=content,
                    type=msg_type,
                    reply_to=reply_to
                )
                
                # Store message
                await self.message_queue.add_message(message)
                
                # Broadcast to room
                await self.sio.emit('new_message', message.to_dict(), room=room_id)
                
                logger.info(f"Message sent: {user_id} -> {room_id}")
                return {'success': True, 'message_id': message.id}
            
            return {'success': False, 'error': 'Invalid message data'}
        
        @self.sio.event
        async def typing_start(sid, data):
            """Handle typing start"""
            room_id = data.get('room_id')
            user_id = self.connection_mgr.user_sessions.get(sid)
            
            if user_id and room_id:
                await self.presence_mgr.set_typing(user_id, room_id)
                
                # Notify room members
                typing_users = await self.presence_mgr.get_typing_users(room_id)
                await self.sio.emit('typing_update', {
                    'room_id': room_id,
                    'users': typing_users
                }, room=room_id, skip_sid=sid)
                
                return {'success': True}
            
            return {'success': False}
        
        @self.sio.event
        async def mark_read(sid, data):
            """Handle read receipt"""
            message_id = data.get('message_id')
            user_id = self.connection_mgr.user_sessions.get(sid)
            
            if user_id and message_id:
                # Store read receipt in Redis
                key = f"read:{message_id}"
                await self.redis_client.sadd(key, user_id)
                
                # Get read count
                read_count = await self.redis_client.scard(key)
                
                # Notify sender
                # TODO: Get message sender and notify
                
                return {'success': True, 'read_count': read_count}
            
            return {'success': False}
        
        @self.sio.event
        async def update_presence(sid, data):
            """Handle presence update"""
            status = data.get('status')
            user_id = self.connection_mgr.user_sessions.get(sid)
            
            if user_id and status:
                await self.presence_mgr.update_presence(user_id, status)
                
                # Broadcast to all user's rooms
                user_rooms = self.connection_mgr.get_user_rooms(user_id)
                for room_id in user_rooms:
                    await self.sio.emit('presence_update', {
                        'user_id': user_id,
                        'status': status
                    }, room=room_id)
                
                return {'success': True}
            
            return {'success': False}
    
    async def startup(self):
        """Server startup"""
        # Connect to Redis
        self.redis_client = await aioredis.create_redis_pool(self.redis_url)
        self.message_queue = MessageQueue(self.redis_client)
        self.presence_mgr = PresenceManager(self.redis_client)
        
        logger.info("Connected to Redis")
        logger.info("KCS Messenger Server started")
    
    async def cleanup(self):
        """Server cleanup"""
        if self.redis_client:
            self.redis_client.close()
            await self.redis_client.wait_closed()
        
        logger.info("Server shutdown complete")
    
    def run(self, host: str = '0.0.0.0', port: int = 8000):
        """Run the server"""
        # Setup signal handlers
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, lambda s, f: asyncio.create_task(self.cleanup()))
        
        # Run startup
        self.app.on_startup.append(lambda app: self.startup())
        self.app.on_cleanup.append(lambda app: self.cleanup())
        
        # Start server
        logger.info(f"Starting server on {host}:{port}")
        web.run_app(self.app, host=host, port=port)


if __name__ == '__main__':
    server = KCSMessengerServer()
    server.run()