# Mini Prod SRE – Metrics, Logs, and Traces

**local SRE / observability lab demonstrates how 3 core observability pillars work **together**:

- **Metrics** → Prometheus  
- **Logs** → Loki + Promtail  
- **Traces** → OpenTelemetry + Jaeger  
- **Panel** → Grafana

Collect telemetry, and **debug an incident** by correlating:
**a spike in metrics → the exact log lines → the exact distributed trace** that caused the issue.

---

We simulate a small production‑like API service:

- A FastAPI service with:
  - `/work` endpoint that:
    - Sleeps for a short time
    - Randomly fails (~20% of requests)
  - `/healthz` endpoint
  - `/metrics` endpoint for Prometheus
- Realistic failure behavior (HTTP 500s)
- Structured logs written to files (not just stdout)
- Distributed tracing with trace IDs injected into logs

This lets us reproduce a common real‑world scenario:

> “Users are seeing errors — what changed, when did it start, and what exactly failed?”

---

## Architecture Overview

```
curl / browser
      │
      ▼
FastAPI (Python)
 ├─ Prometheus metrics (/metrics)
 ├─ File logs (/logs/api.log)
 └─ OpenTelemetry traces
      │
      ▼
OpenTelemetry Collector
 ├─ forwards traces → Jaeger
 └─ (future) logs/metrics routing

Promtail
 └─ tails log files → Loki

Prometheus
 └─ scrapes metrics every 10s

Grafana
 ├─ Metrics (Prometheus)
 ├─ Logs (Loki)
 └─ Traces (Jaeger)
```

---

## Key Concepts Demonstrated

### Metrics (Prometheus)
- Request rate
- Error counts (200 vs 500)
- Latency histograms
- Burst traffic analysis using:
  - `rate()`
  - `increase()`
  - `sum by (http_status)`

Metrics answer:
> **“Is something wrong, and how bad is it?”**

---

### Logs (Loki + Promtail)
- Application logs written to files:
  - `logs/api.log` (inside the app container)
- Promtail tails files and ships logs to Loki
- Logs include:
  - Timestamp
  - Log level
  - Message
  - **trace_id + span_id**

Logs answer:
> **“What exactly happened?”**

---

### Traces (OpenTelemetry + Jaeger)
- Each request creates a trace
- Errors automatically mark spans as failed
- Exceptions captured with stack traces
- Traces visualize:
  - Request lifecycle
  - Duration
  - Failure location

Traces answer:
> **“Where did it fail, and why?”**

---

## The Metric → Log → Trace Drill

### Step 1: Detect the problem (Metrics)
We generate a burst of traffic:

```bash
for i in {1..50}; do curl -s -o /dev/null http://localhost:8000/work; done
```

In Prometheus:

```promql
sum by (http_status) (
  increase(api_requests_total{endpoint="/work"}[5m])
)
```

We observe:
- ~40 successful requests (200)
- ~10 failures (500)

This confirms **an error spike**.

---

### Step 2: Investigate what failed (Logs)
In Grafana → Explore → Loki:

```logql
{job="api"} |= "work failed"
```

We see:
- Exact timestamps of failures
- Error messages
- Embedded `trace_id` values

Now we know:
> **Which requests failed and when.**

---

### Step 3: Root cause analysis (Traces)
From the log entry, we copy the `trace_id` and open Jaeger:

```
http://localhost:16686/trace/<trace_id>
```

In Jaeger we see:
- The failing `/work` request
- Exception details (`simulated failure`)
- Span timing and error flags

Now we know:
> **Exactly why the request failed.**

---

## Why This Matters (Real‑World Value)

This setup mirrors how production teams operate at scale:

- Metrics detect issues early
- Logs provide context
- Traces prove causality

Without correlation:
- Metrics alone are vague
- Logs alone are noisy
- Traces alone lack impact context

**Together, they reduce MTTR dramatically.**

---

## Tech Stack

- **FastAPI** – API service
- **Prometheus** – Metrics
- **Grafana** – Visualization
- **Loki** – Log storage
- **Promtail** – Log shipping
- **OpenTelemetry** – Instrumentation
- **Jaeger** – Distributed tracing
- **Docker Compose** – Local orchestration

---

## What This Repo Is (and Is Not)

**This is:**
- A learning lab
- A portfolio‑ready SRE example
- A realistic incident drill

**This is not:**
- A production‑hardened setup
- A long‑term storage configuration
- A full alerting system (yet)

---

## Next Steps

- Grafana dashboards with:
  - Click metric → related logs
  - Click log → trace
- Error rate alerts
- Latency SLOs
- Trace‑derived RED metrics

---

## TL;DR

Metrics tell you **something is wrong**  
Logs tell you **what happened**  
Traces tell you **why it happened**  
