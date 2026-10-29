"""
Server Node 3 — app.py
Independent Flask backend server running on Port 5003.
See server_node_1/app.py for full documentation.
"""

import sys
import os
import datetime
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from flask import Flask, jsonify, request
from flask_cors import CORS

import config
from database.database import init_db, get_all_products, get_product_by_id, create_order

logging.basicConfig(
    level=logging.INFO,
    format=f"[{config.SERVER_ID.upper()}] %(message)s"
)
log = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

request_count = 0
last_request_time = None


def record_request():
    global request_count, last_request_time
    request_count += 1
    last_request_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def base_response(data: dict) -> dict:
    data.update({"server_id": config.SERVER_ID, "port": config.PORT})
    return data


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify(base_response({"status": "healthy"})), 200


@app.route("/api/server-status", methods=["GET"])
def server_status():
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
    record_request()
    log.info(f"Processing GET /api/products/{product_id}")
    product = get_product_by_id(product_id)
    if not product:
        return jsonify(base_response({
            "status":  "error",
            "message": f"Product {product_id} not found",
        })), 404
    return jsonify(base_response({"status": "success", "product": product})), 200


@app.route("/api/orders", methods=["POST"])
def place_order():
    record_request()
    log.info("Processing POST /api/orders")
    data = request.get_json(silent=True)
    if not data:
        return jsonify(base_response({"status": "error", "message": "Invalid or missing JSON body"})), 400

    required = ["product_id", "quantity", "customer_name"]
    for field in required:
        if field not in data:
            return jsonify(base_response({"status": "error", "message": f"Missing required field: {field}"})), 400

    try:
        product_id    = int(data["product_id"])
        quantity      = int(data["quantity"])
        customer_name = str(data["customer_name"]).strip()
    except (ValueError, TypeError):
        return jsonify(base_response({"status": "error", "message": "product_id and quantity must be integers"})), 400

    if quantity <= 0:
        return jsonify(base_response({"status": "error", "message": "Quantity must be greater than zero"})), 400
    if not customer_name:
        return jsonify(base_response({"status": "error", "message": "customer_name cannot be empty"})), 400

    order_id, error = create_order(product_id, quantity, customer_name, config.SERVER_ID)
    if error:
        return jsonify(base_response({"status": "error", "message": error})), 400

    log.info(f"Order {order_id} created for '{customer_name}'")
    return jsonify(base_response({
        "status":   "success",
        "message":  "Order created successfully",
        "order_id": order_id,
    })), 201


@app.errorhandler(404)
def not_found(e):
    return jsonify(base_response({"status": "error", "message": "Endpoint not found"})), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify(base_response({"status": "error", "message": "Internal server error"})), 500


if __name__ == "__main__":
    log.info(f"Starting {config.SERVER_ID} on port {config.PORT} ...")
    init_db()
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
