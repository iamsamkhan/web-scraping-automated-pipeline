#!/usr/bin/env python3
"""
Monitor Blue-Green Deployment Metrics
"""

import argparse
import time
import json
import requests
from datetime import datetime
from typing import Dict, List
from dataclasses import dataclass
from prometheus_api_client import PrometheusConnect

@dataclass
class DeploymentMetrics:
    color: str
    error_rate: float
    response_time_p95: float
    cpu_usage: float
    memory_usage: float
    request_count: int
    success_rate: float
    timestamp: datetime

class BlueGreenMonitor:
    def __init__(self, prometheus_url: str, namespace: str = "research-automation-bg"):
        self.prometheus = PrometheusConnect(url=prometheus_url, disable_ssl=True)
        self.namespace = namespace
    
    def get_error_rate(self, color: str, duration: str = "5m") -> float:
        """Get error rate for specific color"""
        query = f"""
        sum(rate(http_requests_total{{
            namespace="{self.namespace}",
            deployment="api-{color}",
            status=~"5.."
        }}[{duration}]))
        /
        sum(rate(http_requests_total{{
            namespace="{self.namespace}",
            deployment="api-{color}"
        }}[{duration}]))
        """
        
        try:
            result = self.prometheus.custom_query(query)
            if result:
                return float(result[0]['value'][1])
        except Exception as e:
            print(f"Error querying error rate: {e}")
        
        return 0.0
    
    def get_response_time(self, color: str, percentile: float = 0.95, duration: str = "5m") -> float:
        """Get response time percentile"""
        query = f"""
        histogram_quantile({percentile},
            sum(rate(http_request_duration_seconds_bucket{{
                namespace="{self.namespace}",
                deployment="api-{color}"
            }}[{duration}])) by (le)
        )
        """
        
        try:
            result = self.prometheus.custom_query(query)
            if result:
                return float(result[0]['value'][1])
        except Exception as e:
            print(f"Error querying response time: {e}")
        
        return 0.0
    
    def get_cpu_usage(self, color: str) -> float:
        """Get CPU usage percentage"""
        query = f"""
        sum(rate(container_cpu_usage_seconds_total{{
            namespace="{self.namespace}",
            pod=~"api-{color}-.*"
        }}[5m])) 
        / 
        sum(kube_pod_container_resource_limits{{
            namespace="{self.namespace}",
            pod=~"api-{color}-.*",
            resource="cpu"
        }})
        * 100
        """
        
        try:
            result = self.prometheus.custom_query(query)
            if result:
                return float(result[0]['value'][1])
        except Exception as e:
            print(f"Error querying CPU usage: {e}")
        
        return 0.0
    
    def get_memory_usage(self, color: str) -> float:
        """Get memory usage percentage"""
        query = f"""
        sum(container_memory_working_set_bytes{{
            namespace="{self.namespace}",
            pod=~"api-{color}-.*"
        }})
        /
        sum(kube_pod_container_resource_limits{{
            namespace="{self.namespace}",
            pod=~"api-{color}-.*",
            resource="memory"
        }})
        * 100
        """
        
        try:
            result = self.prometheus.custom_query(query)
            if result:
                return float(result[0]['value'][1])
        except Exception as e:
            print(f"Error querying memory usage: {e}")
        
        return 0.0
    
    def get_request_count(self, color: str, duration: str = "5m") -> int:
        """Get request count"""
        query = f"""
        sum(increase(http_requests_total{{
            namespace="{self.namespace}",
            deployment="api-{color}"
        }}[{duration}]))
        """
        
        try:
            result = self.prometheus.custom_query(query)
            if result:
                return int(float(result[0]['value'][1]))
        except Exception as e:
            print(f"Error querying request count: {e}")
        
        return 0
    
    def get_success_rate(self, color: str, duration: str = "5m") -> float:
        """Get success rate"""
        query = f"""
        sum(rate(http_requests_total{{
            namespace="{self.namespace}",
            deployment="api-{color}",
            status=~"2.."
        }}[{duration}]))
        /
        sum(rate(http_requests_total{{
            namespace="{self.namespace}",
            deployment="api-{color}"
        }}[{duration}]))
        * 100
        """
        
        try:
            result = self.prometheus.custom_query(query)
            if result:
                return float(result[0]['value'][1])
        except Exception as e:
            print(f"Error querying success rate: {e}")
        
        return 0.0
    
    def get_metrics(self, color: str) -> DeploymentMetrics:
        """Get all metrics for a deployment"""
        return DeploymentMetrics(
            color=color,
            error_rate=self.get_error_rate(color),
            response_time_p95=self.get_response_time(color),
            cpu_usage=self.get_cpu_usage(color),
            memory_usage=self.get_memory_usage(color),
            request_count=self.get_request_count(color),
            success_rate=self.get_success_rate(color),
            timestamp=datetime.now()
        )
    
    def compare_deployments(self) -> Dict:
        """Compare metrics between blue and green"""
        blue_metrics = self.get_metrics("blue")
        green_metrics = self.get_metrics("green")
        
        comparison = {
            'blue': blue_metrics,
            'green': green_metrics,
            'differences': {}
        }
        
        # Calculate differences
        metrics_to_compare = ['error_rate', 'response_time_p95', 'cpu_usage', 
                            'memory_usage', 'success_rate']
        
        for metric in metrics_to_compare:
            blue_val = getattr(blue_metrics, metric)
            green_val = getattr(green_metrics, metric)
            
            # Calculate percentage difference
            if blue_val > 0:
                diff_percent = ((green_val - blue_val) / blue_val) * 100
            else:
                diff_percent = 0
            
            comparison['differences'][metric] = {
                'absolute': green_val - blue_val,
                'percent': diff_percent,
                'status': 'better' if diff_percent <= 0 else 'worse'
            }
        
        return comparison
    
    def check_deployment_health(self, color: str, thresholds: Dict) -> Dict:
        """Check if deployment meets health thresholds"""
        metrics = self.get_metrics(color)
        
        checks = {
            'error_rate': metrics.error_rate <= thresholds.get('max_error_rate', 0.05),
            'response_time': metrics.response_time_p95 <= thresholds.get('max_response_time', 1.0),
            'cpu_usage': metrics.cpu_usage <= thresholds.get('max_cpu', 80),
            'memory_usage': metrics.memory_usage <= thresholds.get('max_memory', 90),
            'success_rate': metrics.success_rate >= thresholds.get('min_success_rate', 95),
        }
        
        all_passing = all(checks.values())
        
        return {
            'deployment': color,
            'metrics': metrics,
            'checks': checks,
            'all_passing': all_passing,
            'failing_checks': [k for k, v in checks.items() if not v]
        }

