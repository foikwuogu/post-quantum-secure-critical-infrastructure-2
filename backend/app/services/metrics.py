from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

PAYMENTS_PROCESSED = Counter(
    "pqc_payments_processed_total",
    "Count of simulated payments processed",
    ["rail", "path"],
)

HANDSHAKE_LATENCY_MS = Histogram(
    "pqc_handshake_latency_ms",
    "Key-exchange handshake latency in milliseconds",
    ["path"],
    buckets=[0.5, 1, 2, 5, 10, 25, 50, 100, 250, 500],
)

SIGNING_LATENCY_MS = Histogram(
    "pqc_signing_latency_ms",
    "Message signing latency in milliseconds",
    ["path"],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 25, 50, 100],
)


def record_payment(rail: str, path: str, handshake_ms: float, signing_ms: float):
    PAYMENTS_PROCESSED.labels(rail=rail, path=path).inc()
    HANDSHAKE_LATENCY_MS.labels(path=path).observe(handshake_ms)
    SIGNING_LATENCY_MS.labels(path=path).observe(signing_ms)


def metrics_response():
    return generate_latest(), CONTENT_TYPE_LATEST
