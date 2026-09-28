import sys
from pathlib import Path

# The real ulauncher package needs GTK and a running app; tests use a minimal stand-in.
sys.path.insert(0, str(Path(__file__).parent / "_stubs"))
