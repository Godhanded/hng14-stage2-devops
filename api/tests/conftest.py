import sys
import os

# Ensure the api/ directory is on the path so `import main` resolves correctly
# when pytest is invoked from the repo root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
