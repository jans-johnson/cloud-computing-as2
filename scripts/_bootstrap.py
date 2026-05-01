"""Make `core` and `config` importable when scripts are run directly.

Lets `python scripts/create_login_table.py` work without an editable
install or PYTHONPATH gymnastics on the AWS Academy VM.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
