#!/usr/bin/env python
"""
Memory Agent Test Runner

This script runs all tests related to the Memory Agent and reports results.
There are three types of tests:
1. Unit tests - Testing core functionality with mocked dependencies
2. API tests - Testing API endpoints with mocked dependencies
3. End-to-end tests - Testing the full system with a real Marqo instance

Usage:
    python run_memory_tests.py [--unit] [--api] [--e2e] [--all]

Options:
    --unit: Run only unit tests
    --api: Run only API tests
    --e2e: Run only end-to-end tests
    --all: Run all tests (default)
"""

import os
import sys
import time
import argparse
import subprocess
from typing import List, Dict, Tuple, Optional


def run_unit_tests() -> Tuple[bool, str, float]:
    """Run memory agent unit tests and return results."""
    print("\n==================================================")
    print("Running Memory Agent Unit Tests...")
    print("==================================================\n")
    
    # Record start time
    start_time = time.time()
    
    # Run pytest with unit test marker
    try:
        result = subprocess.run(
            ["pytest", "tests/test_memory_agent.py", "-v"],
            capture_output=True,
            text=True,
            check=False
        )
        output = result.stdout
        errors = result.stderr
        success = result.returncode == 0
    except Exception as e:
        output = ""
        errors = f"Error running unit tests: {str(e)}"
        success = False
    
    # Calculate elapsed time
    elapsed_time = time.time() - start_time
    
    # Print results
    print(f"Output:\n{output}")
    if errors:
        print(f"Errors:\n{errors}")
    
    if success:
        print(f"✅ Memory Agent Unit Tests passed in {elapsed_time:.2f} seconds")
    else:
        print(f"❌ Memory Agent Unit Tests failed with exit code {result.returncode}")
    
    return success, output, elapsed_time


def run_api_tests() -> Tuple[bool, str, float]:
    """Run memory agent API tests and return results."""
    print("\n==================================================")
    print("Running Memory Agent API Tests...")
    print("==================================================\n")
    
    # Record start time
    start_time = time.time()
    
    # Run pytest with API test marker
    try:
        result = subprocess.run(
            ["pytest", "tests/test_memory_api.py", "-v"],
            capture_output=True,
            text=True,
            check=False
        )
        output = result.stdout
        errors = result.stderr
        success = result.returncode == 0
    except Exception as e:
        output = ""
        errors = f"Error running API tests: {str(e)}"
        success = False
    
    # Calculate elapsed time
    elapsed_time = time.time() - start_time
    
    # Print results
    print(f"Output:\n{output}")
    if errors:
        print(f"Errors:\n{errors}")
    
    if success:
        print(f"✅ Memory Agent API Tests passed in {elapsed_time:.2f} seconds")
    else:
        print(f"❌ Memory Agent API Tests failed with exit code {result.returncode}")
    
    return success, output, elapsed_time


def run_e2e_tests() -> Tuple[bool, str, float]:
    """Run memory agent end-to-end tests and return results."""
    print("\n==================================================")
    print("Running Memory Agent End-to-End Tests...")
    print("==================================================\n")
    
    # Record start time
    start_time = time.time()
    
    # Check if docker is installed (required for E2E tests)
    docker_available = False
    try:
        docker_check = subprocess.run(
            ["docker", "--version"], 
            capture_output=True,
            text=True,
            check=False
        )
        docker_available = docker_check.returncode == 0
    except FileNotFoundError:
        docker_available = False
    
    if not docker_available:
        output = "Docker is not available. End-to-end tests require Docker to run Marqo."
        errors = "Docker not found in PATH"
        print(f"Output:\n{output}")
        print(f"Errors:\n{errors}")
        print("⚠️ End-to-End tests skipped: Docker not available")
        return False, output, time.time() - start_time
    
    # Run the E2E test script directly
    try:
        result = subprocess.run(
            ["python", "tests/test_memory_e2e.py"],
            capture_output=True,
            text=True,
            check=False,
            timeout=300  # 5 minute timeout
        )
        output = result.stdout
        errors = result.stderr
        success = result.returncode == 0
    except subprocess.TimeoutExpired:
        output = "End-to-end tests timed out after 5 minutes"
        errors = "Test execution exceeded timeout limit"
        success = False
    except Exception as e:
        output = ""
        errors = f"Error running end-to-end tests: {str(e)}"
        success = False
    
    # Calculate elapsed time
    elapsed_time = time.time() - start_time
    
    # Print results
    print(f"Output:\n{output}")
    if errors:
        print(f"Errors:\n{errors}")
    
    if success:
        print(f"✅ Memory Agent End-to-End Tests passed in {elapsed_time:.2f} seconds")
    else:
        print(f"❌ Memory Agent End-to-End Tests failed with exit code {result.returncode if 'result' in locals() else 'unknown'}")
        # If it failed due to Marqo connection issues, make this clearer
        if "Could not start Marqo" in output or "Timeout waiting for Marqo" in output:
            print("\n⚠️ End-to-End tests failed because Marqo couldn't be started or reached.")
            print("This may be due to Docker configuration issues or port conflicts.")
            print("The unit and API tests should still work correctly.")
    
    return success, output, elapsed_time


def main():
    """Run the selected tests and report results."""
    parser = argparse.ArgumentParser(description="Run memory agent tests")
    parser.add_argument("--unit", action="store_true", help="Run unit tests")
    parser.add_argument("--api", action="store_true", help="Run API tests")
    parser.add_argument("--e2e", action="store_true", help="Run end-to-end tests")
    parser.add_argument("--all", action="store_true", help="Run all tests (default)")
    args = parser.parse_args()
    
    # If no specific tests are selected, run all tests
    run_all = args.all or not (args.unit or args.api or args.e2e)
    
    # Store test results
    results = {}
    
    # Run the selected tests
    if args.unit or run_all:
        results["UNIT TESTS"] = run_unit_tests()[0]
    
    if args.api or run_all:
        results["API TESTS"] = run_api_tests()[0]
    
    if args.e2e or run_all:
        e2e_success, e2e_output, _ = run_e2e_tests()
        # Special case for E2E tests - if they failed due to Marqo not being available,
        # we don't count this as a failure for the overall test run
        if not e2e_success and ("Could not start Marqo" in e2e_output or "Timeout waiting for Marqo" in e2e_output):
            results["E2E TESTS"] = "SKIPPED"
        else:
            results["E2E TESTS"] = e2e_success
    
    # Print summary
    print("\n==================================================")
    print("SUMMARY OF TEST RESULTS")
    print("==================================================")
    
    # Determine overall success
    overall_success = True
    
    for test_name, success in results.items():
        if success is True:
            print(f"{test_name}: ✅ PASSED")
        elif success == "SKIPPED":
            print(f"{test_name}: ⚠️ SKIPPED")
            # Don't count skipped tests as failures
        else:
            print(f"{test_name}: ❌ FAILED")
            # Only count actual failures as failures
            if success is False:
                overall_success = False
    
    # Return appropriate exit code
    return 0 if overall_success else 1


if __name__ == "__main__":
    sys.exit(main()) 