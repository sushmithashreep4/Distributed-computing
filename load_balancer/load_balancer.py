"""
load_balancer.py
Core Round Robin load-balancing logic and health monitoring.

This module is imported by load_balancer/app.py.
It is intentionally separated from the Flask application code
so the algorithm is easy to read, test, and explain.

ROUND ROBIN ALGORITHM:
    Keep a shared index (current_index).
    Each time a request arrives, pick the next available node:
        selected = nodes[current_index % len(available_nodes)]
        current_index += 1
    This guarantees even distribution over time.
"""

import threading
import time
import logging
import requests as http_client

import config as lb_config

log = logging.getLogger("[LOAD BALANCER]")


class RoundRobinLoadBalancer:
    """
    Maintains the list of backend nodes, their health status,
    per-node request counters, and implements the Round Robin
    selection algorithm.
    """

    def __init__(self):
        # Deep-copy the node list so we can add runtime state
        self.nodes = [
            {
                "id":              node["id"],
                "host":            node["host"],
                "healthy":         False,   # proven healthy only after first check
                "request_count":   0,
                "last_request_at": None,
            }
            for node in lb_config.BACKEND_NODES
        ]

        # Round Robin pointer — incremented on every request
        self._index = 0
        self._lock  = threading.Lock()   # Thread-safe index updates

        # Total requests forwarded since load balancer started
        self.total_requests = 0

        # Activity log — last 50 entries shown in the frontend
        self.activity_log = []

        # Start background health-check thread
        self._start_health_checker()

    # ── Health checking ───────────────────────────────────────────────────────

    def _check_node_health(self, node: dict):
        """Ping /api/health on a single node and update its healthy flag."""
        url = f"{node['host']}/api/health"
        try:
            resp = http_client.get(url, timeout=lb_config.REQUEST_TIMEOUT)
            node["healthy"] = (resp.status_code == 200)
        except Exception:
            node["healthy"] = False

    def _health_check_loop(self):
        """Background thread: periodically check all nodes."""
        while True:
            for node in self.nodes:
                self._check_node_health(node)
            time.sleep(lb_config.HEALTH_CHECK_INTERVAL)

    def _start_health_checker(self):
        """
        Run an immediate health check then start the periodic background thread.
        """
        # First check — run synchronously so the first real request
        # already has accurate health information.
        for node in self.nodes:
            self._check_node_health(node)

        thread = threading.Thread(target=self._health_check_loop, daemon=True)
        thread.start()
        log.info("Health-check thread started.")

    # ── Round Robin selection ─────────────────────────────────────────────────

    def _get_next_node(self):
        """
        Select the next healthy node using Round Robin.

        The algorithm:
            1. Collect all healthy nodes.
            2. If none are healthy, return None.
            3. Use (self._index % len(healthy_nodes)) to pick the node.
            4. Increment self._index.

        Note: We operate on the *healthy* subset so that an offline node
        is simply skipped — this provides basic fault tolerance.
        """
        with self._lock:
            healthy = [n for n in self.nodes if n["healthy"]]
            if not healthy:
                return None
            node = healthy[self._index % len(healthy)]
            self._index += 1
            return node

    # ── Request forwarding ────────────────────────────────────────────────────

    def forward_request(self, method: str, path: str, data=None, json=None, params=None):
        """
        Forward an HTTP request to the next available backend node.

        Returns (response_dict, http_status_code).
        """
        node = self._get_next_node()

        if node is None:
            log.warning("No healthy backend nodes available!")
            self._add_log("ERROR: No healthy backend nodes available")
            return {
                "status":  "error",
                "message": "No backend servers are currently available. Please start the server nodes.",
            }, 503

        target_url = f"{node['host']}{path}"
        log.info(f"Forwarding {method} {path} → {node['id']} ({node['host']})")
        self._add_log(f"Request received → Load Balancer selected {node['id']}")

        try:
            resp = http_client.request(
                method     = method,
                url        = target_url,
                json       = json,
                data       = data,
                params     = params,
                timeout    = lb_config.REQUEST_TIMEOUT,
            )
            # Update counters
            with self._lock:
                node["request_count"]   += 1
                node["last_request_at"]  = time.strftime("%Y-%m-%d %H:%M:%S")
                self.total_requests     += 1

            self._add_log(f"{node['id']} processed {method} {path} ✓")
            log.info(f"Response from {node['id']}: HTTP {resp.status_code}")

            return resp.json(), resp.status_code

        except http_client.exceptions.Timeout:
            node["healthy"] = False
            log.error(f"{node['id']} timed out — marked OFFLINE")
            self._add_log(f"{node['id']} TIMEOUT — marked OFFLINE")
            return {
                "status":  "error",
                "message": f"{node['id']} did not respond in time",
                "server_id": node["id"],
            }, 504

        except http_client.exceptions.ConnectionError:
            node["healthy"] = False
            log.error(f"{node['id']} connection refused — marked OFFLINE")
            self._add_log(f"{node['id']} CONNECTION REFUSED — marked OFFLINE")
            return {
                "status":  "error",
                "message": f"{node['id']} is not reachable",
                "server_id": node["id"],
            }, 503

        except Exception as exc:
            log.error(f"Unexpected error forwarding to {node['id']}: {exc}")
            self._add_log(f"ERROR forwarding to {node['id']}: {exc}")
            return {
                "status":  "error",
                "message": "Internal load balancer error",
            }, 500

    # ── Activity log ──────────────────────────────────────────────────────────

    def _add_log(self, message: str):
        """Append a timestamped entry to the activity log (max 50 entries)."""
        timestamp = time.strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        self.activity_log.insert(0, entry)
        if len(self.activity_log) > 50:
            self.activity_log = self.activity_log[:50]

    # ── Status summary ────────────────────────────────────────────────────────

    def get_status(self):
        """
        Return a JSON-serialisable summary of all nodes and statistics.
        Used by the /api/servers and /api/statistics endpoints.
        """
        return {
            "algorithm":      "Round Robin",
            "total_requests": self.total_requests,
            "nodes": [
                {
                    "id":              n["id"],
                    "host":            n["host"],
                    "status":          "online" if n["healthy"] else "offline",
                    "request_count":   n["request_count"],
                    "last_request_at": n["last_request_at"],
                }
                for n in self.nodes
            ],
        }
