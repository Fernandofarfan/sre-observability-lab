# Runbook: Infrastructure Down

## Alert Information

| Field | Value |
|-------|-------|
| **Alert Names** | `ApiDown`, `AlertmanagerDown`, `WebhookReceiverDown`, `PromtailDown`, `LokiDown` |
| **Severity** | critical (`ApiDown`, `AlertmanagerDown`) / warning (`WebhookReceiverDown`, `PromtailDown`, `LokiDown`) |
| **SLO** | N/A — monitoring pipeline availability |

## Description

These alerts fire when Prometheus cannot scrape one of the monitored targets
(`up == 0`) for the configured `for` duration:

| Alert | Target | Impact |
|-------|--------|--------|
| `ApiDown` | `api:8000` | The demo API is unreachable — no traffic, metrics, traces or logs |
| `AlertmanagerDown` | `alertmanager:9093` | Alerts are not routed or delivered — nobody is notified |
| `WebhookReceiverDown` | `webhook-receiver:9095` | Alert webhook delivery is broken and `alerts_received_total` goes stale |
| `PromtailDown` | `promtail:9080` | Container logs stop flowing into Loki |
| `LokiDown` | `loki:3100` | Log ingestion and Grafana log queries fail |

## Impact

- `ApiDown` is a user-facing outage for the simulated service.
- `AlertmanagerDown` silently breaks the alerting pipeline: alerts may still fire
  in Prometheus, but they are never routed to the pager/ticket receivers.
- `PromtailDown` / `LokiDown` degrade incident investigation: the runbooks' log
  steps ("Review Application Logs") will return no results.

## Investigation Steps

1. **Check container state**
   ```bash
   docker compose ps
   docker compose ps --format '{{.Name}} {{.Status}}'
   ```

2. **Inspect the failing service logs**
   ```bash
   docker compose logs <service> --tail 100
   ```

3. **Confirm the scrape failure in Prometheus**
   - Open `http://localhost:9090/targets` and find the failing job
   - Or query `up == 0` in the Prometheus UI to list every down target

4. **Check the pipeline dashboard**
   - Open Grafana → "SRE Observability Lab - Alert Delivery"
   - "Targets Down" and "Scrape Targets (up)" show which job stopped reporting

5. **Rule out resource exhaustion**
   ```bash
   docker stats --no-stream
   ```

## Remediation Steps

1. **Restart the affected container**
   ```bash
   docker compose restart <service>
   ```

2. **If it exits again immediately, check config validity**
   ```bash
   docker compose logs <service> --tail 200
   docker compose config -q
   ```

3. **If the API is down, redeploy the full stack**
   ```bash
   docker compose up -d --build --wait
   ```

4. **Verify recovery**
   ```bash
   docker compose ps
   curl -fsS http://localhost:9090/api/v1/query --data-urlencode 'query=up == 0'
   ```

## Escalation

Contact the on-call lead if a critical target (`ApiDown` / `AlertmanagerDown`)
stays down for more than 15 minutes, or if restarts do not restore the target.
