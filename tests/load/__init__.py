"""Load Tests Package

This package contains load tests simulating concurrent users:
- 100 concurrent user simulations
- Login pressure tests
- Data read pressure tests
- Data write pressure tests

Usage:
    pytest tests/load -v --benchmark-only

Requirements:
    - pytest-benchmark
    - pytest-asyncio
    - httpx
"""
