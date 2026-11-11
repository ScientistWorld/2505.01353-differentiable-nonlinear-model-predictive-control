#!/usr/bin/env python3
"""Entry point for fd_oracle_shortcut; implementation shared to keep comparisons exact."""
import runpy
import sys
sys.path.insert(0, '/home/user/redteam')
sys.argv = ['quality_method.py', 'fd_oracle_shortcut']
runpy.run_path('/home/user/redteam/quality_method.py', run_name='__main__')
