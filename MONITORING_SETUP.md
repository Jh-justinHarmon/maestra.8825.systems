# Monitoring Setup Guide

## Prometheus Metrics Collection

The backend exposes Prometheus metrics at `/metrics`. Configure your Prometheus instance to scrape:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'maestra-backend'
    static_configs:
      - targets: ['maestra-backend-8825-systems.fly.dev:443']
    scheme: https
    metrics_path: '/metrics'
```

## Key Metrics to Monitor

### Request Volume
- `precompute_requests_total` - Total requests received
- Alert if: `rate(precompute_requests_total[5m]) == 0` (no traffic)

### Latency
- `precompute_latency_seconds` - Request latency histogram
- Alert if: `histogram_quantile(0.95, precompute_latency_seconds) > 0.8` (p95 > 800ms)
- Alert if: `histogram_quantile(0.99, precompute_latency_seconds) > 1.5` (p99 > 1.5s)

### Grounding Rate
- `precompute_grounded_total` - Successful groundings
- Calculate: `rate(precompute_grounded_total[1h]) / rate(precompute_requests_total[1h])`
- Alert if: `grounding_rate < 0.15` (< 15% grounding)

### Refusal Rate
- `precompute_refusals_total` - Refusal Contract triggers
- Calculate: `rate(precompute_refusals_total[1h]) / rate(precompute_requests_total[1h])`
- Alert if: `refusal_rate > 0.5` (> 50% refusals)

### Error Rate
- `precompute_errors_total` - Total errors
- Calculate: `rate(precompute_errors_total[5m]) / rate(precompute_requests_total[5m])`
- Alert if: `error_rate > 0.01` (> 1% errors)

### Confidence Distribution
- `precompute_confidence` - Confidence score histogram
- Monitor: `histogram_quantile(0.5, precompute_confidence)` (median confidence)
- Alert if: `median_confidence < 0.4` (low confidence)

## Grafana Dashboard

### Panel 1: Request Rate
```
rate(precompute_requests_total[5m])
```
- Type: Graph
- Y-axis: Requests/sec
- Alert: > 100 RPS

### Panel 2: Latency (P50, P95, P99)
```
histogram_quantile(0.50, precompute_latency_seconds)
histogram_quantile(0.95, precompute_latency_seconds)
histogram_quantile(0.99, precompute_latency_seconds)
```
- Type: Graph
- Y-axis: Seconds
- Alert: P95 > 0.8s

### Panel 3: Grounding Rate
```
rate(precompute_grounded_total[1h]) / rate(precompute_requests_total[1h])
```
- Type: Gauge
- Min: 0, Max: 1
- Alert: < 0.15

### Panel 4: Error Rate
```
rate(precompute_errors_total[5m]) / rate(precompute_requests_total[5m])
```
- Type: Gauge
- Min: 0, Max: 0.1
- Alert: > 0.01

### Panel 5: Confidence Distribution
```
histogram_quantile(0.50, precompute_confidence)
histogram_quantile(0.95, precompute_confidence)
```
- Type: Graph
- Y-axis: Confidence (0-1)
- Alert: Median < 0.4

## Alert Rules

### Critical Alerts (Page on-call)
```yaml
- alert: PrecomputeEndpointDown
  expr: up{job="maestra-backend"} == 0
  for: 5m
  annotations:
    summary: "Precompute endpoint down"

- alert: HighErrorRate
  expr: rate(precompute_errors_total[5m]) / rate(precompute_requests_total[5m]) > 0.05
  for: 5m
  annotations:
    summary: "Error rate > 5%"

- alert: P95LatencyHigh
  expr: histogram_quantile(0.95, precompute_latency_seconds) > 1.0
  for: 10m
  annotations:
    summary: "P95 latency > 1s"
```

### Warning Alerts (Slack notification)
```yaml
- alert: LowGroundingRate
  expr: rate(precompute_grounded_total[1h]) / rate(precompute_requests_total[1h]) < 0.15
  for: 30m
  annotations:
    summary: "Grounding rate < 15%"

- alert: LowConfidence
  expr: histogram_quantile(0.50, precompute_confidence) < 0.4
  for: 30m
  annotations:
    summary: "Median confidence < 0.4"

