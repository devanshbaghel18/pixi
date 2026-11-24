#!/usr/bin/env python3
"""
run_tests.py — Unified Test Runner for Princess Mia
Discovers and executes all 162 unit and integration tests across the project.
"""

import os
import sys
import time
import unittest


def main():
    start_time = time.time()
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=".", pattern="test_*.py")

    print("\033[1;35m" + "=" * 65)
    print("✨ Running Princess Mia Automated Test Suite ✨")
    print("=" * 65 + "\033[0m\n")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    duration = time.time() - start_time
    total = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    passed = total - failures - errors

    print("\n" + "=" * 65)
    if result.wasSuccessful():
        print(
            f"\033[1;32m🎉 ALL {passed} TESTS PASSED SUCCESSFULLY in {duration:.2f}s! (100% OK)\033[0m"
        )
        return 0
    else:
        print(
            f"\033[1;31m❌ TEST FAILURES: {failures} failed, {errors} errors out of {total} total tests.\033[0m"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
