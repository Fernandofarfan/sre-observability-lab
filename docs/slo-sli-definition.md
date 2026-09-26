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

**Alerting — Multi-Window, Multi-Burn-Rate:**

Alerts consume the error budget burn rate (`burn rate = error rate / 0.005`), using the
dual-window pattern from the Google SRE workbook: a long window detects sustained burn,
a short window confirms it is still burning and cuts through noise. A spike visible in
only one window never pages.

| Alert | Burn Rate | Windows | Threshold | `for` | Severity |
|-------|-----------|---------|-----------|-------|----------|
| `ErrorBudgetBurnRate_Fast` | 14.4x | 10m **and** 1m | error rate > 7.2% | 1m | critical |
| `ErrorBudgetBurnRate_Slow` | 6x | 30m **and** 5m | error rate > 3% | 5m | warning |

> **Lab-scaled windows:** the canonical workbook pairs are 1h+5m (14.4x), 6h+30m (6x)
> and 2d+1h (3x) against a 30-day SLO. This lab scales the windows down (10m+1m and
> 30m+5m) so burn-rate alerts are observable within a demo session. The dual-window
> structure and burn-rate math are preserved; swap the windows back to canonical
> values for a production-style 30-day SLO.

**Worked example (fast burn):** at a sustained 7.2% error rate, the rolling 30-minute
99.5% objective is already mathematically unreachable for the current window — the
alert fires after the condition holds for 1 minute on both windows.

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

| Alert | Threshold | `for` | Severity |
|-------|-----------|-------|----------|
| `HighLatency_P95` | P95 > 250ms (SLO breach) | 2m | warning |
| `CriticalLatency_P99` | P99 > 1s | 2m | critical |

---

## SLO 3 — Saturation

**Threshold:** ≤ 50 concurrent in-flight requests.

| Alert | Threshold | `for` | Severity |
|-------|-----------|-------|----------|
| `HighRequestConcurrency` | total in-flight > 50 | 1m | warning |

---

## Summary Table

| SLO | SLI Metric | Threshold | Window | Error Budget | Alert | Severity |
|-----|-----------|-----------|--------|--------------|-------|----------|
| Availability | Success rate (non-5xx / total) | ≥ 99.5% | 30m | 0.5% | `ErrorBudgetBurnRate_Fast` | critical |
| Availability | Success rate (non-5xx / total) | ≥ 99.5% | 30m | 0.5% | `ErrorBudgetBurnRate_Slow` | warning |
| Latency | P95 request duration | ≤ 250ms | 5m | N/A | `HighLatency_P95` | warning |
| Latency | P99 request duration | ≤ 1s | 5m | N/A | `CriticalLatency_P99` | critical |
| Saturation | Concurrent in-flight requests | ≤ 50 | 1m | N/A | `HighRequestConcurrency` | warning |

## Alert Delivery

Firing alerts are routed by severity in Alertmanager:

- `severity=critical` → **pager** receiver → `webhook-receiver:9095/pager`
- `severity=warning` → **ticket** receiver → `webhook-receiver:9095/ticket`

The webhook receiver logs every alert (structured JSON → Loki) and exposes
`alerts_received_total{receiver, severity, status, alertname}` so delivery itself is
observable. Prometheus scrapes the receiver (job `sre-lab-webhook-receiver`), and
infrastructure alerts (`ApiDown`, `AlertmanagerDown`, `WebhookReceiverDown`,
`PromtailDown`, `LokiDown`) page when any part of this delivery pipeline dies.
