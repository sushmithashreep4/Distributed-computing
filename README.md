# Distributed E-Commerce — Load Balancing Demo
### B.Tech Distributed Computing Practical Assignment

---

## Objective

Demonstrate the **Load Balancing** concept in a distributed computing environment using a functional e-commerce application. The prototype shows how a Load Balancer distributes incoming client requests across multiple independent backend server nodes using the **Round Robin** algorithm.

---

## Distributed Computing Concept

### Without Load Balancing
```
100 requests
      |
      ▼
  Server 1        ← OVERLOADED, single point of failure
```

### With Load Balancing (this project)
```
100 requests
      |
      ▼
 Load Balancer
      |
  +---+---+---+
  |   |   |   |
  ▼   ▼   ▼   
 N1  N2  N3   ← Even distribution
 34  33  33 requests each
```

---

## Architecture

```
USER / CLIENT (Browser)
         |
         | HTTP Request to port 5000
         ▼
+---------------------------+
|      LOAD BALANCER        |
|       Port: 5000          |
|   Algorithm: Round Robin  |
|   (Flask Application)     |
+----------+----------------+
           |
   +-------+-------+-------+
   |       |               |
   ▼       ▼               ▼
+-------+ +-------+   +-------+
|NODE 1 | |NODE 2 |   |NODE 3 |
|:5001  | |:5002  |   |:5003  |
|Flask  | |Flask  |   |Flask  |
+---+---+ +---+---+   +---+---+
    \          |          /
     \         |         /
      +--------+---------+
               |
               ▼
        +-------------+
        |  SQLite DB  |
        | ecommerce.db|
        +-------------+
```

> **Note:** Distributed servers are **simulated as independent Python processes** running on different localhost ports. This is the same architectural concept used when backend servers are deployed across separate physical machines or cloud instances.

---

## Technologies Used

| Layer             | Technology       |
|-------------------|-----------------|
| Frontend          | HTML5, CSS3, JavaScript (Vanilla) |
| Backend           | Python 3, Flask  |
| Load Balancer     | Flask + `requests` library |
| Database          | SQLite           |
| Cross-Origin      | Flask-CORS       |

---

## Project Structure

```
distributed-ecommerce/
│
├── load_balancer/
│   ├── app.py              ← Flask app, serves frontend + proxies API calls
│   ├── load_balancer.py    ← Round Robin algorithm + health checking
│   └── config.py           ← LB port, backend node list, timeouts
│
├── server_node_1/
│   ├── app.py              ← Independent Flask server (port 5001)
│   └── config.py
│
├── server_node_2/
│   ├── app.py              ← Independent Flask server (port 5002)
│   └── config.py
│
├── server_node_3/
│   ├── app.py              ← Independent Flask server (port 5003)
│   └── config.py
│
├── database/
│   ├── database.py         ← SQLite schema, seed data, query functions
│   └── ecommerce.db        ← Created automatically on first run
│
├── frontend/
│   ├── index.html          ← Dashboard UI
│   ├── style.css           ← Dark-theme professional styling
│   └── script.js           ← Real API calls, live log, test requests
│
├── requirements.txt
├── start_all_servers.bat   ← One-click Windows startup
└── README.md
```

---

## Installation

### Step 1 — Prerequisites
- Python 3.8 or higher (verify: `python --version`)
- pip (comes with Python)

### Step 2 — Install dependencies
Open a terminal in the `distributed-ecommerce/` folder and run:
```bash
pip install -r requirements.txt
```

This installs:
- `Flask` — web framework for all four servers
- `flask-cors` — enables cross-origin requests
- `requests` — used by the Load Balancer to forward HTTP requests

---

## How to Run

### Option A — One-Click (Recommended)
Double-click `start_all_servers.bat`

This opens **4 separate terminal windows**:
- `Server Node 1 [:5001]`
- `Server Node 2 [:5002]`
- `Server Node 3 [:5003]`
- `Load Balancer [:5000]`

Then opens your browser at `http://localhost:5000` automatically.

---

### Option B — Manual (if batch file fails)

Open **4 separate terminals** and run one command in each:

**Terminal 1 — Server Node 1:**
```bash
cd distributed-ecommerce/server_node_1
python app.py
```

**Terminal 2 — Server Node 2:**
```bash
cd distributed-ecommerce/server_node_2
python app.py
```

**Terminal 3 — Server Node 3:**
```bash
cd distributed-ecommerce/server_node_3
python app.py
```

**Terminal 4 — Load Balancer (start last):**
```bash
cd distributed-ecommerce/load_balancer
python app.py
```

Then open `http://localhost:5000` in your browser.

---

## API Endpoints

### Load Balancer (Port 5000)

