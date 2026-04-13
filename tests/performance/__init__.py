"""Performance Tests Package

This package contains performance benchmarks for the application:
- Database performance tests (N+1 queries, batch operations, index efficiency)
- Cache performance tests (hit rates, write performance, concurrent access)
- API response time tests (endpoints, concurrent requests, memory usage)

Usage:
    pytest tests/performance -v --benchmark-only

Requirements:
    - pytest-benchmark
    - pytest-asyncio
"""
