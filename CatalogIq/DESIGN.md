# CatalogIQ --- System Design

## 1. Architecture

CatalogIQ uses FastAPI, asyncio and SQLite. A job is accepted by the API
and processed in the background so the API remains responsive.

``` text
Frontend
   |
   v
FastAPI API
   |
   +--> JobService --> SQLite
   |       |
   |       +--> CacheService
   |       +--> LLMService
   |               |
   |               +--> Global asyncio Semaphore
   |               +--> Retry + Metrics + Validation
   |               |
   |               +--> MockProvider
   |               +--> GeminiProvider
   |
   +--> ProductService --> SQLite
```

### Job flow

1.  `POST /api/jobs` or `POST /api/jobs/csv` validates input and creates
    a job.
2.  Products and job items are persisted in SQLite.
3.  The API returns the job ID without waiting for enrichment.
4.  Background processing starts with `asyncio.create_task()`.
5.  Products are processed concurrently with `asyncio.gather()`.
6.  Persistent cache is checked before an LLM call.
7.  If identical content is already in flight, the request waits for the
    existing future.
8.  New LLM work passes through a global semaphore.
9.  `LLMService` applies retry, metrics and output validation.
10. Results are saved to SQLite and job progress is updated.
11. Failed products are isolated so other products continue.

### Why asyncio?

LLM calls are primarily I/O-bound. `asyncio` allows many product tasks
to exist concurrently without creating a thread for each item. A shared
`asyncio.Semaphore` limits the number of active LLM calls across jobs.

### Alternatives rejected

**Threads:** Possible for blocking SDKs, but asyncio fits the I/O-bound
workload and makes the concurrency model explicit.

**Multiprocessing:** Unnecessary because the bottleneck is external LLM
latency rather than CPU computation.

**Distributed queue:** A queue such as Redis/Celery would be appropriate
at production scale, but adds infrastructure that is unnecessary for the
assignment's single-process implementation.

------------------------------------------------------------------------

## 2. Crash Recovery

SQLite preserves completed product and job-item state across a normal
server restart. However, in-memory asyncio tasks are lost if the process
crashes.

For a 10,000-item job:

``` text
10,000 total
6,000 completed
4,000 queued/running
       |
       X crash
```

The completed results remain in SQLite. The lost in-memory tasks must be
recreated.

### Resume design

A production startup recovery flow would be:

``` text
Server starts
    |
    v
Find queued/running jobs
    |
    v
Find job_items not completed
    |
    v
Reset stale running items to queued
    |
    v
Resume remaining items
```

Completed products are skipped because their enriched result and content
key are already persisted.

A stronger production implementation would add worker IDs,
leases/heartbeats, lease expiry, idempotent state transitions and
startup recovery of stale items.

**Current limitation:** the project persists product/job state and cache
results, but does not yet implement a full startup worker that
automatically resumes an interrupted job. That is a production extension
rather than a hidden claim about the current code.

------------------------------------------------------------------------

## 3. Scale and Cost --- 1 Million Listings/Day

One million listings per day is approximately:

``` text
1,000,000 / 86,400 = 11.6 listings/second average
```

The provider's RPM/TPM limits are the important constraint.

### Reduce LLM work

First normalize:

``` text
raw_title + " " + raw_description
```

then hash it and check the persistent cache. Identical items should not
consume another LLM request.

### Batch requests

At large scale, instead of one product per request:

``` text
1 product -> 1 LLM request
```

use structured batches:

``` text
N products -> 1 LLM request -> N JSON results
```

Batch size should respect token limits and response reliability.

### Distributed rate limiting

A local semaphore is not enough when several machines are running. A
production system should use a shared rate limiter:

``` text
                 Shared Rate Limiter
                         |
          +--------------+--------------+
          |              |              |
       Worker 1       Worker 2       Worker 3
          |              |              |
          +--------------+--------------+
                         |
                         v
                    LLM Provider
```

This should enforce both concurrency and requests/tokens per minute
across all workers.

### Horizontal workers

At higher volume, replace in-process background tasks with a durable
queue:

