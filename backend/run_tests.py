#!/usr/bin/env python3
"""
Test runner script for the RAG system backend tests.

This script provides a convenient way to run tests with different configurations.
"""
import subprocess
import sys
import argparse
from pathlib import Path


def run_pytest(args):
    """Run pytest with the given arguments."""
    cmd = ["uv", "run", "pytest"] + args
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    return result.returncode


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Run RAG system backend tests")
    parser.add_argument("--unit", action="store_true", help="Run only unit tests")
    parser.add_argument("--integration", action="store_true", help="Run only integration tests")
    parser.add_argument("--api", action="store_true", help="Run only API tests")
    parser.add_argument("--slow", action="store_true", help="Run slow tests")
    parser.add_argument("--coverage", action="store_true", help="Run with coverage report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--quiet", "-q", action="store_true", help="Quiet output")
    parser.add_argument("--file", "-f", help="Run specific test file")
    parser.add_argument("--function", "-k", help="Run tests matching keyword")
    parser.add_argument("--failed", action="store_true", help="Run only failed tests from last run")
    parser.add_argument("--parallel", "-n", type=int, help="Run tests in parallel")

    args, unknown_args = parser.parse_known_args()

    # Build pytest arguments
    pytest_args = []

    # Add test selection arguments
    if args.unit:
        pytest_args.extend(["-m", "unit"])
    elif args.integration:
        pytest_args.extend(["-m", "integration"])
    elif args.api:
        pytest_args.extend(["-m", "api"])
    elif args.slow:
        pytest_args.extend(["-m", "slow"])
    else:
        # Default: run all tests except slow ones
        pytest_args.extend(["-m", "not slow"])

    # Add coverage if requested
    if args.coverage:
        pytest_args.extend([
            "--cov=rag_system",
            "--cov=app",
            "--cov=config",
            "--cov=vector_store",
            "--cov=document_processor",
            "--cov=ai_generator",
            "--cov=session_manager",
            "--cov=search_tools",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "--cov-report=xml"
        ])

    # Add verbosity
    if args.verbose:
        pytest_args.append("-v")
    elif args.quiet:
        pytest_args.append("-q")

    # Add specific file
    if args.file:
        pytest_args.append(args.file)

    # Add keyword filter
    if args.function:
        pytest_args.extend(["-k", args.function])

    # Run only failed tests
    if args.failed:
        pytest_args.append("--lf")

    # Add parallel execution
    if args.parallel:
        pytest_args.extend(["-n", str(args.parallel)])

    # Add any additional arguments
    pytest_args.extend(unknown_args)

    # Run the tests
    return_code = run_pytest(pytest_args)

    # Exit with the pytest return code
    sys.exit(return_code)


if __name__ == "__main__":
    main()
