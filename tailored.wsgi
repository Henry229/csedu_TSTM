import os
import sys
basedir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, basedir)

from tailored import app as application
