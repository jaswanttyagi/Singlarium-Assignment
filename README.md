# CatalogIQ

An LLM-powered product catalogue enrichment system built for the
Singularium Technologies SWE Internship Assignment.

CatalogIQ takes messy product listings, processes them asynchronously,
enriches them using an LLM, validates the result, avoids repeated work
through persistent caching and in-flight de-duplication, and exposes the
processed catalogue through a REST API and a plain HTML/CSS/JavaScript
frontend.

## Features

-   FastAPI backend with asynchronous background job processing
-   Parallel product processing with a global LLM concurrency limit
-   Mock LLM provider for local and automated testing
-   Google Gemini provider for real LLM enrichment
-   Provider-independent LLM service architecture
-   Retry with exponential backoff
-   LLM output validation
-   Persistent SQLite cache
-   In-flight de-duplication for simultaneous duplicate products
-   Job progress tracking and metrics
-   CSV upload
-   Product search and category filtering
-   Pagination
-   Product review, edit and approve workflow
-   Automated tests for retry, concurrency and de-duplication
-   Persistent data storage in SQLite

## Technology Stack

  Layer              Technology
  ------------------ ------------------------------
  Backend            Python, FastAPI
  Frontend           HTML, CSS, JavaScript
  Database           SQLite
  LLM                Mock Provider, Google Gemini
  Async Processing   Python asyncio
  Testing            pytest, pytest-asyncio
  Configuration      python-dotenv

## Architecture

``` text
Frontend
   |
   v
FastAPI Routes
   |
   +---- JobService --------> SQLite
   |       |
   |       +--> CacheService
   |       +--> LLMService
   |               |
   |               +--> ConcurrencyLimiter
   |               +--> Retry
   |               +--> Validation
   |               |
   |               +--> MockProvider
   |               +--> GeminiProvider
   |
   +---- ProductService ----> SQLite
```

### Product Processing Flow

``` text
Upload products
      |
      v
Create background job
      |
      v
Process products concurrently
      |
      v
Normalize content and create SHA-256 content key
      |
      +---- Persistent cache hit ----> reuse result
      |
      +---- In-flight duplicate ---> wait for existing result
      |
      +---- New content -----------> concurrency limit
                                      |
                                      v
                                  LLM request
                                      |
                                      v
                                    Retry
                                      |
                                      v
                                  Validate
                                      |
                                      v
                                Save to SQLite
                                      |
                                      v
                              Update job progress
```

## Project Structure

``` text
CatalogIq/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── routes/
│   │   ├── jobs.py
│   │   ├── products.py
│   │   ├── health.py
│   │   └── metrics_route.py
│   ├── services/
│   │   ├── job_service.py
│   │   ├── product_service.py
│   │   ├── llm_services.py
│   │   ├── cache_service.py
│   │   ├── retry_service.py
│   │   ├── concurrency.py
│   │   ├── metrics.py
│   │   └── validation.py
│   ├── providers/
│   │   ├── base.py
│   │   ├── mock_provider.py
│   │   └── gemini_provider.py
│   └── schemas/
│       ├── job.py
│       └── product.py
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── tests/
│   ├── test_retry.py
│   ├── test_concurrency.py
│   └── test_deduplication.py
├── data/
│   └── sample.csv
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
├── DESIGN.md
├── run.py
└── catalogiq.db
```

## Getting Started

### 1. Clone the repository

``` bash
git clone <your-repository-url>
cd CatalogIq
```

### 2. Create and activate a virtual environment

Windows:

``` bash
python -m venv venv
venv\Scripts\activate
```

Linux/macOS:

``` bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

``` bash
pip install -r requirements.txt
```

For tests:

``` bash
pip install pytest pytest-asyncio
```

### 4. Configure `.env`

``` env
LLM_PROVIDER=mock
LLM_CONCURRENCY=5
MOCK_LATENCY_MS=200
MOCK_FAILURE_RATE=0.1

