#!/usr/bin/env python3
"""
Test runner for compiler optimization test suite.
Discovers and executes all test_* functions across tests/ directory.
"""
import os
import sys
import inspect
import importlib
import traceback


def run_all_tests():
    tests_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests")
    test_files = sorted([f for f in os.listdir(tests_dir) if f.startswith("test_") and f.endswith(".py")])

    total_tests = 0
    passed_tests = 0
    failed_tests = 0

    print(f"\n====================== RUNNING TEST SUITE ======================")
    print(f"Found {len(test_files)} test files in {tests_dir}\n")

    for f in test_files:
        mod_name = f"tests.{f[:-3]}"
        try:
            mod = importlib.import_module(mod_name)
        except Exception as e:
            print(f"❌ Failed to import {mod_name}: {e}")
            traceback.print_exc()
            failed_tests += 1
            continue

        test_funcs = [
            (name, func) for name, func in inspect.getmembers(mod, inspect.isfunction)
            if name.startswith("test_")
        ]

        print(f"📁 {f} ({len(test_funcs)} tests):")
        for name, func in test_funcs:
            total_tests += 1
            try:
                func()
                passed_tests += 1
                print(f"   ✓ {name}")
            except AssertionError as e:
                failed_tests += 1
                print(f"   ❌ {name}: Assertion failed: {e}")
                traceback.print_exc()
            except Exception as e:
                failed_tests += 1
                print(f"   ❌ {name}: Unexpected error: {e}")
                traceback.print_exc()

    print(f"\n======================= TEST SUMMARY =======================")
    print(f"Total:  {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")

    if failed_tests == 0 and total_tests > 0:
        print("\n🎉 ALL TESTS PASSED!\n")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED!\n")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