- alert: HighRefusalRate
  expr: rate(precompute_refusals_total[1h]) / rate(precompute_requests_total[1h]) > 0.5
  for: 30m
  annotations:
    summary: "Refusal rate > 50%"
```

## 24-Hour Baseline Monitoring

### Day 1: Establish Baseline
1. Deploy to production
2. Monitor `/metrics` endpoint
3. Record P50, P95, P99 latencies
4. Track grounding rate
5. Monitor error rate

### Metrics to Collect
- Request volume (RPS)
- Latency percentiles (P50, P95, P99)
- Grounding rate (%)
- Refusal rate (%)
- Error rate (%)
- Confidence distribution

### Expected Baseline
| Metric | Expected | Alert Threshold |
|--------|----------|-----------------|
| P50 Latency | 200ms | > 400ms |
| P95 Latency | 400ms | > 800ms |
| P99 Latency | 800ms | > 1.5s |
| Grounding Rate | 20-40% | < 15% |
| Refusal Rate | 5-15% | > 50% |
| Error Rate | < 1% | > 5% |
| Median Confidence | 0.6-0.8 | < 0.4 |

## Tuning Grounding Thresholds

### Current Behavior
- Grounding rate: ~0% (Library path not accessible in Fly.io)
- Confidence: 0.5-0.7 (moderate)
- Refusal rate: 0% (not enforcing grounding)

### Tuning Strategy

1. **Increase Library Coverage**
   - Ingest more conversation data
   - Expand 8825-library with new entries
   - Target: 1000+ indexed documents

2. **Adjust Relevance Threshold**
   - Current: 0.7 (70% similarity required)
   - Experiment: 0.5 (50% similarity)
   - Monitor: Grounding rate and accuracy

3. **Tune Confidence Calculation**
   - Current: Based on intent classification
   - Improve: Factor in context relevance
   - Target: Confidence > 0.7 when grounded

4. **Enforce Grounding Selectively**
   - High-stakes intents (code, security): Require grounding
   - Low-stakes intents (general): Allow without grounding
   - Monitor: Refusal rate and user satisfaction

### Monitoring Tuning Impact

```
Before Tuning:
- Grounding Rate: 0%
- Confidence: 0.5
- Refusal Rate: 0%

After Tuning (Target):
- Grounding Rate: 30-50%
- Confidence: 0.7+
- Refusal Rate: 5-10%
```

## Runbook: Low Grounding Rate

**Symptom:** Grounding rate < 15%

**Diagnosis:**
1. Check Library size: `ls ~/Hammer\ Consulting\ Dropbox/Justin\ Harmon/8825-Team/shared/8825-library/ | wc -l`
2. Check Context Builder logs
3. Review relevance threshold

**Solution:**
1. Ingest more data: Run UCMA conversation ingestion
2. Lower relevance threshold: Adjust from 0.7 to 0.5
3. Expand Library: Add more indexed documents
4. Monitor: Check grounding rate after 1 hour

## Runbook: High Latency

**Symptom:** P95 latency > 800ms

**Diagnosis:**
1. Check backend CPU: `flyctl status -a maestra-backend-8825-systems`
2. Check Context Builder query time
3. Review PromptGen processing time

**Solution:**
1. Scale horizontally: `flyctl scale count 2 -a maestra-backend-8825-systems`
2. Optimize Context Builder: Add caching
3. Profile PromptGen: Identify slow operations
4. Monitor: Check latency after scaling

## Runbook: High Error Rate

**Symptom:** Error rate > 5%

**Diagnosis:**
1. Check logs: `flyctl logs -a maestra-backend-8825-systems | grep error`
2. Check PromptGen import: `/health/deep`
3. Review error types

**Solution:**
1. Verify PromptGen: Check `/health/deep`
2. Review error logs for patterns
3. Rollback if needed
4. Monitor: Check error rate after fix

## Success Criteria

✅ **Monitoring Established**
- Prometheus scraping metrics
- Grafana dashboard displaying data
- Alert rules configured and tested

✅ **Baseline Established**
- 24 hours of metrics collected
- P50, P95, P99 latencies recorded
- Grounding rate and error rate tracked

✅ **Thresholds Tuned**
- Relevance threshold optimized
- Confidence calculation improved
- Grounding rate > 20%

✅ **Alerts Active**
- Critical alerts page on-call
- Warning alerts notify team
- Runbooks available for common issues
