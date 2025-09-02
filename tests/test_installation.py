#!/usr/bin/env python
"""
Installation verification script for KCS Messenger
Checks all required dependencies and configurations
"""

import sys
import os
import importlib
import subprocess
from typing import Tuple, List

def check_python_version() -> Tuple[bool, str]:
    """Check Python version"""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        return True, f"Python {version.major}.{version.minor}.{version.micro}"
    return False, f"Python {version.major}.{version.minor} (3.8+ required)"

def check_package(package_name: str, import_name: str = None) -> Tuple[bool, str]:
    """Check if a package is installed"""
    if import_name is None:
        import_name = package_name
    
    try:
        module = importlib.import_module(import_name)
        version = getattr(module, '__version__', 'unknown')
        return True, f"{package_name} {version}"
    except ImportError:
        return False, f"{package_name} not installed"

def check_service(service_name: str, host: str, port: int) -> Tuple[bool, str]:
    """Check if a service is running"""
    import socket
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            return True, f"{service_name} running on {host}:{port}"
        else:
            return False, f"{service_name} not available on {host}:{port}"
    except Exception as e:
        return False, f"{service_name} check failed: {e}"

def check_docker() -> Tuple[bool, str]:
    """Check if Docker is installed and running"""
    try:
        result = subprocess.run(
            ['docker', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # Check if Docker daemon is running
            result = subprocess.run(
                ['docker', 'ps'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return True, "Docker is installed and running"
            else:
                return False, "Docker installed but daemon not running"
        else:
            return False, "Docker not installed"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False, "Docker not found"

def run_checks():
    """Run all installation checks"""
    print("="*60)
    print("KCS Messenger Installation Verification")
    print("="*60)
    
    checks = [
        ("Python Version", lambda: check_python_version()),
        ("PyQt5", lambda: check_package("PyQt5", "PyQt5.QtCore")),
        ("socketio", lambda: check_package("python-socketio", "socketio")),
        ("aiohttp", lambda: check_package("aiohttp")),
        ("aioredis", lambda: check_package("aioredis")),
        ("Pillow", lambda: check_package("PIL", "PIL")),
        ("Docker", lambda: check_docker()),
    ]
    
    # Run basic checks
    results = []
    all_passed = True
    
    print("\n[Core Dependencies]")
    for name, check_func in checks:
        passed, message = check_func()
        status = "[OK]" if passed else "[FAIL]"
        print(f"{status:6} {name:20} - {message}")
        results.append((name, passed))
        if not passed and name in ["Python Version", "PyQt5"]:
            all_passed = False
    
    # Check services
    print("\n[Services]")
    services = [
        ("PostgreSQL", "localhost", 5432),
        ("Redis", "localhost", 6379),
        ("KCS Server", "localhost", 8000),
    ]
    
    for service_name, host, port in services:
        passed, message = check_service(service_name, host, port)
        status = "[OK]" if passed else "[INFO]"
        print(f"{status:6} {service_name:20} - {message}")
    
    # Check project structure
    print("\n[Project Structure]")
    required_dirs = [
        "server",
        "client",
        "docs",
        "server/core",
        "client/desktop",
    ]
    
    for dir_path in required_dirs:
        exists = os.path.exists(dir_path)
        status = "[OK]" if exists else "[FAIL]"
        print(f"{status:6} Directory: {dir_path}")
        if not exists:
            all_passed = False
    
    # Check critical files
    print("\n[Critical Files]")
    critical_files = [
        "client/desktop/kakaotalk_ui.py",
        "client/desktop/kakaotalk_integrated.py",
        "server/core/async_server.py",
        "requirements.txt",
    ]
    
    for file_path in critical_files:
        exists = os.path.exists(file_path)
        status = "[OK]" if exists else "[FAIL]"
        print(f"{status:6} File: {file_path}")
        if not exists:
            all_passed = False
    
    # Summary
    print("\n" + "="*60)
    if all_passed:
        print("[SUCCESS] All critical components are installed!")
        print("\nYou can now run the application:")
        print("  1. Start server: python server/core/async_server.py")
        print("  2. Start client: python client/desktop/kakaotalk_integrated.py")
    else:
        print("[WARNING] Some components are missing or failed.")
        print("\nTo fix missing dependencies:")
        print("  pip install -r requirements.txt")
        print("\nTo start services:")
        print("  docker-compose up -d")
    
    print("="*60)
    
    return all_passed

def main():
    """Main entry point"""
    try:
        success = run_checks()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[ERROR] Installation check failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()