| Method | Endpoint              | Description                                 |
|--------|-----------------------|---------------------------------------------|
| GET    | `/`                   | Serve frontend HTML                         |
| GET    | `/api/health`         | Load balancer health status                 |
| GET    | `/api/servers`        | All backend node statuses + request counts  |
| GET    | `/api/statistics`     | Full stats + activity log                   |
| GET    | `/api/products`       | **Forwarded** → backend node via Round Robin|
| GET    | `/api/products/<id>`  | **Forwarded** → backend node via Round Robin|
| POST   | `/api/orders`         | **Forwarded** → backend node via Round Robin|

### Backend Nodes (Ports 5001, 5002, 5003)

| Method | Endpoint              | Description                        |
|--------|-----------------------|------------------------------------|
| GET    | `/api/health`         | Node health check                  |
| GET    | `/api/server-status`  | Node status + request statistics   |
| GET    | `/api/products`       | All products from SQLite DB        |
| GET    | `/api/products/<id>`  | Single product                     |
| POST   | `/api/orders`         | Create order, deduct stock         |

Every backend response includes:
```json
{
  "server_id": "Server Node 2",
  "port": 5002,
  "status": "success",
  "products": [...]
}
```

---

## How Round Robin Works

```python
# From load_balancer.py

def _get_next_node(self):
    healthy = [n for n in self.nodes if n["healthy"]]
    if not healthy:
        return None
    node = healthy[self._index % len(healthy)]
    self._index += 1
    return node
```

**Example with 3 nodes:**
```
Request 1  →  index=0  →  0 % 3 = 0  →  Node 1
Request 2  →  index=1  →  1 % 3 = 1  →  Node 2
Request 3  →  index=2  →  2 % 3 = 2  →  Node 3
Request 4  →  index=3  →  3 % 3 = 0  →  Node 1
Request 5  →  index=4  →  4 % 3 = 1  →  Node 2
...
```

---

## How to Demonstrate Server Failure

1. Start all 4 processes.
2. Open the frontend at `http://localhost:5000`.
3. Send some requests — observe all 3 nodes receiving traffic.
4. **Close the terminal for Server Node 2.**
5. Wait ~10 seconds for the health-check thread to mark Node 2 as OFFLINE.
6. The UI shows `Server Node 2 — OFFLINE`.
7. Send more requests — the Load Balancer now distributes only between Node 1 and Node 3:
   ```
   Request 1 → Node 1
   Request 2 → Node 3
   Request 3 → Node 1
   Request 4 → Node 3
   ```
8. Restart Node 2 terminal — it comes back ONLINE within 10 seconds.

---

## Expected Output (Viva Demo Flow)

1. Four terminal windows, each running independently.
2. Browser shows the dashboard at `http://localhost:5000`.
3. Header: **Load Balancer ACTIVE | Algorithm: Round Robin**.
4. Server Monitor panel: **Node 1 ONLINE | Node 2 ONLINE | Node 3 ONLINE**.
5. Browse products → each click shows a different `server_id` in the activity log.
6. Place an order → confirmation shows which node processed it.
7. Click **Send Test Requests (12)** → bar chart shows ~4 requests per node.
8. Stop Node 2 → monitor shows it OFFLINE.
9. Send more requests → only Node 1 and Node 3 handle them.

---

## Real-World Use Case

Large e-commerce platforms (Amazon, Flipkart, Myntra) receive **millions of requests simultaneously** during events like flash sales. Without load balancing:

- All traffic hits a single server.
- The server becomes overloaded, slows down, and eventually crashes.
- The entire application goes down → lost revenue.

**With load balancing:**
```
Millions of users
        |
        ▼
   Load Balancer
        |
  +-----+-----+-----+
  |     |     |     |
  S1    S2    S3    S4 ...
```

Benefits demonstrated in this prototype:

| Benefit               | How demonstrated                                   |
|-----------------------|----------------------------------------------------|
| **Scalability**       | More nodes = more capacity (add to config)         |
| **High Availability** | Requests continue even when one node is stopped    |
| **Fault Tolerance**   | Failed node is skipped automatically               |
| **Load Distribution** | Round Robin ensures even request spread            |
| **Response Time**     | No single server bottleneck                        |

---

## Troubleshooting

| Problem                        | Solution                                           |
|--------------------------------|----------------------------------------------------|
| `pip` not found                | Use `python -m pip install -r requirements.txt`    |
| Port already in use            | Kill process: `netstat -ano | findstr :5000`       |
| Products not loading           | Ensure server nodes started before load balancer   |
| `ModuleNotFoundError: flask`   | Activate your virtual environment or reinstall     |
| Batch file opens and closes    | Right-click → "Run as administrator"               |

---

*Distributed Computing Practical — B.Tech CSE*
