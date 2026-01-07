import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const latency = new Trend('latency');
const groundedCount = new Counter('grounded_requests');
const refusalCount = new Counter('refusal_requests');

export const options = {
  stages: [
    { duration: '2m', target: 10 },   // Ramp up to 10 RPS
    { duration: '5m', target: 50 },   // Ramp up to 50 RPS
    { duration: '10m', target: 50 },  // Stay at 50 RPS
    { duration: '2m', target: 0 },    // Ramp down
  ],
  thresholds: {
    'http_req_duration': ['p(95)<800', 'p(99)<1500'],
    'errors': ['rate<0.01'],
  },
};

const BASE_URL = 'https://maestra-backend-8825-systems.fly.dev';

// Test queries with varying complexity
const testQueries = [
  'implement authentication system',
  'library integration context',
  'optimize database queries',
  'fix memory leak in production',
  'design API for microservices',
  'implement caching strategy',
  'setup CI/CD pipeline',
  'refactor legacy code',
  'add unit tests',
  'deploy to kubernetes',
];

export default function () {
  // Random query from test set
  const query = testQueries[Math.floor(Math.random() * testQueries.length)];
  
  const payload = JSON.stringify({
    text: query,
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
    timeout: '10s',
  };

  // Make request
  const startTime = new Date();
  const res = http.post(`${BASE_URL}/api/precompute`, payload, params);
  const duration = new Date() - startTime;

  // Record latency
  latency.add(duration);

  // Check response
  const success = check(res, {
    'status is 200': (r) => r.status === 200,
    'has optimized_prompt': (r) => r.json('optimized_prompt') !== undefined,
    'has confidence': (r) => r.json('confidence') !== undefined,
    'has intent': (r) => r.json('intent') !== undefined,
    'confidence > 0': (r) => r.json('confidence') > 0,
  });

  if (!success) {
    errorRate.add(1);
  } else {
    errorRate.add(0);
    
    // Track grounding and refusal
    const grounded = res.json('grounded');
    const intent = res.json('intent');
    
    if (grounded) {
      groundedCount.add(1);
    }
    
    if (intent === 'refusal') {
      refusalCount.add(1);
    }
  }

  // Small delay between requests
  sleep(0.1);
}

export function handleSummary(data) {
  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
  };
}

function textSummary(data, options) {
  const { indent = '', enableColors = false } = options;
  
  let summary = '\n=== Load Test Summary ===\n';
  
  if (data.metrics) {
    const metrics = data.metrics;
    
    if (metrics.latency) {
      const trend = metrics.latency.values;
      summary += `\nLatency:\n`;
      summary += `${indent}P50: ${trend.p50 || 'N/A'}ms\n`;
      summary += `${indent}P95: ${trend.p95 || 'N/A'}ms\n`;
      summary += `${indent}P99: ${trend.p99 || 'N/A'}ms\n`;
    }
    
    if (metrics.errors) {
      summary += `\nError Rate: ${(metrics.errors.value * 100).toFixed(2)}%\n`;
    }
    
    if (metrics.grounded_requests) {
      summary += `Grounded Requests: ${metrics.grounded_requests.value}\n`;
    }
    
    if (metrics.refusal_requests) {
      summary += `Refusal Requests: ${metrics.refusal_requests.value}\n`;
    }
  }
  
  summary += '\n=== End Summary ===\n';
  return summary;
}
