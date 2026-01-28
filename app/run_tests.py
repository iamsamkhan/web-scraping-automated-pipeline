#!/usr/bin/env python3
"""
Comprehensive test runner for Academic Research Automation System
"""

import sys
import os
import subprocess
import argparse
import json
from pathlib import Path
from datetime import datetime
import webbrowser

def run_tests(test_type: str = "all", verbose: bool = False, 
              coverage: bool = True, parallel: bool = False,
              output_dir: str = "test_reports"):
    """
    Run tests based on type
    
    Args:
        test_type: Type of tests to run (all, unit, integration, e2e, specific)
        verbose: Enable verbose output
        coverage: Generate coverage reports
        parallel: Run tests in parallel
        output_dir: Directory for test reports
    """
    
    # Create output directory
    Path(output_dir).mkdir(exist_ok=True)
    
    # Build pytest command
    cmd = ["pytest"]
    
    # Add markers based on test type
    if test_type == "unit":
        cmd.extend(["tests/unit", "-m", "not integration and not e2e"])
    elif test_type == "integration":
        cmd.extend(["tests/integration", "-m", "integration"])
    elif test_type == "e2e":
        cmd.extend(["tests/e2e", "-m", "e2e"])
    elif test_type == "all":
        cmd.extend(["tests/"])
    elif test_type.startswith("test_"):
        # Specific test file
        cmd.extend([f"tests/unit/{test_type}"])
    else:
        # Specific test
        cmd.extend([test_type])
    
    # Add options
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend([
            "--cov=app",
            "--cov-report=html",
            "--cov-report=term",
            "--cov-report=xml",
            f"--cov-report=html:{output_dir}/coverage",
            f"--cov-report=xml:{output_dir}/coverage.xml"
        ])
    
    if parallel:
        cmd.extend(["-n", "auto"])
    
    # Add report generation
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    cmd.extend([
        f"--html={output_dir}/test_report_{timestamp}.html",
        f"--self-contained-html",
        f"--junitxml={output_dir}/junit_{timestamp}.xml"
    ])
    
    print(f"\n🚀 Running tests: {' '.join(cmd)}")
    print("="*60)
    
    # Run tests
    try:
        result = subprocess.run(cmd, check=False)
        
        # Generate summary report
        generate_summary_report(output_dir, timestamp, result.returncode)
        
        # Open coverage report in browser
        if coverage and result.returncode == 0:
            coverage_report = Path(output_dir) / "coverage" / "index.html"
            if coverage_report.exists():
                print(f"\n📊 Coverage report: file://{coverage_report.absolute()}")
                if input("\nOpen coverage report in browser? (y/n): ").lower() == 'y':
                    webbrowser.open(f"file://{coverage_report.absolute()}")
        
        return result.returncode
        
    except KeyboardInterrupt:
        print("\n\n⏹️ Test run interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        return 1

def generate_summary_report(output_dir: str, timestamp: str, exit_code: int):
    """Generate test summary report"""
    summary = {
        "timestamp": datetime.now().isoformat(),
        "exit_code": exit_code,
        "status": "PASSED" if exit_code == 0 else "FAILED",
        "reports": {
            "html": f"test_report_{timestamp}.html",
            "junit": f"junit_{timestamp}.xml",
            "coverage": "coverage/index.html"
        }
    }
    
    summary_file = Path(output_dir) / f"summary_{timestamp}.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n📋 Summary report: {summary_file}")
    print(f"   Status: {summary['status']}")
    print(f"   HTML Report: {summary['reports']['html']}")

def run_debug_tests():
    """Run tests in debug mode with extra verbosity"""
    print("\n🔧 Running tests in DEBUG mode")
    print("="*60)
    
    cmd = [
        "pytest", "tests/unit/", "-v", "-s",
        "--tb=long",
        "--capture=no",
        "--log-level=DEBUG",
        "--show-capture=all"
    ]
    
    return subprocess.run(cmd).returncode

def run_performance_tests():
    """Run performance tests"""
    print("\n⏱️ Running performance tests")
    print("="*60)
    
    cmd = [
        "pytest", "tests/unit/", "-m", "performance", "-v",
        "--durations=10"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print(result.stdout)
    
    if result.stderr:
        print("\nErrors:")
        print(result.stderr)
    
    return result.returncode

def run_security_tests():
    """Run security tests"""
    print("\n🔒 Running security tests")
    print("="*60)
    
    cmd = [
        "pytest", "tests/unit/", "-m", "security", "-v"
    ]
    
    result = subprocess.run(cmd)
    return result.returncode

def main():
    parser = argparse.ArgumentParser(description="Run tests for Academic Research Automation System")
    parser.add_argument("type", nargs="?", default="all",
                       choices=["all", "unit", "integration", "e2e", "debug", 
                                "performance", "security", "specific"],
                       help="Type of tests to run")
    parser.add_argument("--specific", help="Specific test file or test name")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--no-coverage", action="store_true", help="Disable coverage reports")
    parser.add_argument("-p", "--parallel", action="store_true", help="Run tests in parallel")
    parser.add_argument("-o", "--output", default="test_reports", help="Output directory for reports")
    
    args = parser.parse_args()
    
    # Set up environment
    os.environ["TEST_MODE"] = "true"
    os.environ["LOG_LEVEL"] = "INFO"
    
    # Run appropriate tests
    if args.type == "debug":
        return run_debug_tests()
    elif args.type == "performance":
        return run_performance_tests()
    elif args.type == "security":
        return run_security_tests()
    elif args.type == "specific":
        if not args.specific:
            print("❌ Error: --specific argument required for 'specific' test type")
            return 1
        test_target = args.specific
    else:
        test_target = args.type
    
    return run_tests(
        test_type=test_target,
        verbose=args.verbose,
        coverage=not args.no_coverage,
        parallel=args.parallel,
        output_dir=args.output
    )

if __name__ == "__main__":
    sys.exit(main())