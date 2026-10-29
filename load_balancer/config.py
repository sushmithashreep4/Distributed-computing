"""
config.py — Load Balancer Configuration
"""

PORT  = 5000
HOST  = "0.0.0.0"
DEBUG = False

# Backend server nodes that the load balancer distributes requests across.
# In a real deployment these would be different IP addresses / hostnames.
# Here we simulate separate machines using different localhost ports.
BACKEND_NODES = [
    {"id": "Server Node 1", "host": "http://127.0.0.1:5001"},
    {"id": "Server Node 2", "host": "http://127.0.0.1:5002"},
    {"id": "Server Node 3", "host": "http://127.0.0.1:5003"},
]

# How long (seconds) to wait for a backend node to respond before
# considering it unavailable.
REQUEST_TIMEOUT = 5

# How often (seconds) the background health-check thread pings each node.
HEALTH_CHECK_INTERVAL = 10
