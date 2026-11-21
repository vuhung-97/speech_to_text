"""Start the STT server (web UI + API). See backend/bootstrap.py for all options.

Run:  python run.py
      python run.py --mode accurate --no-browser
"""

import sys

from backend.bootstrap import main

if __name__ == "__main__":
    sys.exit(main())
