#!/usr/bin/env python3
import runpy
import sys
sys.path.insert(0, '/home/user/redteam')
sys.argv = ['native_better.py', 'better_native_tol12']
runpy.run_path('/home/user/redteam/native_better.py', run_name='__main__')
