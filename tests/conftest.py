import pytest
from pathlib import Path
import os
import sys


@pytest.fixture(autouse=True)
def setup_environment():
    """
    Ensure the proper environment for tests.
    - Add project root to Python path if not already there
    - Set working directory for proper file access
    """
    project_root = Path(__file__).parent.parent

    # Add project root to Python path if not already there
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # Store original directory to restore later
    original_dir = os.getcwd()

    # Change to project root for test execution
    os.chdir(project_root)

    yield

    # Restore original directory after test completes
    os.chdir(original_dir)
