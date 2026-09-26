# Runbook: High Error Rate

## Alert Information

| Field | Value |
|-------|-------|
| **Alert Name** | `ErrorBudgetBurnRate_Fast` / `ErrorBudgetBurnRate_Slow` |
| **Severity** | critical / warning |
| **SLO** | Availability (99.5%) |

## Description

These alerts fire on **error budget burn rate** (not static thresholds):
- **Critical (`ErrorBudgetBurnRate_Fast`):** error rate > 7.2% (14.4x burn of the 0.5% budget) sustained on both the 10-minute and 1-minute windows.
- **Warning (`ErrorBudgetBurnRate_Slow`):** error rate > 3% (6x burn) sustained on both the 30-minute and 5-minute windows.

The dual-window condition means a brief single-window spike will not alert; both the long and short window must be over budget simultaneously.

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
   Or query the same logs in Grafana (Explore → Loki datasource, `{service="api"}`).

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

5. **Verify Alert Delivery**
   ```bash
   curl -sL http://localhost:9095/metrics | grep alerts_received_total
   docker compose logs webhook-receiver --tail 50
   ```

## Remediation Steps

1. **If Chaos Engineering is Active:**
   ```bash
   curl -X POST http://localhost:8000/chaos/reset -H "X-Chaos-Token: $CHAOS_TOKEN"
   ```
   (The header is ignored when `CHAOS_TOKEN` is unset; required when it is configured.)

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
