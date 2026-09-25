# SLI/SLO Definition

## Overview

This document defines the Service Level Indicators (SLIs) and Service Level Objectives (SLOs) for the SRE Observability Lab, following Google SRE best practices.

---

## SLO 1 — Availability

**Objective:** 99.5% of HTTP requests must complete successfully (status codes 2xx or 3xx).

**Window:** Rolling 30-minute window.

**SLI (PromQL):**

```promql
sum(rate(http_requests_total{status_code!~"5.."}[30m]))
/
sum(rate(http_requests_total[30m]))
```

**Error Budget:** 0.5% of total requests. In a 30-minute window with ~1,800 requests, this allows approximately 9 failed requests before the budget is exhausted.

**Associated Alert:**

| Alert | Threshold | Duration | Severity |
|-------|-----------|----------|----------|
| `HighErrorRate_BurnRate_1h` | Error rate > 2% over 1h | 5m | warning |
| `CriticalErrorRate_BurnRate_5m` | Error rate > 10% over 5m | 2m | critical |

---

## SLO 2 — Latency

**Objective:** 95% of HTTP requests must complete in under 250 milliseconds.

**Window:** Rolling 5-minute window.

**SLI (PromQL):**

```promql
histogram_quantile(0.95,
  sum(rate(http_request_duration_seconds_bucket[5m])) by (le)
)
```

**Threshold:** P95 ≤ 0.25 seconds (250ms).

**Associated Alert:**

| Alert | Threshold | Duration | Severity |
|-------|-----------|----------|----------|
| `HighLatency_P95` | P95 > 500ms for 5m | 5m | warning |
| `CriticalLatency_P99` | P99 > 1s for 2m | 2m | critical |

---

## Summary Table

| SLO | SLI Metric | Threshold | Window | Error Budget | Alert | Severity |
|-----|-----------|-----------|--------|--------------|-------|----------|
| Availability | Success rate (non-5xx / total) | ≥ 99.5% | 30m | 0.5% | `HighErrorRate_BurnRate_1h` | warning |
| Availability | Success rate (non-5xx / total) | ≥ 90% | 5m | 10% | `CriticalErrorRate_BurnRate_5m` | critical |
| Latency | P95 request duration | ≤ 250ms | 5m | N/A | `HighLatency_P95` | warning |
| Latency | P99 request duration | ≤ 1s | 5m | N/A | `CriticalLatency_P99` | critical |
| Saturation | Concurrent in-flight requests | ≤ 50 | 1m | N/A | `HighRequestConcurrency` | warning |
