import fcntl
from contextlib import contextmanager
from pathlib import Path

LOCK_PATH = Path(__file__).resolve().parent.parent / ".outreach.lock"


@contextmanager
def run_lock():
    """Wait for any other pull/send run to finish, so two runs never read and write the sheet at once."""
    with open(LOCK_PATH, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
