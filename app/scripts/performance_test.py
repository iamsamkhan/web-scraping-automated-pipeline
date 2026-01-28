#!/usr/bin/env python3
"""
Performance testing script
"""

import requests
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import sys

def test_endpoint_performance(url: str, endpoint: str, num_requests: int = 100) -> Dict:
    """Test endpoint performance"""
    times = []
    errors = 0
    
    for i in range(num_requests):
        start_time = time.time()
        try:
            response = requests.get(f"{url}/{endpoint}", timeout=10)
            if response.status_code != 200:
                errors += 1
        except Exception:
            errors += 1
        finally:
            end_time = time.time()
            times.append((end_time - start_time) * 1000)  # Convert to ms
    
    if times:
        return {
            "endpoint": endpoint,
            "requests": num_requests,
            "errors": errors,
            "avg_time": statistics.mean(times),
            "min_time": min(times),
            "max_time": max(times),
            "p95": statistics.quantiles(times, n=20)[18],  # 95th percentile
            "p99": statistics.quantiles(times, n=100)[98],  # 99th percentile
        }
    return None

def run_load_test(url: str, concurrent_users: int = 10, duration: int = 60) -> Dict:
    """Run load test with concurrent users"""
    results = []
    
    def worker(user_id: int):
        start_time = time.time()
        requests_made = 0
        
        while time.time() - start_time < duration:
            try:
                # Alternate between endpoints
                if requests_made % 3 == 0:
                    endpoint = "/health"
                elif requests_made % 3 == 1:
                    endpoint = "/api/v1/students"
                else:
                    endpoint = "/api/v1/universities"
                
                response = requests.get(f"{url}{endpoint}", timeout=5)
                requests_made += 1
                
            except Exception:
                pass
        
        return requests_made
    
    with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
        futures = [executor.submit(worker, i) for i in range(concurrent_users)]
        total_requests = sum(f.result() for f in as_completed(futures))
    
    return {
        "concurrent_users": concurrent_users,
        "duration_seconds": duration,
        "total_requests": total_requests,
        "requests_per_second": total_requests / duration,
        "requests_per_user_per_second": total_requests / duration / concurrent_users
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Performance testing")
    parser.add_argument("--url", required=True, help="Base URL to test")
    parser.add_argument("--concurrent", type=int, default=10, help="Number of concurrent users")
    parser.add_argument("--duration", type=int, default=60, help="Test duration in seconds")
    
    args = parser.parse_args()
    
    print(f"Running performance test for: {args.url}")
    print(f"Concurrent users: {args.concurrent}")
    print(f"Duration: {args.duration} seconds")
    print("=" * 60)
    
    # Test individual endpoints
    endpoints = ["/health", "/api/v1/students", "/api/v1/universities"]
    
    for endpoint in endpoints:
        print(f"\nTesting {endpoint}:")
        result = test_endpoint_performance(args.url, endpoint, 50)
        if result:
            print(f"  Requests: {result['requests']}")
            print(f"  Errors: {result['errors']}")
            print(f"  Avg response time: {result['avg_time']:.2f} ms")
            print(f"  Min: {result['min_time']:.2f} ms")
            print(f"  Max: {result['max_time']:.2f} ms")
            print(f"  P95: {result['p95']:.2f} ms")
            print(f"  P99: {result['p99']:.2f} ms")
    
    # Run load test
    print(f"\nRunning load test ({args.concurrent} users, {args.duration}s):")
    load_result = run_load_test(args.url, args.concurrent, args.duration)
    
    print(f"  Total requests: {load_result['total_requests']}")
    print(f"  Requests per second: {load_result['requests_per_second']:.2f}")
    print(f"  Requests per user per second: {load_result['requests_per_user_per_second']:.2f}")
    
    # Determine if performance is acceptable
    if load_result['requests_per_second'] > 50:
        print("\n✅ Performance test passed!")
        sys.exit(0)
    else:
        print("\n❌ Performance test failed - throughput too low!")
        sys.exit(1)