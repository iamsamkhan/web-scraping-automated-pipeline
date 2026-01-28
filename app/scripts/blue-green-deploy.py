#!/usr/bin/env python3
"""
Blue-Green Deployment Management Script
"""

import argparse
import yaml
import subprocess
import time
import json
import sys
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import requests

class BlueGreenDeployer:
    def __init__(self, namespace: str = "research-automation-bg", 
                 kubeconfig: Optional[str] = None):
        self.namespace = namespace
        self.kubeconfig = kubeconfig
        self.kubectl_cmd = ["kubectl"]
        if kubeconfig:
            self.kubectl_cmd.extend(["--kubeconfig", kubeconfig])
        
    def run_kubectl(self, args: List[str], capture_output: bool = True) -> Dict:
        """Run kubectl command"""
        cmd = self.kubectl_cmd + args
        try:
            result = subprocess.run(
                cmd,
                capture_output=capture_output,
                text=True,
                check=True
            )
            if capture_output:
                return json.loads(result.stdout) if result.stdout else {}
            return {}
        except subprocess.CalledProcessError as e:
            print(f"Kubectl command failed: {e}")
            print(f"Stderr: {e.stderr}")
            raise
    
    def get_current_color(self) -> str:
        """Get currently active color"""
        try:
            config = self.run_kubectl([
                "get", "configmap", "blue-green-config",
                "-n", self.namespace,
                "-o", "json"
            ])
            return config.get('data', {}).get('active-color', 'blue')
        except:
            return "blue"
    
    def get_deployment_status(self, color: str) -> Dict:
        """Get deployment status for a specific color"""
        try:
            deployment = self.run_kubectl([
                "get", "deployment", f"api-{color}",
                "-n", self.namespace,
                "-o", "json"
            ])
            
            status = deployment.get('status', {})
            ready_replicas = status.get('readyReplicas', 0)
            replicas = status.get('replicas', 0)
            available_replicas = status.get('availableReplicas', 0)
            
            return {
                'color': color,
                'ready': ready_replicas,
                'total': replicas,
                'available': available_replicas,
                'fully_ready': ready_replicas == replicas and available_replicas == replicas
            }
        except:
            return {'color': color, 'ready': 0, 'total': 0, 'available': 0, 'fully_ready': False}
    
    def deploy_new_version(self, image_tag: str, color: str) -> bool:
        """Deploy new version to specified color"""
        print(f"Deploying version {image_tag} to {color} environment")
        
        # Update deployment image
        try:
            self.run_kubectl([
                "set", "image", f"deployment/api-{color}",
                f"api=ghcr.io/yourusername/research-automation:{image_tag}",
                "-n", self.namespace
            ], capture_output=False)
            return True
        except Exception as e:
            print(f"Failed to update deployment: {e}")
            return False
    
    def scale_deployment(self, color: str, replicas: int) -> bool:
        """Scale deployment to specified number of replicas"""
        print(f"Scaling {color} deployment to {replicas} replicas")
        
        try:
            self.run_kubectl([
                "scale", "deployment", f"api-{color}",
                f"--replicas={replicas}",
                "-n", self.namespace
            ], capture_output=False)
            return True
        except Exception as e:
            print(f"Failed to scale deployment: {e}")
            return False
    
    def update_configmap(self, key: str, value: str) -> bool:
        """Update blue-green configmap"""
        try:
            self.run_kubectl([
                "patch", "configmap", "blue-green-config",
                "-n", self.namespace,
                "--type", "merge",
                f"--patch='{{\"data\":{{\"{key}\":\"{value}\"}}}}'"
            ], capture_output=False)
            return True
        except Exception as e:
            print(f"Failed to update configmap: {e}")
            return False
    
    def update_ingress_weight(self, color: str, weight: int) -> bool:
        """Update traffic weight for specific color"""
        print(f"Setting traffic weight for {color} to {weight}%")
        
        # Update nginx ingress annotation
        try:
            self.run_kubectl([
                "patch", "ingress", "api-ingress",
                "-n", self.namespace,
                "--type", "merge",
                f"--patch='{{\"metadata\":{{\"annotations\":{{\"nginx.ingress.kubernetes.io/canary-weight\":\"{weight}\"}}}}}}'"
            ], capture_output=False)
            return True
        except Exception as e:
            print(f"Failed to update ingress weight: {e}")
            return False
    
    def run_health_check(self, color: str, base_url: str = None) -> bool:
        """Run health checks on deployment"""
        if not base_url:
            # Try to get service IP
            try:
                service = self.run_kubectl([
                    "get", "service", f"api-{color}-service",
                    "-n", self.namespace,
                    "-o", "jsonpath={.status.loadBalancer.ingress[0].ip}"
                ])
                base_url = f"http://{service}"
            except:
                base_url = f"http://api-{color}-service.{self.namespace}.svc.cluster.local:8000"
        
        endpoints = [
            "/health",
            "/health/ready",
            "/api/v1/students",
            "/api/v1/email/templates"
        ]
        
        all_healthy = True
        for endpoint in endpoints:
            url = f"{base_url.rstrip('/')}{endpoint}"
            try:
                response = requests.get(
                    url,
                    headers={'X-Deployment-Color': color},
                    timeout=5
                )
                if response.status_code == 200:
                    print(f"✓ {color}: {endpoint} - Healthy")
                else:
                    print(f"✗ {color}: {endpoint} - Status {response.status_code}")
                    all_healthy = False
            except Exception as e:
                print(f"✗ {color}: {endpoint} - Error: {e}")
                all_healthy = False
        
        return all_healthy
    
    def canary_deployment(self, image_tag: str, 
                         max_percentage: int = 50,
                         duration_minutes: int = 30,
                         step_percentage: int = 10) -> bool:
        """
        Perform canary deployment with gradual traffic shifting
        
        Steps:
        1. Deploy to green environment
        2. Start with 0% traffic
        3. Gradually increase traffic
        4. Monitor health metrics
        5. Roll forward or rollback
        """
        print(f"Starting canary deployment for version {image_tag}")
        
        # Step 1: Deploy to green
        current_color = self.get_current_color()
        new_color = "green" if current_color == "blue" else "blue"
        
        if not self.deploy_new_version(image_tag, new_color):
            return False
        
        # Wait for deployment to be ready
        print("Waiting for deployment to be ready...")
        for i in range(30):  # 5 minutes max
            status = self.get_deployment_status(new_color)
            if status['fully_ready']:
                print(f"{new_color} deployment is ready")
                break
            time.sleep(10)
            print(f"Waiting... ({i+1}/30)")
        else:
            print(f"Timeout waiting for {new_color} deployment")
            return False
        
        # Step 2: Run initial health checks
        if not self.run_health_check(new_color):
            print(f"Initial health checks failed for {new_color}")
            return False
        
        # Step 3: Gradual traffic shifting
        percentages = list(range(step_percentage, max_percentage + step_percentage, step_percentage))
        percentages.append(100)  # Final shift
        
        for percentage in percentages:
            print(f"\nShifting {percentage}% traffic to {new_color}")
            
            # Update ingress weight
            self.update_ingress_weight(new_color, percentage)
            
            # Wait for traffic to stabilize
            time.sleep(60)  # Wait 1 minute
            
            # Run health checks
            print(f"Running health checks with {percentage}% traffic...")
            if not self.run_health_check(new_color):
                print(f"Health checks failed at {percentage}% traffic")
                
                # Rollback: shift all traffic back to old color
                print("Rolling back traffic...")
                self.update_ingress_weight(new_color, 0)
                return False
            
            # Check metrics
            if not self.check_metrics(new_color):
                print(f"Metrics check failed at {percentage}% traffic")
                self.update_ingress_weight(new_color, 0)
                return False
            
            # If this is the final step, complete the switch
            if percentage == 100:
                print(f"\n✅ Canary deployment successful!")
                print(f"Switching active color to {new_color}")
                self.update_configmap("active-color", new_color)
                return True
        
        return False
    
    def check_metrics(self, color: str) -> bool:
        """Check Prometheus metrics for deployment"""
        # In production, this would query Prometheus
        # For now, simulate with simple checks
        metrics_to_check = {
            'error_rate': 0.05,  # Max 5% error rate
            'response_time_p95': 1.0,  # Max 1 second P95
            'cpu_usage': 80,  # Max 80% CPU
            'memory_usage': 90,  # Max 90% memory
        }
        
        # Simulate metrics check
        time.sleep(5)
        return True
    
    def rollback(self) -> bool:
        """Rollback to previous version"""
        print("Initiating rollback...")
        
        current_color = self.get_current_color()
        previous_color = "green" if current_color == "blue" else "blue"
        
        # Shift all traffic to previous color
        print(f"Shifting all traffic to {previous_color}")
        self.update_ingress_weight(previous_color, 100)
        self.update_configmap("active-color", previous_color)
        
        # Scale down current deployment
        print(f"Scaling down {current_color} deployment")
        self.scale_deployment(current_color, 0)
        
        print("✅ Rollback completed")
        return True
    
    def cleanup_old_deployment(self) -> bool:
        """Clean up old deployment resources"""
        current_color = self.get_current_color()
        old_color = "green" if current_color == "blue" else "blue"
        
        print(f"Cleaning up {old_color} deployment")
        
        # Scale down to 0
        self.scale_deployment(old_color, 0)
        
        # Optionally delete resources
        # self.run_kubectl(["delete", "deployment", f"api-{old_color}", "-n", self.namespace])
        
        return True

