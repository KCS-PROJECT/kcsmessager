#!/usr/bin/env python
"""
Simple Chat Server for Real-Time Communication
Handles multiple client connections and broadcasts messages
"""

import socket
import threading
import json
from datetime import datetime

class ChatServer:
    """Simple chat server for handling multiple clients"""
    
    def __init__(self, host='127.0.0.1', port=5555):
        self.host = host
        self.port = port
        self.clients = {}  # {client_socket: {"username": name, "address": addr}}
        self.server_socket = None
        self.running = False
        
    def start(self):
        """Start the chat server"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            
            print(f"[SERVER] Chat server started on {self.host}:{self.port}")
            print("[SERVER] Waiting for connections...")
            
            # Accept connections in main thread
            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    print(f"[SERVER] New connection from {address}")
                    
                    # Handle each client in a separate thread
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, address)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    
                except socket.error:
                    if self.running:
                        print("[SERVER] Socket error occurred")
                    break
                    
        except Exception as e:
            print(f"[SERVER] Error starting server: {e}")
        finally:
            self.stop()
    
    def handle_client(self, client_socket, address):
        """Handle individual client connection"""
        try:
            # Wait for username
            data = client_socket.recv(1024).decode('utf-8')
            if data:
                message = json.loads(data)
                if message['type'] == 'join':
                    username = message['username']
                    
                    # Store client info
                    self.clients[client_socket] = {
                        'username': username,
                        'address': address
                    }
                    
                    print(f"[SERVER] {username} joined the chat")
                    
                    # Notify all clients about new user
                    join_msg = {
                        'type': 'user_joined',
                        'username': username,
                        'timestamp': datetime.now().isoformat()
                    }
                    self.broadcast_message(json.dumps(join_msg), client_socket)
                    
                    # Send current users list to new client
                    users_list = {
                        'type': 'users_list',
                        'users': [client['username'] for client in self.clients.values()]
                    }
                    client_socket.send(json.dumps(users_list).encode('utf-8'))
            
            # Handle messages
            while self.running:
                try:
                    data = client_socket.recv(1024).decode('utf-8')
                    if not data:
                        break
                    
                    message = json.loads(data)
                    
                    if message['type'] == 'message':
                        # Add server timestamp
                        message['timestamp'] = datetime.now().isoformat()
                        message['sender'] = self.clients[client_socket]['username']
                        
                        print(f"[SERVER] {message['sender']}: {message['content']}")
                        
                        # Broadcast to all clients (including sender for consistency)
                        self.broadcast_message(json.dumps(message), exclude_socket=None)
                        
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"[SERVER] Error handling message: {e}")
                    break
                    
        except Exception as e:
            print(f"[SERVER] Error with client {address}: {e}")
        finally:
            self.remove_client(client_socket)
    
    def broadcast_message(self, message, exclude_socket=None):
        """Broadcast message to all connected clients"""
        disconnected_clients = []
        
        for client_socket in self.clients:
            if exclude_socket is None or client_socket != exclude_socket:
                try:
                    client_socket.send(message.encode('utf-8'))
                except:
                    disconnected_clients.append(client_socket)
        
        # Remove disconnected clients
        for client_socket in disconnected_clients:
            self.remove_client(client_socket)
    
    def remove_client(self, client_socket):
        """Remove a client from the server"""
        if client_socket in self.clients:
            username = self.clients[client_socket]['username']
            del self.clients[client_socket]
            
            # Notify others about user leaving
            leave_msg = {
                'type': 'user_left',
                'username': username,
                'timestamp': datetime.now().isoformat()
            }
            self.broadcast_message(json.dumps(leave_msg))
            
            print(f"[SERVER] {username} left the chat")
            
            try:
                client_socket.close()
            except:
                pass
    
    def stop(self):
        """Stop the server"""
        self.running = False
        
        # Close all client connections
        for client_socket in list(self.clients.keys()):
            self.remove_client(client_socket)
        
        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        print("[SERVER] Server stopped")


def main():
    """Run the chat server"""
    server = ChatServer()
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n[SERVER] Shutting down...")
        server.stop()


if __name__ == '__main__':
    main()