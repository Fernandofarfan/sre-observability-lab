# Runbook: High Error Rate

## Alert Information

| Field | Value |
|-------|-------|
| **Alert Name** | `HighErrorRate_BurnRate_1h` / `CriticalErrorRate_BurnRate_5m` |
| **Severity** | warning / critical |
| **SLO** | Availability (99.5%) |

## Description

This alert fires when the HTTP 5xx error rate exceeds the defined threshold:
- **Warning:** Error rate > 2% sustained over a 1-hour window.
- **Critical:** Error rate > 10% sustained over a 5-minute window.

This indicates the service is consuming its Error Budget at an unsustainable rate and may breach its availability SLO.

## Impact

- Users experience failed requests when attempting to create or retrieve orders.
- Downstream integrations may receive incomplete or failed responses.
- Extended outage erodes the monthly Error Budget, risking SLO breach.

## Investigation Steps

1. **Check Grafana Dashboard**
   - Open Grafana at `http://localhost:3000`
   - Navigate to the "SRE Observability Lab — Golden Signals" dashboard
   - Examine the "Error Rate Over Time" panel to understand when the spike began

2. **Review Application Logs**
   ```bash
   docker compose logs api --tail 100
   ```
   Look for stack traces, exception messages, or error patterns.

3. **Check for Active Chaos Injection**
   ```bash
   curl http://localhost:8000/chaos/status
   ```
   If chaos injection is active, this may be the expected cause.

4. **Inspect Traces in Jaeger**
   - Open Jaeger at `http://localhost:16686`
   - Select the `sre-observability-lab` service
   - Filter by operation name and look for error tags on spans
   - Identify which endpoint is failing and what the root cause error is

## Remediation Steps

1. **If Chaos Engineering is Active:**
   ```bash
   curl -X POST http://localhost:8000/chaos/reset
   ```

2. **If a Bug is Identified:**
   - Identify the failing endpoint from Jaeger traces
   - Review the relevant service code for the error
   - Deploy a fix and monitor the error rate for recovery

3. **If Saturation is the Cause:**
   - Check the "Concurrent Requests Over Time" panel in Grafana
   - Scale the API horizontally or increase resource limits
   - Review `http_requests_in_progress` metric

## Escalation

Contact the on-call lead if the issue is not resolved within 15 minutes or if the critical alert fires repeatedly after remediation attempts.
