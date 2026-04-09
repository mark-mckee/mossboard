# MOSSBoard

![Main View](src/mainview.png)

**Max's OpenSource Status Board** — a self-hosted, Docker-based status page for displaying the operational state of your services.

Built with Python, Vue 3, and MongoDB.

![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)
![Python](https://img.shields.io/badge/Python-3.12-blue)
![Vue](https://img.shields.io/badge/Vue-3-42b883)

---

## Features

- **Public status page** — overall status banner, collapsible service sections, 24-hour history bars, scheduled maintenance notices
- **Service detail** — 5-minute granularity history bar, 30-day uptime summary, status change log, incident timeline
- **Fullscreen monitor** — optimized for wall displays; live clock, pulsing indicators for degraded services
- **Active monitoring** — HTTP, TCP, ICMP (ping), and DNS checks; threshold-based status mapping; anti-flap confirmation periods; staleness detection
- **Incident management** — multi-step incident lifecycle: Investigating → Identified → Monitoring → Resolved
- **Scheduled maintenance** — windows with optional auto-status: service is automatically set to `under_maintenance` on start and restored to `operational` on end
- **API token auth** — push status updates from CI/CD or external tools via `PATCH /api/v1/services/{slug}/status`
- **Status change notes** — attach an optional reason to every status change; shown in the service log
- **Admin interface** — manage sections, services, incidents, maintenance, monitors, API tokens, and users
- **Swagger UI** — interactive API docs at `/docs` with Bearer token support
- **Dark / light theme** — toggled in the header and admin sidebar; persisted in `localStorage`

---

## Screenshots

### Mainview
![Main View](src/mainview.png)

### Details of a service
![Details of a service](src/details.png)

### Monitor view (with fullscreen mode)
![Monitor view](src/monitor.png)

### Admin
![Admin](src/admin.png)

### Monitors
![Monitors](src/monitors.png)

### Plan maintenances
![Plan maintenances](src/maintenance.png)




## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12 · APIFlask · MongoEngine |
| Database | MongoDB 7 |
| Queue | Redis 7 · Celery · Celery Beat |
| Frontend | Vue 3 · Vite · Tailwind CSS |
| Icons | Lucide Vue Next |
| Font | JetBrains Mono (self-hosted via @fontsource) |
| Proxy | nginx (inside frontend container) |

---

## Docker Compose Setup

MOSSBoard ships as a fully self-contained Docker Compose stack. No external services are required — MongoDB and Redis run as containers alongside the application.

### Services

```
┌─────────────┐     ┌─────────────┐
│   frontend  │────▶│   backend   │
│  Vue + nginx│     │   APIFlask  │
│  port 3444  │     │  port 5444  │
└─────────────┘     └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         ┌────────┐  ┌────────┐  ┌────────┐
         │ worker │  │  beat  │  │ mongo  │
         │ Celery │  │ Celery │  │  + DB  │
         └────────┘  └────────┘  └────────┘
                           │
                      ┌────────┐
                      │ redis  │
                      └────────┘
```

| Service | Role |
|---------|------|
| `frontend` | Serves the Vue SPA via nginx; proxies `/api/`, `/docs`, `/openapi.json` to `backend` |
| `backend` | Python/APIFlask REST API |
| `worker` | Celery worker — executes monitor checks and background tasks |
| `beat` | Celery Beat — dispatches scheduled tasks every minute/5 minutes |
| `mongo` | MongoDB 7 — persistent data store (volume: `mongo_data`) |
| `redis` | Redis 7 — Celery broker and result backend |

Only `frontend` (port `3444`) needs to be exposed publicly. `backend` (port `5444`) is only needed if you want direct API access during development.

---

## Installation

### Requirements

- [Docker](https://docs.docker.com/get-docker/) 24+
- [Docker Compose](https://docs.docker.com/compose/) v2 (`docker compose`, not `docker-compose`)

### Step 1 — Clone the repository

```bash
git clone https://github.com/lanbugs/mossboard.git
cd mossboard
```

### Step 2 — Create the environment file

```bash
cp .env.example .env
```

Open `.env` in your editor and set the required values (see [Configuration](#configuration) below).  
At minimum you must set `SECRET_KEY` and `ADMIN_PASSWORD`.

### Step 3 — Start all services

```bash
docker compose up -d
```

This will build the `backend` and `frontend` images on first run (a few minutes). Subsequent starts are instant.

Check that all containers are running:

```bash
docker compose ps
```

```
NAME                STATUS          PORTS
mossboard-backend   Up              0.0.0.0:5444->5000/tcp
mossboard-beat      Up
mossboard-frontend  Up              0.0.0.0:3444->80/tcp
mossboard-mongo     Up              27017/tcp
mossboard-redis     Up              6379/tcp
mossboard-worker    Up
```

### Step 4 — Open in browser

| URL | Description |
|-----|-------------|
| `http://localhost:3444/` | Public status page |
| `http://localhost:3444/monitor` | Fullscreen monitor |
| `http://localhost:3444/admin` | Admin interface |
| `http://localhost:3444/docs` | Swagger API docs |

Log in at `/admin` with the credentials from your `.env` file.

---

## Configuration

All configuration is done via environment variables in `.env`.

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | *(required)* | Flask session secret — use a long random string in production |
| `FLASK_ENV` | `development` | Set to `production` in production deployments |
| `MONGODB_URI` | `mongodb://mongo:27017/mossboard` | MongoDB connection URI |
| `REDIS_URL` | `redis://redis:6379/0` | Redis URL for general use |
| `CELERY_BROKER_URL` | `redis://redis:6379/1` | Celery task broker |
| `CELERY_RESULT_BACKEND` | `redis://redis:6379/2` | Celery result storage |
| `ADMIN_USERNAME` | `admin` | Fallback admin username — only used when no users exist in the database |
| `ADMIN_PASSWORD` | *(required)* | Fallback admin password |

> **Note:** The `ADMIN_USERNAME` / `ADMIN_PASSWORD` fallback is only active as long as the `users` collection in MongoDB is empty. Once you create a user via **Admin → Users**, the env-var credentials are no longer used.

### Generating a secure SECRET_KEY

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### Using an external MongoDB or Redis

Replace the default URIs with your own connection strings. The `mongo` and `redis` services in `docker-compose.yml` can then be removed or commented out.

```env
MONGODB_URI=mongodb://user:password@your-mongo-host:27017/mossboard
REDIS_URL=redis://:password@your-redis-host:6379/0
CELERY_BROKER_URL=redis://:password@your-redis-host:6379/1
CELERY_RESULT_BACKEND=redis://:password@your-redis-host:6379/2
```

---

## First-Time Setup

After starting MOSSBoard for the first time:

### 1. Create sections and services

Navigate to **Admin → Sections** and create at least one section (e.g. "Infrastructure", "Applications").

Then go to **Admin → Services** and add your services. Each service needs:
- A **name** and **section**
- A **slug** (auto-generated, used in API calls)
- Optionally a **staleness timeout** — the service will flip to `unknown` if no update arrives within this window

### 2. Set up monitors (optional)

Go to **Admin → Monitors → New Monitor** to configure automatic checks for your services:

1. Select a **check type** (HTTP / TCP / ICMP / DNS)
2. Enter the target (URL, host, or host + port)
3. Define **response-time thresholds** — add one row per status level, e.g. `200 ms → operational`, `800 ms → performance_issues`
4. Set a **failure status** for connection errors and timeouts
5. Optionally set a **confirmation period** to avoid status flapping
6. Click **Save**, then **Run now** to test immediately

### 3. Create API tokens (optional)

Go to **Admin → API Tokens** to generate tokens for pushing status updates from CI/CD pipelines, deployment scripts, or monitoring tools. Tokens can be restricted to specific services.

### 4. Add users

Go to **Admin → Users** to create dedicated accounts. Two roles are available:
- **Admin** — full access to all admin features
- **Viewer** — read-only access to the admin interface

### 5. Schedule maintenance

Go to **Admin → Maintenance** to create planned maintenance windows. Enable **Auto-status** to have MOSSBoard automatically set the service to `under_maintenance` when the window starts and restore it to `operational` when it ends.

---

## Active Monitoring

Monitors run as Celery tasks every minute and automatically update the linked service status. Configure under **Admin → Monitors**.

### Check types

| Type | What is checked |
|------|----------------|
| **HTTP** | GET request — HTTP status code + response time |
| **TCP** | TCP connection to `host:port` — connection time |
| **ICMP** | `ping -c 3` — packet loss % + average RTT |
| **DNS** | DNS resolution — answer values + query latency |

### Threshold system

Each monitor defines **response-time thresholds** as an ordered list of `(max_ms → status)` rules. The first rule whose `max_ms` covers the measured time wins. If none match, `failure_status` is applied.

ICMP monitors additionally support **packet-loss thresholds** (`max_percent → status`). When both apply, the worse status wins.

DNS monitors can specify **expected values** (e.g. an IP address). All listed values must appear in the answer; otherwise `failure_status` is used.

**Example — HTTP monitor:**

| Condition | Status |
|-----------|--------|
| Response time ≤ 200 ms | `operational` |
| Response time ≤ 800 ms | `performance_issues` |
| Response time > 800 ms or wrong status code | `major_outage` |

### Anti-flap confirmation period

Set **Confirmation (s)** to require a new candidate status to be observed continuously for that many seconds before it is applied. Useful for services with occasional brief latency spikes. Set to `0` for immediate changes.

### Staleness detection

Each service can have an optional **Staleness timeout** (seconds). If no status update is received within that window — from any source (monitor, API, or admin) — the service is automatically set to `unknown`. Useful for detecting dead monitors or missing push updates.

---

## API

### Push status from CI/CD or external tools

```bash
curl -X PATCH https://your-domain/api/v1/services/{slug}/status \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"status": "operational", "note": "Deployment completed"}'
```

**Status values:** `operational` · `performance_issues` · `partial_outage` · `major_outage` · `under_maintenance` · `unknown`

The `note` field is optional. A status change snapshot is written immediately and appears in the service log.

### Generate a token

1. Go to **Admin → API Tokens → New Token**
2. Optionally restrict the token to specific services
3. Copy the token — it is shown only once

Full interactive API documentation is available at `/docs`.

---

## Production Deployment

### Reverse proxy

In production, place a reverse proxy (nginx, Caddy, Traefik, etc.) in front of MOSSBoard and terminate TLS there. Proxy all traffic to `localhost:3444`.

Example nginx server block:

```nginx
server {
    listen 443 ssl;
    server_name status.example.com;

    ssl_certificate     /etc/ssl/certs/your-cert.pem;
    ssl_certificate_key /etc/ssl/private/your-key.pem;

    location / {
        proxy_pass http://localhost:3444;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Recommended `.env` settings for production

```env
FLASK_ENV=production
SECRET_KEY=<long-random-string>
ADMIN_PASSWORD=<strong-password>
```

### Data persistence

MongoDB data is stored in the `mongo_data` Docker volume. Back it up with:

```bash
docker compose exec mongo mongodump --db mossboard --out /tmp/dump
docker cp $(docker compose ps -q mongo):/tmp/dump ./backup
```

### Keeping images up to date

```bash
git pull
docker compose up --build -d
```

---

## Status Reference

| Status | Meaning |
|--------|---------|
| `operational` | Service is fully functional |
| `performance_issues` | Degraded performance or higher latency |
| `partial_outage` | Subset of functionality unavailable |
| `major_outage` | Service is down or critically impaired |
| `under_maintenance` | Planned maintenance in progress |
| `unknown` | Status not yet determined or stale |

The **overall status** shown on the public page is the worst status across all visible services.

---

## Development

```bash
# Rebuild after backend changes (Python code, requirements, Dockerfile)
docker compose up --build -d backend worker beat

# Rebuild after frontend changes
docker compose up --build -d frontend

# Follow logs
docker compose logs -f backend
docker compose logs -f worker

# Open a shell in the backend container
docker compose exec backend bash
```

### Project structure

```
mossboard/
├── backend/
│   ├── app/
│   │   ├── api/          # API blueprints (public, admin, token auth, monitors)
│   │   ├── models/       # MongoEngine models
│   │   └── tasks/        # Celery tasks (snapshots, monitors, staleness, maintenance)
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── views/        # Vue pages (StatusPage, ServiceDetail, Monitor, admin/*)
│   │   └── components/   # Shared components (StatusBar, StatusBadge, ...)
│   └── Dockerfile
└── docker-compose.yml
```

---

## Contributing

Contributions are welcome. Please open an issue first to discuss larger changes. For bug fixes and small improvements, pull requests are appreciated.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes
4. Open a pull request

Please keep the code style consistent with the existing codebase (Python: PEP 8, Vue: Composition API `<script setup>`).

---

## License

MOSSBoard is licensed under the [GNU General Public License v3.0](LICENSE).

© 2026 Maximilian Thoma
