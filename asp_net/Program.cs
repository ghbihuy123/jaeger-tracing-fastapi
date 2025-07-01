using Microsoft.OpenApi.Models;
using OpenTelemetry.Trace;
using OpenTelemetry.Resources;
using OpenTelemetry.Exporter;
using System.Diagnostics;

var builder = WebApplication.CreateBuilder(args);

// === Swagger ===
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(c =>
{
    c.SwaggerDoc("v1", new OpenApiInfo { Title = "My API", Version = "v1" });
});

// === OpenTelemetry Tracing ===
builder.Services.AddOpenTelemetry()
    .WithTracing(tracing =>
    {
        tracing
            .AddAspNetCoreInstrumentation()
            .AddHttpClientInstrumentation()
            .SetResourceBuilder(ResourceBuilder.CreateDefault()
                .AddService("asp-app"))
            .AddOtlpExporter(opt =>
            {
                opt.Protocol = OtlpExportProtocol.HttpProtobuf;
                opt.Endpoint = new Uri("http://otel-collector:4318/v1/traces");
            });
    });

// === Named HttpClient that calls server:8000 ===
builder.Services.AddHttpClient("chainApi", client =>
{
    client.BaseAddress = new Uri("http://server:8000/");
});

var app = builder.Build();

// === Middleware: log TraceId and SpanId for all requests ===
app.Use(async (context, next) =>
{
    var activity = Activity.Current;
    var traceId = activity?.TraceId.ToString() ?? "no-trace";
    var spanId = activity?.SpanId.ToString() ?? "no-span";

    var logger = context.RequestServices.GetRequiredService<ILogger<Program>>();
    logger.LogInformation("📥 {Method} {Path} | TraceId: {TraceId} | SpanId: {SpanId}",
        context.Request.Method,
        context.Request.Path,
        traceId,
        spanId);

    await next();
});

// === Swagger UI ===
app.UseSwagger();
app.UseSwaggerUI();

// === Simple endpoint ===
app.MapGet("/hello", () => "Hello from ASP.NET 8!");

// === Traced endpoint that calls external API ===
app.MapGet("/call_chain", async (IHttpClientFactory httpClientFactory, ILogger<Program> logger) =>
{
    var activity = Activity.Current;
    var traceId = activity?.TraceId.ToString() ?? "no-trace";
    var spanId = activity?.SpanId.ToString() ?? "no-span";
    logger.LogInformation("➡️ Calling downstream /chain | TraceId: {TraceId} | SpanId: {SpanId}", traceId, spanId);

    var client = httpClientFactory.CreateClient("chainApi");
    var response = await client.GetAsync("chain");
    var content = await response.Content.ReadAsStringAsync();

    return Results.Content(content, "application/json");
})
.WithName("CallChain")
.WithDescription("Calls external service at server:8000/chain")
.Produces<string>(StatusCodes.Status200OK, "application/json")
.WithOpenApi();

app.Run();
