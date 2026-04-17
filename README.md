# MOSSBoard

![Main View](src/mainview.png)

**Max's OpenSource Status Board** — a self-hosted, Docker-based status page for displaying the operational state of your services.

Built with Python, Vue 3, and MongoDB.

![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)
![Python](https://img.shields.io/badge/Python-3.12-blue)
![Vue](https://img.shields.io/badge/Vue-3-42b883)

---

## Features

- **Public status page** — overall status banner, collapsible service sections, 24-hour history bars, scheduled maintenance notices, optional incident timeline
- **Service detail** — 5-minute granularity history bar, 30-day and 12-month uptime summaries, inline metric charts, status change log, incident timeline
- **Fullscreen monitor** — optimized for wall displays; live clock, pulsing indicators for degraded services; two views: standard card grid (`/monitor`) and compressed section view (`/monitor2`)
- **Compressed monitor view** — sections collapse automatically when all services are operational (shows service count and green summary row); sections with any degraded service expand automatically and highlight affected services with pulsing status badges
- **Metrics** — push time-series data via API token; display as current value and/or sparkline chart on the status page and service detail view
- **Active monitoring** — HTTP, TCP, ICMP (ping), and DNS checks; threshold-based status mapping; anti-flap confirmation periods; staleness detection
- **HTTP monitor options** — custom proxy (host + port), SSL certificate verification toggle, response body regex validation
- **Incident management** — multi-step incident lifecycle: Investigating → Identified → Monitoring → Resolved
- **Scheduled maintenance** — windows with optional auto-status: service is automatically set to `under_maintenance` on start and restored to `operational` on end; active monitors are paused for the duration; supports **multiple services per window**, **recurring schedules** (daily / weekly / monthly with configurable day), and inline editing
- **Notifications** — fire-and-forget delivery via **HTTP webhook** (configurable method, headers, JSON body template) or **Email** (SMTP); trigger on maintenance announced/started/ended, incident created/updated/resolved, or monitor status transitions (filterable by from→to status and by service); template variables (`{{service_name}}`, `{{status}}`, `{{prev_status}}`, `{{title}}`, `{{message}}`, `{{timestamp}}`, and more) available in all body and subject templates; built-in test button sends a sample payload immediately
- **API token auth** — push status updates and metric data from CI/CD or external tools; tokens can be scoped to specific services and/or specific metrics, with independent master switches for each operation type
- **Status change notes** — attach an optional reason to every status change; shown in the service log; monitor-triggered changes include the measured value (response time, HTTP code, packet loss, etc.)
- **Admin interface** — manage sections, services, incidents, maintenance, monitors, metrics, API tokens, users, and global settings
- **Global settings** — configurable site title, default theme, wide layout, incident timeline, no-data behavior
- **Swagger UI** — interactive API docs at `/docs` with Bearer token support
- **Dark / light theme** — toggled in the header and admin sidebar; persisted in `localStorage`; server-side default respected on first visit

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

Two installation methods are available: using **pre-built images from Docker Hub** (recommended, no build step) or **building from source**.

---

### Option A — Docker Hub images (recommended)

Pre-built images are published on Docker Hub:

| Image | Description |
|-------|-------------|
| [`lanbugsde/mossboard-backend`](https://hub.docker.com/r/lanbugsde/mossboard-backend) | Python/APIFlask backend + Celery |
| [`lanbugsde/mossboard-frontend`](https://hub.docker.com/r/lanbugsde/mossboard-frontend) | Vue SPA served via nginx |

#### Step 1 — Clone the repository

```bash
git clone https://github.com/lanbugs/mossboard.git
cd mossboard
```

#### Step 2 — Create the environment file

```bash
cp .env.example .env
```

Open `.env` in your editor and set the required values (see [Configuration](#configuration) below).  
At minimum you must set `SECRET_KEY` and `ADMIN_PASSWORD`.

#### Step 3 — Start all services

```bash
docker compose -f docker-compose.hub.yml up -d
```

Images are pulled from Docker Hub automatically — no local build required.

Check that all containers are running:

```bash
docker compose -f docker-compose.hub.yml ps
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

#### Keeping Hub images up to date

```bash
docker compose -f docker-compose.hub.yml pull
docker compose -f docker-compose.hub.yml up -d
```

---

### Option B — Build from source

#### Step 1 — Clone the repository

```bash
git clone https://github.com/lanbugs/mossboard.git
cd mossboard
```

#### Step 2 — Create the environment file

```bash
cp .env.example .env
```

Open `.env` in your editor and set the required values (see [Configuration](#configuration) below).  
At minimum you must set `SECRET_KEY` and `ADMIN_PASSWORD`.

#### Step 3 — Start all services

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
| `http://localhost:3444/monitor` | Fullscreen monitor (card grid) |
| `http://localhost:3444/monitor2` | Fullscreen monitor — compressed section view |
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

### 3. Create metrics (optional)

Go to **Admin → Metrics → New Metric** to define time-series metrics for any service:

1. Select the **service** to attach the metric to
2. Set a **name** and optional **suffix** (e.g. `Users Online` / `users`)
3. Choose a **metric type**: *Average*, *Sum*, or *Last Value*
4. Set the **default view** window: Last Hour, Today, Last 7 Days, or Last 30 Days
5. Optionally configure a **threshold** (seconds) — pushes within the window are merged instead of stacked
6. Enable **Display Chart** to show an inline sparkline on the status page

Push data points to a metric using a Bearer token:

```bash
curl -X POST https://your-domain/api/v1/metrics/{metric-id}/points \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"value": 42}'
```

An optional `timestamp` field (ISO 8601) can be included to back-date a point.

### 4. Create API tokens (optional)

Go to **Admin → API Tokens** to generate tokens for pushing status updates or metric data from CI/CD pipelines, deployment scripts, or monitoring tools.

Each token has two independent permission switches:

| Permission | Controls |
|---|---|
| **Service status updates** | `PATCH /api/v1/services/{slug}/status` |
| **Metric data pushes** | `POST /api/v1/metrics/{id}/points` |

Each permission can be further restricted to a specific list of services or metrics. Leaving a list empty grants access to all resources of that type.

### 5. Add users

Go to **Admin → Users** to create dedicated accounts. Two roles are available:
- **Admin** — full access to all admin features
- **Viewer** — read-only access to the admin interface

### 6. Schedule maintenance

Go to **Admin → Maintenance** to create planned maintenance windows. Each window supports:

- **Multiple services** — select any number of services to include in the window
- **Auto-status** — MOSSBoard automatically sets each service to `under_maintenance` when the window starts and restores it to `operational` when it ends; active monitors are paused for the duration
- **Recurring schedules** — choose *Daily*, *Weekly* (with configurable day of week), or *Monthly* (with configurable day of month); MOSSBoard spawns the next occurrence automatically when the current window ends
- **Inline editing** — edit any existing window directly in the list without leaving the page

### 7. Configure notifications (optional)

Go to **Admin → Notifications** to set up automated alerts. The section has three tabs:

**Destinations** — Define where notifications are delivered:
- **Webhook** — HTTP POST (or GET/PUT/PATCH) to any URL with custom headers and a JSON body template
- **Email** — sends via SMTP to a configured recipient address with a subject and plain-text body template

Use the **Test** button on any destination to send a sample payload immediately.

**Rules** — Map triggers to destinations:

| Trigger | Fires when |
|---------|-----------|
| Maintenance Announced | A maintenance window is created |
| Maintenance Started | A window becomes active |
| Maintenance Ended | A window finishes |
| Incident Created | A new incident is opened |
| Incident Updated | An update is added to an incident |
| Incident Resolved | An incident is resolved |
| Monitor Status Change | A monitor changes status (optionally filter by from→to state) |

Rules can be limited to specific services and, for monitor status changes, to specific from/to status combinations.

**SMTP** — Configure the outgoing mail server (host, port, credentials, STARTTLS).

**Template variables** available in webhook body, email subject, and email body:

`{{service_name}}` · `{{service_slug}}` · `{{section_name}}` · `{{status}}` · `{{prev_status}}` · `{{title}}` · `{{description}}` · `{{starts_at}}` · `{{ends_at}}` · `{{message}}` · `{{monitor_name}}` · `{{recurrence}}` · `{{timestamp}}`

### 8. Configure global settings

Go to **Admin → Settings** to adjust board-wide behaviour:

| Setting | Description |
|---|---|
| **Site title** | Displayed in the public page header and monitor view |
| **Default theme** | Dark or light — applied on first visit; explicit browser preference always takes priority |
| **Wide layout** | Expands public pages from 896 px to 1152 px |
| **Incident timeline** | Show a day-grouped incident history at the bottom of the status page, with a configurable look-back window (1–90 days) |
| **No-data behavior** | How periods without snapshot data are handled in uptime calculations: *Unknown* (counts as downtime), *Operational* (counts as uptime), or *Exclude* (omitted from the percentage) |

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

### HTTP monitor options

| Option | Description |
|--------|-------------|
| **Proxy** | Route requests through an HTTP proxy (`host` + `port`) |
| **Verify SSL** | Disable TLS certificate verification for self-signed certificates |
| **Body regex** | Fail the check if the response body does not match the given regular expression |

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

### Maintenance protection

A monitor will never override a service that is currently in `under_maintenance` state — whether set manually or via a scheduled maintenance window. The monitor continues to run and record results but does not apply any status changes until the maintenance is lifted.

### Staleness detection

Each service can have an optional **Staleness timeout** (seconds). If no status update is received within that window — from any source (monitor, API, or admin) — the service is automatically set to `unknown`. Useful for detecting dead monitors or missing push updates.

---

## API

### Push a status update

```bash
curl -X PATCH https://your-domain/api/v1/services/{slug}/status \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"status": "operational", "note": "Deployment completed"}'
```

**Status values:** `operational` · `performance_issues` · `partial_outage` · `major_outage` · `under_maintenance` · `unknown`

The `note` field is optional. A status change snapshot is written immediately and appears in the service log.

### Push a metric data point

```bash
curl -X POST https://your-domain/api/v1/metrics/{metric-id}/points \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"value": 1234}'
```

An optional `timestamp` (ISO 8601) can be included. If the metric has a **threshold** configured and the last recorded point is within that window, the point is updated in place (sum accumulates; average uses a running mean) instead of creating a new entry.

### Generate a token

1. Go to **Admin → API Tokens → New Token**
2. Enable or disable **Service status updates** and **Metric data pushes** independently
3. Optionally restrict each permission to specific services or metrics
4. Copy the token — it is shown only once

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

**Docker Hub images:**

```bash
docker compose -f docker-compose.hub.yml pull
docker compose -f docker-compose.hub.yml up -d
```

**Build from source:**

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
│   │   ├── api/          # API blueprints (public, admin, token auth, monitors, metrics, settings, notifications)
│   │   ├── models/       # MongoEngine models
│   │   └── tasks/        # Celery tasks (snapshots, monitors, staleness, maintenance, notifications)
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── composables/  # Shared state (useTheme, useLayout)
│   │   ├── views/        # Vue pages (StatusPage, ServiceDetail, Monitor, Monitor2, admin/*)
│   │   └── components/   # Shared components (StatusBar, StatusBadge, MetricChart, ...)
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
