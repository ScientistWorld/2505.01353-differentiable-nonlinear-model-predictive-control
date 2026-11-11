#!/usr/bin/env python3
"""Entry point for weaker_gn; implementation shared to keep comparisons exact."""
import runpy
import sys
sys.path.insert(0, '/home/user/redteam')
sys.argv = ['artifact_shortcuts.py', 'weaker_gn']
runpy.run_path('/home/user/redteam/artifact_shortcuts.py', run_name='__main__')
