#!/usr/bin/env python
"""
KCS Messenger Launcher
Starts server and client with proper configuration
"""

import sys
import os
import subprocess
import time
import argparse
from typing import Optional

def check_requirements():
    """Check if basic requirements are met"""
    try:
        import PyQt5
        import socketio
        import aiohttp
        return True
    except ImportError as e:
        print(f"[ERROR] Missing dependency: {e}")
        print("\nPlease install requirements:")
        print("  pip install PyQt5 python-socketio aiohttp aioredis pillow")
        return False

def start_server(detached: bool = False) -> Optional[subprocess.Popen]:
    """Start the server process"""
    print("[INFO] Starting KCS Messenger Server...")
    
    server_script = os.path.join("server", "core", "async_server.py")
    
    if not os.path.exists(server_script):
        # Try creating a minimal server if the full one doesn't exist
        print("[WARNING] Server script not found, creating minimal server...")
        create_minimal_server()
    
    try:
        if detached:
            # Start server in background
            if sys.platform == "win32":
                process = subprocess.Popen(
                    [sys.executable, server_script],
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
            else:
                process = subprocess.Popen(
                    [sys.executable, server_script],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            print("[OK] Server started in background (PID: {})".format(process.pid))
            return process
        else:
            # Start server in same console
            subprocess.run([sys.executable, server_script])
            return None
    except Exception as e:
        print(f"[ERROR] Failed to start server: {e}")
        return None

def create_minimal_server():
    """Create a minimal server for testing"""
    server_dir = os.path.join("server", "core")
    os.makedirs(server_dir, exist_ok=True)
    
    minimal_server = '''"""
Minimal WebSocket server for KCS Messenger
"""

import asyncio
import json
from aiohttp import web
import socketio

sio = socketio.AsyncServer(async_mode='aiohttp', cors_allowed_origins='*')
app = web.Application()
sio.attach(app)

clients = {}

@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")
    return True

@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")
    if sid in clients:
        del clients[sid]

@sio.event
async def authenticate(sid, data):
    user_id = data.get('user_id')
    clients[sid] = user_id
    print(f"User authenticated: {user_id}")
    await sio.emit('authenticated', {'success': True, 'user_id': user_id}, room=sid)

@sio.event
async def join_room(sid, data):
    room_id = data.get('room_id')
    await sio.enter_room(sid, room_id)
    print(f"User joined room: {room_id}")
    
    # Send recent messages (mock data)
    messages = [
        {
            'id': '1',
            'content': 'Welcome to KCS Messenger!',
            'sender_id': 'System',
            'sender_name': 'System',
            'created_at': '2024-01-01T00:00:00Z'
        }
    ]
    await sio.emit('message_history', {'room_id': room_id, 'messages': messages}, room=sid)

@sio.event
async def send_message(sid, data):
    room_id = data.get('room_id')
    content = data.get('content')
    user_id = clients.get(sid, 'Unknown')
    
    message = {
        'id': str(asyncio.get_event_loop().time()),
        'room_id': room_id,
        'sender_id': user_id,
        'sender_name': user_id,
        'content': content,
        'created_at': '2024-01-01T00:00:00Z'
    }
    
    await sio.emit('new_message', message, room=room_id)
    print(f"Message from {user_id}: {content}")

async def index(request):
    return web.json_response({'status': 'running', 'name': 'KCS Messenger Server'})

async def health(request):
    return web.json_response({'status': 'healthy'})

app.router.add_get('/', index)
app.router.add_get('/health', health)

if __name__ == '__main__':
    print("Starting minimal KCS Messenger server on http://localhost:8000")
    web.run_app(app, host='0.0.0.0', port=8000)
'''
    
    server_file = os.path.join(server_dir, "async_server.py")
    with open(server_file, 'w', encoding='utf-8') as f:
        f.write(minimal_server)
    
    print(f"[OK] Created minimal server at {server_file}")

def start_client():
    """Start the client application"""
    print("[INFO] Starting KCS Messenger Client...")
    
    # Try integrated client first
    client_script = os.path.join("client", "desktop", "kakaotalk_integrated.py")
    
    if not os.path.exists(client_script):
        # Fall back to basic UI
        client_script = os.path.join("client", "desktop", "kakaotalk_ui.py")
    
    if not os.path.exists(client_script):
        print("[ERROR] Client script not found!")
        print("Expected location: client/desktop/kakaotalk_integrated.py")
        return
    
    try:
        subprocess.run([sys.executable, client_script])
    except Exception as e:
        print(f"[ERROR] Failed to start client: {e}")

def main():
    """Main launcher"""
    parser = argparse.ArgumentParser(description="KCS Messenger Launcher")
    parser.add_argument(
        '--mode',
        choices=['full', 'server', 'client', 'standalone'],
        default='full',
        help='Launch mode (default: full)'
    )
    parser.add_argument(
        '--no-server',
        action='store_true',
        help='Skip server startup'
    )
    
    args = parser.parse_args()
    
    print("="*60)
    print("KCS Messenger Launcher")
    print("="*60)
    
    # Check requirements
    if not check_requirements():
        return
    
    server_process = None
    
    try:
        if args.mode == 'server':
            # Server only
            start_server(detached=False)
        
        elif args.mode == 'client':
            # Client only
            start_client()
        
        elif args.mode == 'standalone':
            # Standalone mode (no server)
            print("[INFO] Starting in standalone mode...")
            os.environ['STANDALONE_MODE'] = '1'
            start_client()
        
        else:  # full mode
            # Start both server and client
            if not args.no_server:
                server_process = start_server(detached=True)
                
                # Wait for server to start
                print("[INFO] Waiting for server to initialize...")
                time.sleep(3)
            
            # Start client
            start_client()
    
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down...")
    
    finally:
        # Clean up server process if started
        if server_process:
            print("[INFO] Stopping server...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()
    
    print("[INFO] KCS Messenger closed.")

if __name__ == "__main__":
    main()