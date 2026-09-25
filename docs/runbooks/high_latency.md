# Runbook: High Latency

## Alert Information

| Field | Value |
|-------|-------|
| **Alert Name** | `HighLatency_P95` / `CriticalLatency_P99` |
| **Severity** | warning / critical |
| **SLO** | Latency (P95 ≤ 250ms) |

## Description

This alert fires when request latency exceeds the defined threshold:
- **Warning:** P95 latency > 500ms sustained for 5 minutes.
- **Critical:** P99 latency > 1 second sustained for 2 minutes.

This indicates degraded performance affecting user experience, possibly due to slow downstream calls, resource contention, or artificial latency injection.

## Impact

- Users experience slow response times when interacting with the API.
- Request queues build up, increasing concurrent in-flight requests.
- Prolonged high latency may trigger cascading failures in dependent systems.

## Investigation Steps

1. **Check Grafana Dashboard**
   - Open Grafana at `http://localhost:3000`
   - Navigate to the "SRE Observability Lab — Golden Signals" dashboard
   - Examine the "Request Duration Percentiles" panel to identify which percentile is elevated
   - Check the "Concurrent Requests Over Time" panel for saturation

2. **Check for Active Latency Injection**
   ```bash
   curl http://localhost:8000/chaos/status
   ```
   If `latency.enabled` is `true`, the high latency is intentionally injected.

3. **Search for Slow Traces in Jaeger**
   - Open Jaeger at `http://localhost:16686`
   - Select the `sre-observability-lab` service
   - Sort traces by duration (longest first)
   - Examine the waterfall to identify which span is slow (e.g., `payment.process`)

4. **Review Application Logs**
   ```bash
   docker compose logs api --tail 100
   ```
   Look for timeout errors or slow operation warnings.

## Remediation Steps

1. **If Latency Injection is Active:**
   ```bash
   curl -X POST http://localhost:8000/chaos/reset
   ```

2. **If a Specific Span is Slow:**
   - Identify the slow span from Jaeger traces
   - Check if the downstream dependency (e.g., payment gateway simulation) is degraded
   - Review the `payment_service.process()` function for unexpected delays

3. **If Saturation is the Cause:**
   - Check `http_requests_in_progress` in Grafana
   - Reduce traffic using the traffic generator or scale the API
   - Review system resource usage (CPU, memory) via `docker stats`

## Escalation

Contact the on-call lead if the issue persists for more than 15 minutes or if the critical P99 alert fires after remediation attempts.
