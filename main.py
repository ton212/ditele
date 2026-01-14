from typing import Union

from fastapi import FastAPI

from telemetry.router import router as telemetry_router

app = FastAPI(
    title="DiTelemetry API",
    description="Telemetry API for BYD vehicle data",
    version="1.0.0",
)

# Include versioned API router
app.include_router(telemetry_router)

# Keep existing routes for backward compatibility
@app.get("/")
def read_root():
    return {"Hello": "World", "api_version": "1.0.0", "docs": "/docs"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}