def main():
    parser = argparse.ArgumentParser(description="Blue-Green Deployment Manager")
    parser.add_argument("--action", required=True, 
                       choices=["deploy", "canary", "switch", "rollback", "status", "cleanup"],
                       help="Action to perform")
    parser.add_argument("--image-tag", help="Docker image tag to deploy")
    parser.add_argument("--namespace", default="research-automation-bg",
                       help="Kubernetes namespace")
    parser.add_argument("--kubeconfig", help="Path to kubeconfig file")
    parser.add_argument("--max-percentage", type=int, default=50,
                       help="Max traffic percentage for canary")
    parser.add_argument("--duration", type=int, default=30,
                       help="Duration in minutes for canary testing")
    parser.add_argument("--step", type=int, default=10,
                       help="Traffic shift step percentage")
    
    args = parser.parse_args()
    
    deployer = BlueGreenDeployer(args.namespace, args.kubeconfig)
    
    if args.action == "status":
        current = deployer.get_current_color()
        blue_status = deployer.get_deployment_status("blue")
        green_status = deployer.get_deployment_status("green")
        
        print(f"\nCurrent active color: {current}")
        print(f"\nBlue deployment:")
        print(f"  Ready: {blue_status['ready']}/{blue_status['total']}")
        print(f"  Available: {blue_status['available']}")
        print(f"  Fully ready: {blue_status['fully_ready']}")
        
        print(f"\nGreen deployment:")
        print(f"  Ready: {green_status['ready']}/{green_status['total']}")
        print(f"  Available: {green_status['available']}")
        print(f"  Fully ready: {green_status['fully_ready']}")
        
        # Check health
        print("\nHealth checks:")
        for color in ["blue", "green"]:
            healthy = deployer.run_health_check(color)
            print(f"  {color}: {'Healthy' if healthy else 'Unhealthy'}")
    
    elif args.action == "deploy":
        if not args.image_tag:
            print("Error: --image-tag is required for deploy action")
            sys.exit(1)
        
        current_color = deployer.get_current_color()
        new_color = "green" if current_color == "blue" else "blue"
        
        print(f"Current active: {current_color}")
        print(f"Deploying to: {new_color}")
        
        if deployer.deploy_new_version(args.image_tag, new_color):
            print("✅ Deployment initiated")
            # Wait and check status
            time.sleep(30)
            status = deployer.get_deployment_status(new_color)
            print(f"Deployment status: {status}")
        else:
            print("❌ Deployment failed")
            sys.exit(1)
    
    elif args.action == "canary":
        if not args.image_tag:
            print("Error: --image-tag is required for canary action")
            sys.exit(1)
        
        success = deployer.canary_deployment(
            args.image_tag,
            args.max_percentage,
            args.duration,
            args.step
        )
        
        if success:
            print("✅ Canary deployment completed successfully")
            sys.exit(0)
        else:
            print("❌ Canary deployment failed")
            deployer.rollback()
            sys.exit(1)
    
    elif args.action == "switch":
        current = deployer.get_current_color()
        new = "green" if current == "blue" else "blue"
        
        print(f"Switching from {current} to {new}")
        
        # Check if target is ready
        status = deployer.get_deployment_status(new)
        if not status['fully_ready']:
            print(f"Error: {new} deployment is not ready")
            sys.exit(1)
        
        # Update ingress to send all traffic to new
        deployer.update_ingress_weight(new, 100)
        deployer.update_configmap("active-color", new)
        
        print(f"✅ Traffic switched to {new}")
    
    elif args.action == "rollback":
        deployer.rollback()
    
    elif args.action == "cleanup":
        deployer.cleanup_old_deployment()

if __name__ == "__main__":
    main()