``` text
API
 |
 v
Durable Job Queue
 |
 +--> Worker 1
 +--> Worker 2
 +--> Worker 3
 |
 v
Shared DB / Cache
 |
 v
LLM Provider
```

### Cost controls

Use persistent caching, in-flight de-duplication, batching, smaller
models where suitable, deterministic rules for simple cases, and human
review only for uncertain products.

A second provider can be used as a controlled fallback, with the same
validation pipeline applied to its output.

------------------------------------------------------------------------

## 4. API Performance --- 5 Million Products

A search such as:

``` text
GET /api/products?search=milk
```

can become slow if the database scans millions of rows.

### Indexes

Indexes should cover frequent filters and exact lookups:

``` text
sku
category
content_key
```

The current project already uses SKU as the primary key and indexes
`content_key`.

For large-scale category filtering:

``` sql
CREATE INDEX idx_products_category
ON products(category);
```

### Full-text search

For text search across millions of products, SQLite FTS5 is preferable
to repeated wildcard `LIKE` scans. It can index fields such as
`clean_title` and `raw_title`.

At larger production scale, PostgreSQL full-text search or a dedicated
search service could be considered.

### Cursor pagination

Deep offset pagination such as:

``` text
LIMIT 20 OFFSET 4000000
```

can become expensive. A cursor/keyset approach is more scalable:

``` text
GET /api/products?cursor=<last_sku>&limit=20
```

The cursor should use a stable indexed key.

### Query caching

Frequently repeated search/filter queries can be cached with keys based
on search text, category, cursor and page size. Entries should expire or
be invalidated after product updates.

------------------------------------------------------------------------

## 5. Quality, Hallucination and Human Review

A response can be valid JSON and still contain an incorrect brand or
category. Quality control therefore needs more than schema validation.

### Schema validation

The current pipeline checks:

-   valid JSON object
-   non-empty `clean_title`
-   allowed category
-   brand is string or null
-   tags are a list
-   maximum five tags
-   lowercase tag strings

### Business-rule validation

Production checks could compare LLM output against the source and
trusted reference data:

-   Is the category compatible with obvious product keywords?
-   Is the brand present in a trusted brand catalogue?
-   Did the model invent a brand absent from the source?
-   Did important quantities or product attributes change?
-   Are tags supported by the source text?

### Risk scoring

A production review score could combine signals such as:

``` text
unknown brand
category disagreement
missing required data
large title transformation
conflicting source information
low model confidence
```

High-risk products would go to human review.

### Human-in-the-loop

``` text
LLM result
    |
    v
Validation
    |
    +---- Low risk -----> Catalogue
    |
    +---- High risk ----> Human review
                              |
                     +--------+--------+
                     |                 |
                  Approve             Edit
                     |                 |
                     +--------+--------+
                              |
                              v
                         Final catalogue
```

The current frontend already supports editing and approving products. A
future version could display the quality/risk signals directly in the
review screen.

------------------------------------------------------------------------

## Design Trade-offs

  -----------------------------------------------------------------------
  Decision                Chosen approach         Reason
  ----------------------- ----------------------- -----------------------
  Async model             asyncio                 I/O-bound LLM workload

  LLM concurrency         Global semaphore        Prevent provider
                                                  overload

  Persistence             SQLite                  Simple and persistent
                                                  for assignment scale

  LLM abstraction         Provider interface      Easy Mock/Gemini
                                                  switching

  Retry                   Exponential backoff     Handle transient
                                                  failures

  Cache                   Persistent + in-flight  Avoid repeated and
                                                  simultaneous duplicate
                                                  work

  Large-scale queue       Not used currently      Single-process
                                                  assignment scope

  Search at 5M            Indexes + FTS + cursor  Avoid full scans and
                                                  deep offsets

  Human review            Existing edit/approve   Focus review on
                          UI                      uncertain products
  -----------------------------------------------------------------------

## Conclusion

The current implementation is intentionally simple enough to run locally
while demonstrating asynchronous processing, bounded LLM concurrency,
retries, validation, persistent caching, in-flight de-duplication,
failure isolation and live job progress.

For production scale, the main evolution would be a durable distributed
queue, shared rate limiting/cache infrastructure, stronger crash
recovery, and an indexed large-scale search system.
