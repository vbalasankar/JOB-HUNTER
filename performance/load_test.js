import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '10s', target: 20 }, // Ramp up to 20 virtual users
    { duration: '30s', target: 20 }, // Sustain load
    { duration: '10s', target: 0 },  // Ramp down to 0
  ],
  thresholds: {
    http_req_duration: ['p(95)<1000'], // 95% of requests should be below 1s
    http_req_failed: ['rate<0.01'],    // Error rate should be < 1%
  },
};

export default function () {
  // Test the jobs API endpoint
  const res = http.get('http://127.0.0.1:8000/api/jobs');
  
  check(res, {
    'status is 200': (r) => r.status === 200,
    'duration < 500ms': (r) => r.timings.duration < 500,
  });
  
  sleep(1);
}
