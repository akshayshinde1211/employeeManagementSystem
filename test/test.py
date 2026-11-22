"""
Forwarding runner for test directory
Developer: Akshay Shinde
"""
import os
import sys

# Ensure tests folder is in sys.path
TESTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tests'))
if TESTS_DIR not in sys.path:
    sys.path.insert(0, TESTS_DIR)

from test import *

if __name__ == '__main__':
    import unittest
    unittest.main()
