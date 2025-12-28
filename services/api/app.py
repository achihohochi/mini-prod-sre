import random
import time
import logging
from pathlib import Path

# 🔹 OpenTelemetry API
# This lets us ask: "what trace/span am I currently inside?"
from opentelemetry import trace

from fastapi import FastAPI
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

# --------------------------------------------------
# LOGGING SETUP
# --------------------------------------------------

LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "api.log"

logger = logging.getLogger("api")
logger.setLevel(logging.INFO)

# 🔹 This logging filter injects trace_id + span_id
# into EVERY log line automatically.
#
# What this does:
# - Reads the currently active OpenTelemetry span
# - Extracts trace_id and span_id
# - Attaches them to the log record
#
# Result:
# Logs can be correlated directly to traces in Jaeger/Grafana
class TraceContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        span = trace.get_current_span()
        ctx = span.get_span_context()

        if ctx and ctx.is_valid:
            record.trace_id = format(ctx.trace_id, "032x")
            record.span_id = format(ctx.span_id, "016x")
        else:
            record.trace_id = "0" * 32
            record.span_id = "0" * 16

        return True


# Avoid duplicate handlers if the app reloads
if not logger.handlers:
    # 🔹 Log format now includes trace_id + span_id
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s trace_id=%(trace_id)s span_id=%(span_id)s %(message)s"
    )

    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setFormatter(fmt)
    file_handler.addFilter(TraceContextFilter())  # 👈 tracing enabled here

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(fmt)
    stream_handler.addFilter(TraceContextFilter())  # 👈 tracing enabled here

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

# --------------------------------------------------
# FASTAPI APP
# --------------------------------------------------

app = FastAPI()

# --------------------------------------------------
# PROMETHEUS METRICS
# --------------------------------------------------

REQUEST_COUNT = Counter(
    "api_requests_total",
    "Total HTTP requests",
    ["endpoint", "method", "http_status"],
)

REQUEST_LATENCY = Histogram(
    "api_request_duration_seconds",
    "Request latency in seconds",
    ["endpoint", "method"],
)

# --------------------------------------------------
# ROUTES
# --------------------------------------------------

@app.get("/healthz")
def healthz():
    # 🔹 This log will automatically include trace_id/span_id
    logger.info("healthz called")
    return {"status": "ok"}



@app.get("/work")
def work():
    endpoint = "/work"
    method = "GET"
    start = time.time()

    logger.info("work called")  # keep your existing line

    # simulate work
    time.sleep(random.uniform(0.02, 0.12))

    try:
        # simulate occasional failure
        if random.random() < 0.2:
            raise RuntimeError("simulated failure")

        status = "200"
        return {"ok": True, "slept_ms": "some"}

    except Exception as e:
        status = "500"
        logger.exception("work failed")  # <-- IMPORTANT: writes stack trace
        raise

    finally:
        duration = time.time() - start
        REQUEST_LATENCY.labels(endpoint=endpoint, method=method).observe(duration)
        REQUEST_COUNT.labels(endpoint=endpoint, method=method, http_status=status).inc()
        logger.info(f"work done status={status} duration_ms={duration*1000:.1f}")



@app.get("/metrics")
def metrics():
    # Prometheus scrapes this endpoint every N seconds
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)