"""Stress Tests Package

This package contains stress tests for system limits:
- Maximum connection handling
- Large file upload handling
- Long-running stability tests
- Resource release verification

Usage:
    pytest tests/stress -v --benchmark-only

Requirements:
    - pytest-benchmark
    - pytest-asyncio
    - psutil (for memory monitoring)
    - httpx
"""
