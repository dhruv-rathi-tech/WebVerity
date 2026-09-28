"""
Main CLI entrypoint executed when running:
python -m audit <URL> [options]
"""

import sys
from audit import main

if __name__ == "__main__":
    sys.exit(main())
