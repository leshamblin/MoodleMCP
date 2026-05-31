"""
Offline test configuration.

Offline tests are pure unit tests with no network access. They build a
MoodleAPIClient (or stub) directly and never touch the live Moodle instance,
so they do NOT depend on the root conftest's live fixtures.
"""

import sys
from pathlib import Path

# Add src directory to Python path (mirrors the root conftest)
src_dir = Path(__file__).parent.parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))
