# OpenTelemetry Example: FastAPI & ASP.NET with Jaeger

## Overview

This project demonstrates distributed tracing with [OpenTelemetry](https://opentelemetry.io/) in both Python (FastAPI) and .NET (ASP.NET Core), sending traces to [Jaeger](https://www.jaegertracing.io/) for visualization. The setup is containerized using Docker Compose and includes:
- **FastAPI**: Python web application instrumented with OpenTelemetry.
- **ASP.NET Core**: .NET web application instrumented with OpenTelemetry.
- **Jaeger**: Trace backend for collecting and visualizing distributed traces.
- **Grafana**: Visualization and monitoring.
- **Prometheus, Loki, Otel Collector**: For metrics/logs aggregation and collection.

## Features

- Distributed tracing for both FastAPI (Python) and ASP.NET (.NET).
- OpenTelemetry exporter sends traces to Jaeger.
- Ready-to-use Docker Compose for local development and testing.
- Includes configuration for Prometheus and Grafana dashboards.

## Project Structure

```
asp_net/             # ASP.NET Core app (.NET)
  ├── appsettings.json
  ├── Dockerfile
  └── Program.cs
fastapi/             # FastAPI app (Python)
  ├── main.py
  ├── utils.py
  ├── Dockerfile
  ├── requirements.txt
docker/
  ├── etc/
  │   ├── collector/
  │   ├── loki/
  │   └── prometheus/
  └── services/
      ├── aspnet.yml
      ├── fastapi.yml
      ├── grafana.yml
      ├── jaeger.yml
      ├── otel.yml
      └── compose.yml
```

## Getting Started

### Prerequisites

- [Docker](https://www.docker.com/get-started)
- [Docker Compose](https://docs.docker.com/compose/)

### Quick Start

1. **Clone the repository:**

   ```bash
   git clone <your-repo-url>
   cd <repo>
   ```

2. **Start all services:**

   ```bash
   cd docker/services
   docker compose -f compose.yml up --build
   ```

   This will start:
   - FastAPI backend
   - ASP.NET backend
   - Jaeger
   - Grafana
   - Prometheus, Loki, Otel Collector

3. **Access the services:**
   - **FastAPI**: [http://localhost:8000](http://localhost:8000)
   - **ASP.NET**: [http://localhost:5000](http://localhost:5000)
   - **Jaeger UI**: [http://localhost:16686](http://localhost:16686)

## OpenTelemetry Integration

### FastAPI (Python)

- Uses `opentelemetry-instrumentation-fastapi` and `opentelemetry-exporter-otlp`.
- Traces are exported via the OTLP protocol to the Otel Collector, then to Jaeger.

**Example snippet (fastapi/main.py):**
```python
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
# ... more setup ...
FastAPIInstrumentor.instrument_app(app)
```

### ASP.NET Core (.NET)

- Uses `OpenTelemetry` NuGet packages.
- Traces are exported via the OTLP exporter to the Otel Collector, then to Jaeger.

**Example snippet (asp_net/Program.cs):**
```csharp
builder.Services.AddOpenTelemetryTracing(tracerProviderBuilder =>
{
    tracerProviderBuilder
        .AddAspNetCoreInstrumentation()
        .AddOtlpExporter();
});
```

## Configuration

- **Jaeger**: `/docker/services/jaeger.yml`
- **Otel Collector**: `/docker/services/otel.yml`
- **Prometheus**: `/docker/etc/prometheus/`
- **Grafana**: `/docker/services/grafana.yml`

Update endpoints and credentials as needed in the respective files.

## Observability Workflow

1. **Applications** (FastAPI, ASP.NET) emit trace data using OpenTelemetry SDKs.
2. **Otel Collector** receives and processes trace data.
3. **Jaeger** ingests and visualizes traces.
4. **Grafana** can be connected to Jaeger/Prometheus for dashboards.

## Useful Links

- [OpenTelemetry Docs](https://opentelemetry.io/docs/)
- [Jaeger Docs](https://www.jaegertracing.io/docs/)
- [Grafana Docs](https://grafana.com/docs/)
- [Prometheus Docs](https://prometheus.io/docs/)