def main():
    parser = argparse.ArgumentParser(description="Blue-Green Deployment Monitor")
    parser.add_argument("--prometheus-url", required=True,
                       help="Prometheus server URL")
    parser.add_argument("--namespace", default="research-automation-bg",
                       help="Kubernetes namespace")
    parser.add_argument("--action", default="compare",
                       choices=["compare", "monitor", "health-check"],
                       help="Action to perform")
    parser.add_argument("--color", choices=["blue", "green"],
                       help="Specific color to check")
    parser.add_argument("--interval", type=int, default=30,
                       help="Monitoring interval in seconds")
    
    args = parser.parse_args()
    
    monitor = BlueGreenMonitor(args.prometheus_url, args.namespace)
    
    if args.action == "compare":
        comparison = monitor.compare_deployments()
        
        print("\n" + "="*60)
        print("Blue-Green Deployment Comparison")
        print("="*60)
        
        for color in ["blue", "green"]:
            metrics = comparison[color]
            print(f"\n{color.upper()} Deployment Metrics:")
            print(f"  Error Rate: {metrics.error_rate:.4f}")
            print(f"  Response Time (P95): {metrics.response_time_p95:.3f}s")
            print(f"  CPU Usage: {metrics.cpu_usage:.1f}%")
            print(f"  Memory Usage: {metrics.memory_usage:.1f}%")
            print(f"  Request Count: {metrics.request_count}")
            print(f"  Success Rate: {metrics.success_rate:.1f}%")
        
        print("\n" + "="*60)
        print("Differences (Green - Blue):")
        print("="*60)
        
        for metric, diff in comparison['differences'].items():
            status_icon = "✅" if diff['status'] == 'better' else "⚠️"
            print(f"\n{metric.replace('_', ' ').title()}:")
            print(f"  Absolute: {diff['absolute']:+.4f}")
            print(f"  Percent: {diff['percent']:+.1f}%")
            print(f"  Status: {status_icon} {diff['status']}")
    
    elif args.action == "health-check":
        if not args.color:
            print("Error: --color is required for health-check")
            return
        
        thresholds = {
            'max_error_rate': 0.05,
            'max_response_time': 1.0,
            'max_cpu': 80,
            'max_memory': 90,
            'min_success_rate': 95
        }
        
        result = monitor.check_deployment_health(args.color, thresholds)
        
        print(f"\nHealth Check for {args.color.upper()} Deployment:")
        print("="*60)
        
        for check_name, check_passed in result['checks'].items():
            icon = "✅" if check_passed else "❌"
            print(f"{icon} {check_name.replace('_', ' ').title()}")
        
        print("\n" + "="*60)
        if result['all_passing']:
            print("✅ All health checks PASSED")
        else:
            print("❌ FAILING checks:")
            for check in result['failing_checks']:
                print(f"  - {check}")
    
    elif args.action == "monitor":
        print(f"Monitoring deployments every {args.interval} seconds...")
        print("Press Ctrl+C to stop\n")
        
        try:
            while True:
                comparison = monitor.compare_deployments()
                
                # Simple dashboard
                print("\033[2J\033[H")  # Clear screen
                print(f"Monitoring at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print("="*60)
                
                for color in ["blue", "green"]:
                    metrics = comparison[color]
                    print(f"\n{color.upper()}:")
                    print(f"  Error: {metrics.error_rate:.4f} | "
                          f"RT: {metrics.response_time_p95:.3f}s | "
                          f"CPU: {metrics.cpu_usage:.1f}% | "
                          f"Mem: {metrics.memory_usage:.1f}% | "
                          f"Success: {metrics.success_rate:.1f}%")
                
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nMonitoring stopped")

if __name__ == "__main__":
    main()