GEMINI_API_KEY=YOUR_ACTUAL_KEY
GEMINI_MODEL=gemini-2.5-flash
```

For local testing, use:

``` env
LLM_PROVIDER=mock
```

For real Gemini enrichment:

``` env
LLM_PROVIDER=gemini
```

Never commit the real API key.

### 5. Start the application

``` bash
python run.py
```

Application:

``` text
http://127.0.0.1:8000
```

Frontend:

``` text
http://127.0.0.1:8000/frontend/index.html
```

FastAPI docs:

``` text
http://127.0.0.1:8000/docs
```

## API

### Health

``` http
GET /api/health
```

Response:

``` json
{
  "status": "ok"
}
```

### Metrics

``` http
GET /api/metrics
```

Example:

``` json
{
  "total_llm_calls": 10,
  "llm_errors": 1,
  "concurrent_llm_calls": 0,
  "max_concurrent_llm_calls": 5
}
```

### Create JSON Job

``` http
POST /api/jobs
Content-Type: application/json
```

Example:

``` json
{
  "products": [
    {
      "sku": "SKU001",
      "raw_title": "AMUL butter 500G pck of 2",
      "raw_description": "Pasteurized table butter"
    }
  ]
}
```

The endpoint returns a job ID and processing continues in the
background.

### Create CSV Job

``` http
POST /api/jobs/csv
Content-Type: multipart/form-data
```

Required CSV columns:

``` text
sku,raw_title,raw_description
```

Example:

``` csv
sku,raw_title,raw_description
CSV001,Amul Toned Milk 1L,Fresh toned milk
CSV002,Lays Classic Salted Chips,Potato chips with salted flavor
```

### Get Job Status

``` http
GET /api/jobs/{job_id}
```

Example:

``` json
{
  "id": "job-id",
  "status": "completed",
  "total": 10,
  "done": 10,
  "failed": 0,
  "cache_hits": 1
}
```

### List Products

``` http
GET /api/products
```

Supported query parameters:

``` text
page
limit
category
search
```

Example:

``` text
GET /api/products?page=1&limit=20&category=Electronics&search=charger
```

### Get Product

``` http
GET /api/products/{sku}
```

### Update / Approve Product

``` http
PATCH /api/products/{sku}
Content-Type: application/json
```

Example:

``` json
{
  "clean_title": "Samsung Fast USB Charger",
  "category": "Electronics",
  "tags": ["charger", "usb", "fast-charging"]
}
```

A successful update marks the product as approved.

## LLM Providers

The application uses a provider-independent `LLMService`.

Provider selection is controlled through:

``` env
LLM_PROVIDER=mock
```

or:

``` env
LLM_PROVIDER=gemini
```

### Mock Provider

The built-in mock provider allows testing without API cost or external
network dependency.

It supports configurable latency and simulated failures:

``` env
MOCK_LATENCY_MS=200
MOCK_FAILURE_RATE=0.1
```

### Gemini Provider

The Gemini provider uses the Google GenAI SDK and requests structured
JSON containing:

``` json
{
  "clean_title": "string",
  "category": "string",
  "brand": "string or null",
  "tags": ["string"]
}
```

The response is validated before it is stored.

## Reliability and Performance

### Global Concurrency Limit

Products are processed concurrently using `asyncio`, while LLM calls are
protected by a global semaphore.

``` env
LLM_CONCURRENCY=5
```

This prevents more than the configured number of LLM calls from running
simultaneously.

### Retry

Failed LLM operations are retried up to three additional times using
exponential backoff:

``` text
0.2s -> 0.4s -> 0.8s
```

After the final failed attempt, the product is marked as failed and
other products continue processing.

### Persistent Cache

The cache key is generated from:

``` text
raw_title + " " + raw_description
```

after:

-   lowercasing
-   collapsing whitespace
-   trimming

The normalized content is hashed with SHA-256.

Previously enriched content can therefore be reused without another LLM
call.

### In-Flight De-duplication

Persistent caching does not solve simultaneous duplicate requests.
CatalogIQ therefore keeps an in-memory in-flight map.

If one request is already processing a content key, another request
waits for the same future instead of making a second LLM call.

### Validation

LLM output is validated before persistence:

-   JSON object is required
-   `clean_title` must be non-empty
-   category must be from the allowed list
-   brand must be a string or null
-   tags must be a list
-   maximum five tags
-   tags must be lowercase strings

## Testing

Run all automated tests:

``` bash
python -m pytest tests -v
```

Current tests:

``` text
test_retry_succeeds_after_failures
test_retry_fails_after_max_retries
test_concurrency_limit
test_in_flight_deduplication
```

Current result:

``` text
4 passed
```

## Frontend

The frontend uses plain HTML, CSS and JavaScript.

It supports:

-   API health status
-   CSV upload
-   live job progress
-   one-second progress polling
-   product listing
-   search with debounce
-   category filtering
-   pagination
-   product editing
-   product approval
-   failure visibility

Open:

``` text
http://127.0.0.1:8000/frontend/index.html
```

## Sample Data

A sample CSV is included at:

``` text
data/sample.csv
```

It can be uploaded directly from the frontend.

## Key Design Decisions

### SQLite

SQLite provides persistent storage without requiring an external
database server. It is suitable for the assignment implementation and
keeps local setup simple.

### asyncio

The workload is primarily network-bound LLM processing. Async tasks
allow products to be processed concurrently while the semaphore controls
LLM pressure.

### Provider abstraction

The LLM provider is separated from the service layer so the same
processing pipeline works with both the mock provider and Gemini.

### Persistent cache + in-flight cache

These solve two different problems:

-   Persistent cache prevents repeated work across jobs and restarts.
-   In-flight cache prevents duplicate LLM calls when identical products
    arrive simultaneously.

## Production Considerations

For a production-scale deployment, the architecture could be extended
with:

-   a distributed job queue
-   distributed caching
-   multiple worker processes
-   stronger crash recovery and job leasing
-   database migrations
-   connection pooling
-   structured logging and tracing
-   provider-specific rate-limit handling
-   database partitioning/sharding for very large catalogues
-   authentication and authorization
-   additional integration and load tests

Detailed architecture and scaling considerations are documented in
`DESIGN.md`.

## Security

-   Store API keys in `.env`.
-   Never commit `.env`.
-   Keep `.env.example` free of real secrets.
-   Validate LLM responses before persistence.
-   Validate uploaded CSV structure and required fields.

## Assignment

This project was developed for the Singularium Technologies Software
Engineering Internship assignment.
