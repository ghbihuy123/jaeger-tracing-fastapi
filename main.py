import os
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Literal
import pytz
from dateutil import parser as dateutil_parser
from utils import PrometheusMiddleware, metrics, setting_otlp
# from prometheus_fastapi_instrumentator import Instrumentator
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter as OTLPSpanExporterGRPC,
)
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter as OTLPSpanExporterHTTP,
)
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from starlette.types import ASGIApp

EXPOSE_PORT = os.environ.get("EXPOSE_PORT", 8000)

# otlp-grpc, otlp-http
MODE = os.environ.get("MODE", "otlp-grpc")

OTLP_GRPC_ENDPOINT = os.environ.get("OTLP_GRPC_ENDPOINT", "jaeger-collector:4317")
OTLP_HTTP_ENDPOINT = os.environ.get(
    "OTLP_HTTP_ENDPOINT", "http://jaeger-collector:4318/v1/traces"
)

TARGET_ONE_HOST = os.environ.get("TARGET_ONE_HOST", "app-b")
TARGET_TWO_HOST = os.environ.get("TARGET_TWO_HOST", "app-c")

app = FastAPI(
    title="Secure Time Utilities API",
    version="1.0.0",
    description="Provides secure UTC/local time retrieval, formatting, timezone conversion, and comparison.",
)

def setting_jaeger(app: ASGIApp, log_correlation: bool = True) -> None:
    # set the tracer provider
    tracer = TracerProvider()
    trace.set_tracer_provider(tracer)

    if MODE == "otlp-grpc":
        tracer.add_span_processor(
            BatchSpanProcessor(
                OTLPSpanExporterGRPC(endpoint=OTLP_GRPC_ENDPOINT, insecure=True)
            )
        )
    elif MODE == "otlp-http":
        tracer.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporterHTTP(endpoint=OTLP_HTTP_ENDPOINT))
        )
    else:
        # default otlp-grpc
        tracer.add_span_processor(
            BatchSpanProcessor(
                OTLPSpanExporterGRPC(endpoint=OTLP_GRPC_ENDPOINT, insecure=True)
            )
        )

    # override logger format which with trace id and span id
    if log_correlation:
        LoggingInstrumentor().instrument(set_logging_format=True)

    FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer)


# Setting jaeger exporter
setting_jaeger(app)


origins = ["*"]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------
# Pydantic models
# -------------------------------


class FormatTimeInput(BaseModel):
    format: str = Field(
        "%Y-%m-%d %H:%M:%S", description="Python strftime format string"
    )
    timezone: str = Field(
        "UTC", description="IANA timezone name (e.g., UTC, America/New_York)"
    )


class ConvertTimeInput(BaseModel):
    timestamp: str = Field(
        ..., description="ISO 8601 formatted time string (e.g., 2024-01-01T12:00:00Z)"
    )
    from_tz: str = Field(
        ..., description="Original IANA time zone of input (e.g. UTC or Europe/Berlin)"
    )
    to_tz: str = Field(..., description="Target IANA time zone to convert to")


class ElapsedTimeInput(BaseModel):
    start: str = Field(..., description="Start timestamp in ISO 8601 format")
    end: str = Field(..., description="End timestamp in ISO 8601 format")
    units: Literal["seconds", "minutes", "hours", "days"] = Field(
        "seconds", description="Unit for elapsed time"
    )


class ParseTimestampInput(BaseModel):
    timestamp: str = Field(
        ..., description="Flexible input timestamp string (e.g., 2024-06-01 12:00 PM)"
    )
    timezone: str = Field(
        "UTC", description="Assumed timezone if none is specified in input"
    )


# -------------------------------
# Routes
# -------------------------------


@app.get("/get_current_utc_time", summary="Current UTC time")
def get_current_utc():
    """
    Returns the current time in UTC in ISO format.
    """
    return {"utc": datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()}


@app.get("/get_current_local_time", summary="Current Local Time")
def get_current_local():
    """
    Returns the current time in local timezone in ISO format.
    """
    return {"local_time": datetime.now().isoformat()}


