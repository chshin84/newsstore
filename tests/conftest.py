import os
from pathlib import Path

# Pin the working directory to the repo root so tests that read relative paths
# (config/feeds.yaml, tests/fixtures/...) resolve regardless of where pytest is
# invoked from.
os.chdir(Path(__file__).resolve().parent.parent)
