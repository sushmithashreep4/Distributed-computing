"""
Server Node 1 — app.py
Independent Flask backend server running on Port 5001.

This file is identical in structure to server_node_2/app.py and
server_node_3/app.py.  The only difference is the imported config,
which sets SERVER_ID and PORT.

In a real distributed system each of these would run on a separate
physical machine or VM.  Here we simulate that by using different
localhost ports.
"""

import sys
import os
import datetime
import logging

# ── Allow importing the shared database module ──────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from flask import Flask, jsonify, request
from flask_cors import CORS

import config  # server_node_1/config.py
from database.database import init_db, get_all_products, get_product_by_id, create_order

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format=f"[{config.SERVER_ID.upper()}] %(message)s"
)
log = logging.getLogger(__name__)

# ── Flask app ─────────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)  # Allow cross-origin requests from the frontend

# ── In-memory request counter (resets when server restarts) ──────────────────
request_count = 0
last_request_time = None


def record_request():
    """Increment counter and record timestamp for each handled request."""
    global request_count, last_request_time
    request_count += 1
    last_request_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ── Helper ────────────────────────────────────────────────────────────────────
def base_response(data: dict) -> dict:
    """
    Attach server identity metadata to every response.
    This makes the Round Robin distribution clearly visible to the client.
    """
    data.update({
        "server_id": config.SERVER_ID,
        "port":      config.PORT,
    })
    return data


# ─────────────────────────────── ROUTES ──────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health():
    """
    Health check endpoint — used by the Load Balancer to determine
    whether this node is alive.
    """
    return jsonify(base_response({"status": "healthy"})), 200


@app.route("/api/server-status", methods=["GET"])
def server_status():
    """
    Returns full server metadata including request statistics.
    Displayed in the frontend 'Distributed Server Monitor' panel.
    """
    record_request()
    log.info("Processing GET /api/server-status")
    return jsonify(base_response({
        "status":            "online",
        "request_count":     request_count,
        "last_request_time": last_request_time,
        "uptime_note":       "Simulated distributed server node",
    })), 200


@app.route("/api/products", methods=["GET"])
def get_products():
    """Return the full product catalogue."""
    record_request()
    log.info("Processing GET /api/products")
    products = get_all_products()
    return jsonify(base_response({
        "status":   "success",
        "products": products,
        "count":    len(products),
    })), 200


@app.route("/api/products/<int:product_id>", methods=["GET"])
def get_product(product_id):
    """Return a single product by ID."""
    record_request()
    log.info(f"Processing GET /api/products/{product_id}")
    product = get_product_by_id(product_id)
    if not product:
        return jsonify(base_response({
            "status":  "error",
            "message": f"Product {product_id} not found",
        })), 404
    return jsonify(base_response({
        "status":  "success",
        "product": product,
    })), 200


@app.route("/api/orders", methods=["POST"])
def place_order():
    """
    Create a new order.
    Expected JSON body:
        { "product_id": 1, "quantity": 2, "customer_name": "Demo User" }
    """
    record_request()
    log.info("Processing POST /api/orders")

    data = request.get_json(silent=True)
    if not data:
        return jsonify(base_response({
            "status":  "error",
            "message": "Invalid or missing JSON body",
        })), 400

    # Validate required fields
    required = ["product_id", "quantity", "customer_name"]
    for field in required:
        if field not in data:
            return jsonify(base_response({
                "status":  "error",
                "message": f"Missing required field: {field}",
            })), 400

    try:
        product_id    = int(data["product_id"])
        quantity      = int(data["quantity"])
        customer_name = str(data["customer_name"]).strip()
    except (ValueError, TypeError):
        return jsonify(base_response({
            "status":  "error",
            "message": "product_id and quantity must be integers",
        })), 400

    if quantity <= 0:
        return jsonify(base_response({
            "status":  "error",
            "message": "Quantity must be greater than zero",
        })), 400

    if not customer_name:
        return jsonify(base_response({
            "status":  "error",
            "message": "customer_name cannot be empty",
        })), 400

    order_id, error = create_order(product_id, quantity, customer_name, config.SERVER_ID)
    if error:
        return jsonify(base_response({
            "status":  "error",
            "message": error,
        })), 400

    log.info(f"Order {order_id} created for '{customer_name}'")
    return jsonify(base_response({
        "status":   "success",
        "message":  "Order created successfully",
        "order_id": order_id,
    })), 201


# ── Error handlers ────────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return jsonify(base_response({"status": "error", "message": "Endpoint not found"})), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify(base_response({"status": "error", "message": "Internal server error"})), 500


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log.info(f"Starting {config.SERVER_ID} on port {config.PORT} ...")
    init_db()   # Ensure schema and seed data exist
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