@app.post("/format_time", summary="Format current time")
def format_current_time(data: FormatTimeInput):
    """
    Return the current time formatted for a specific timezone and format.
    """
    try:
        tz = pytz.timezone(data.timezone)
    except Exception:
        raise HTTPException(
            status_code=400, detail=f"Invalid timezone: {data.timezone}"
        )
    now = datetime.now(tz)
    try:
        return {"formatted_time": now.strftime(data.format)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid format string: {e}")


@app.post("/convert_time", summary="Convert between timezones")
def convert_time(data: ConvertTimeInput):
    """
    Convert a timestamp from one timezone to another.
    """
    try:
        from_zone = pytz.timezone(data.from_tz)
        to_zone = pytz.timezone(data.to_tz)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid timezone: {e}")

    try:
        dt = dateutil_parser.parse(data.timestamp)
        if dt.tzinfo is None:
            dt = from_zone.localize(dt)
        else:
            dt = dt.astimezone(from_zone)
        converted = dt.astimezone(to_zone)
        return {"converted_time": converted.isoformat()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid timestamp: {e}")


@app.post("/elapsed_time", summary="Time elapsed between timestamps")
def elapsed_time(data: ElapsedTimeInput):
    """
    Calculate the difference between two timestamps in chosen units.
    """
    try:
        start_dt = dateutil_parser.parse(data.start)
        end_dt = dateutil_parser.parse(data.end)
        delta = end_dt - start_dt
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid timestamps: {e}")

    seconds = delta.total_seconds()
    result = {
        "seconds": seconds,
        "minutes": seconds / 60,
        "hours": seconds / 3600,
        "days": seconds / 86400,
    }

    return {"elapsed": result[data.units], "unit": data.units}


@app.post("/parse_timestamp", summary="Parse and normalize timestamps")
def parse_timestamp(data: ParseTimestampInput):
    """
    Parse human-friendly input timestamp and return standardized UTC ISO time.
    """
    try:
        tz = pytz.timezone(data.timezone)
        dt = dateutil_parser.parse(data.timestamp)
        if dt.tzinfo is None:
            dt = tz.localize(dt)
        dt_utc = dt.astimezone(pytz.utc)
        return {"utc": dt_utc.isoformat()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse: {e}")


@app.get("/list_time_zones", summary="All valid time zones")
def list_time_zones():
    """
    Return a list of all valid IANA time zones.
    """
    return pytz.all_timezones

import httpx
from fastapi import FastAPI, Response
from opentelemetry.propagate import inject
import logging

@app.get("/chain")
async def chain(response: Response):
    headers = {}
    inject(headers)  # inject trace info to header
    logging.critical(headers)

    async with httpx.AsyncClient() as client:
        await client.get(
            "http://localhost:8000/",
            headers=headers,
        )
    async with httpx.AsyncClient() as client:
        await client.get(
            f"http://{TARGET_ONE_HOST}:8000/chain-2",
            headers=headers,
        )
    # async with httpx.AsyncClient() as client:
    #     await client.get(
    #         f"http://{TARGET_TWO_HOST}:8000/get_current_utc_time",
    #         headers=headers,
    #     )
    logging.info("Chain Finished")
    return {"path": "/chain"}

@app.get("/chain-2")
async def chain(response: Response):
    headers = {}
    inject(headers)  # inject trace info to header
    logging.critical(headers)

    async with httpx.AsyncClient() as client:
        await client.get(
            f"http://{TARGET_TWO_HOST}:8000/get_current_utc_time",
            headers=headers,
        )
    logging.info("Chain Finished")
    return {"path": "/chain"}

if __name__ == "__main__":
    # update uvicorn access logger format
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["access"][
        "fmt"
    ] = "%(asctime)s %(levelname)s [%(name)s] [%(filename)s:%(lineno)d] [trace_id=%(otelTraceID)s span_id=%(otelSpanID)s resource.service.name=%(otelServiceName)s] - %(message)s"
    uvicorn.run(app, host="0.0.0.0", port=EXPOSE_PORT, log_config=log_config)