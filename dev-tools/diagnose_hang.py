
import requests
import json
import time

def check_server():
    print("Checking server health...")
    try:
        resp = requests.get("http://127.0.0.1:8080/api/health", timeout=5)
        print(f"Health Status: {resp.status_code}, Body: {resp.text}")
    except Exception as e:
        print(f"Health check failed: {e}")

def check_anthropic():
    print("Checking Anthropic connectivity...")
    # We can't easily check the API without a key, but we can check if the host is reachable
    import socket
    try:
        host = "api.anthropic.com"
        port = 443
        socket.create_connection((host, port), timeout=5)
        print(f"Successfully connected to {host}:{port}")
    except Exception as e:
        print(f"Anthropic connectivity check failed: {e}")

if __name__ == "__main__":
    check_server()
    check_anthropic()
