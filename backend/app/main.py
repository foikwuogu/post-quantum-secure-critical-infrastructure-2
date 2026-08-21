from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from .routers import payments, pqc_status
from .services.metrics import metrics_response

app = FastAPI(
    title="Post-Quantum Secure Critical Infrastructure",
    description="Hybrid PQC migration prototype for simulated US payment rails (research prototype).",
    version="0.1.0",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(payments.router)
app.include_router(pqc_status.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    body, content_type = metrics_response()
    return Response(content=body, media_type=content_type)
