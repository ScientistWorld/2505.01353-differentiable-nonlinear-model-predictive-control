#!/usr/bin/env python3
"""Entry point for null_error_shortcut; implementation shared to keep comparisons exact."""
import runpy
import sys
sys.path.insert(0, '/home/user/redteam')
sys.argv = ['artifact_shortcuts.py', 'null_error_shortcut']
runpy.run_path('/home/user/redteam/artifact_shortcuts.py', run_name='__main__')
