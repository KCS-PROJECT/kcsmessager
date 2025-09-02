#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Verify the organized project structure
"""

import os
import sys

def check_file(path, description):
    """Check if a file exists"""
    exists = os.path.exists(path)
    status = "OK" if exists else "MISSING"
    
    print(f"[{status:^7}] {description:<50} {path}")
    
    return exists

def main():
    print("=" * 70)
    print("KCS Messenger - Structure Verification")
    print("=" * 70)
    print()
    
    # Track results
    total = 0
    found = 0
    
    # Server files
    print("SERVER FILES:")
    print("-" * 40)
    server_files = [
        ("server/chat/chat_server.py", "Chat Server"),
        ("server/core/async_server.py", "Async Server"),
    ]
    for path, desc in server_files:
        total += 1
        if check_file(path, desc):
            found += 1
    
    print()
    
    # Client files
    print("CLIENT FILES:")
    print("-" * 40)
    client_files = [
        ("client/standalone/standalone_chat.py", "Standalone Chat"),
        ("client/realtime/chat_client.py", "Real-time Chat Client"),
        ("client/launcher/chat_launcher.py", "GUI Launcher"),
    ]
    for path, desc in client_files:
        total += 1
        if check_file(path, desc):
            found += 1
    
    print()
    
    # Test files
    print("TEST FILES:")
    print("-" * 40)
    test_files = [
        ("tests/test_installation.py", "Installation Test"),
        ("tests/test_all_versions.py", "Version Test"),
        ("tests/test_real_chat_fixes.py", "Real Chat Test"),
    ]
    for path, desc in test_files:
        total += 1
        if check_file(path, desc):
            found += 1
    
    print()
    
    # Documentation
    print("DOCUMENTATION:")
    print("-" * 40)
    doc_files = [
        ("PROJECT_STRUCTURE_NEW.md", "New Structure Guide"),
        ("README_ORGANIZED.md", "Organized README"),
        ("run_organized.bat", "New Launcher Script"),
    ]
    for path, desc in doc_files:
        total += 1
        if check_file(path, desc):
            found += 1
    
    print()
    
    # Legacy files (for compatibility)
    print("LEGACY FILES (Backward Compatibility):")
    print("-" * 40)
    legacy_files = [
        ("kakaotalk_fixed.py", "Fixed Version"),
        ("kakaotalk_real_chat.py", "Real Chat"),
        ("simple_chat_server.py", "Simple Server"),
        ("launch_real_chat.py", "Launcher"),
    ]
    for path, desc in legacy_files:
        if check_file(path, desc):
            pass  # Don't count legacy files in total
    
    print()
    print("=" * 70)
    print(f"SUMMARY: {found}/{total} files in new structure")
    
    if found == total:
        print("SUCCESS: All files are properly organized!")
        print("\nYou can now use:")
        print("  - run_organized.bat - for the new structure")
        print("  - run.bat - for backward compatibility")
    else:
        print("WARNING: Some files are missing in the new structure")
        print("The legacy files are still available for use.")
    
    print()
    print("IMPORTANT REMINDER:")
    print("-" * 40)
    print("Always use these paths for new development:")
    print("   - Server files -> /server/")
    print("   - Client files -> /client/")
    print("   - Test files -> /tests/")
    print("   - Documentation -> /docs/")
    print("-" * 40)

if __name__ == "__main__":
    main()