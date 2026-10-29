"""
Load Balancer — app.py
Entry point for the Flask-based Load Balancer running on Port 5000.

Responsibilities:
    1. Accept all incoming HTTP requests from the frontend client.
    2. Delegate request routing to RoundRobinLoadBalancer.
    3. Return the backend response (with server identity) to the client.
    4. Expose /api/servers and /api/statistics for the monitoring dashboard.
    5. Serve the frontend HTML directly so the browser only needs one origin.

Architecture:
    CLIENT → Load Balancer (:5000) → Node 1 (:5001)
                                   → Node 2 (:5002)
                                   → Node 3 (:5003)
                                              ↓
                                        SQLite DB
"""

import sys
import os
import logging

# ── Allow sibling imports ────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))          # load_balancer/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))  # project root

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

import config as lb_config
from load_balancer import RoundRobinLoadBalancer

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[LOAD BALANCER] %(message)s"
)
log = logging.getLogger(__name__)

# ── Flask app ─────────────────────────────────────────────────────────────────
# Serve static files (frontend/) from the project root
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="/static")
CORS(app)

# ── Instantiate the load balancer (starts health-check thread immediately) ───
lb = RoundRobinLoadBalancer()


# ─────────────────────────────── ROUTES ──────────────────────────────────────

# ── Frontend ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Serve the main frontend HTML page."""
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/style.css")
def stylesheet():
    return send_from_directory(FRONTEND_DIR, "style.css")


@app.route("/script.js")
def javascript():
    return send_from_directory(FRONTEND_DIR, "script.js")


# ── Load Balancer health ───────────────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def lb_health():
    """Confirm the load balancer itself is running."""
    return jsonify({
        "status":    "healthy",
        "component": "Load Balancer",
        "port":      lb_config.PORT,
        "algorithm": "Round Robin",
    }), 200


# ── Server monitoring ─────────────────────────────────────────────────────────

@app.route("/api/servers", methods=["GET"])
def get_servers():
    """
    Return the health and statistics of all backend nodes.
    Used by the 'Distributed Server Monitor' panel in the frontend.
    """
    status = lb.get_status()
    return jsonify(status), 200


@app.route("/api/statistics", methods=["GET"])
def get_statistics():
    """
    Return request counters and the activity log.
    Used by the 'Live Load Balancing Activity' panel.
    """
    status = lb.get_status()
    return jsonify({
        "total_requests": lb.total_requests,
        "activity_log":   lb.activity_log,
        "nodes":          status["nodes"],
        "algorithm":      "Round Robin",
    }), 200


# ── Product routes (forwarded to backend nodes) ───────────────────────────────

@app.route("/api/products", methods=["GET"])
def proxy_products():
    log.info("Incoming request: GET /api/products")
    data, status = lb.forward_request("GET", "/api/products")
    return jsonify(data), status


@app.route("/api/products/<int:product_id>", methods=["GET"])
def proxy_product(product_id):
    log.info(f"Incoming request: GET /api/products/{product_id}")
    data, status = lb.forward_request("GET", f"/api/products/{product_id}")
    return jsonify(data), status


# ── Order route (forwarded to backend nodes) ──────────────────────────────────

@app.route("/api/orders", methods=["POST"])
def proxy_order():
    log.info("Incoming request: POST /api/orders")
    body = request.get_json(silent=True)
    if body is None:
        return jsonify({
            "status":  "error",
            "message": "Invalid or missing JSON body",
        }), 400
    data, status = lb.forward_request("POST", "/api/orders", json=body)
    return jsonify(data), status


# ── Error handlers ────────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return jsonify({"status": "error", "message": "Endpoint not found on load balancer"}), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"status": "error", "message": "Load balancer internal error"}), 500


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log.info(f"Load Balancer starting on port {lb_config.PORT} ...")
    log.info("Algorithm: Round Robin")
    log.info(f"Backend nodes: {[n['host'] for n in lb_config.BACKEND_NODES]}")
    app.run(host=lb_config.HOST, port=lb_config.PORT, debug=lb_config.DEBUG)
