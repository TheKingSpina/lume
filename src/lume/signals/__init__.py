"""Signal capture modules - git, sessions, files, decay."""

from lume.signals.decay import apply_decay, recompute_importance
from lume.signals.files import FileCorrelation
from lume.signals.git import GitSync, capture_recent_commits
from lume.signals.session import Session, SessionTracker

__all__ = [
    "GitSync",
    "capture_recent_commits",
    "Session",
    "SessionTracker",
    "apply_decay",
    "recompute_importance",
    "FileCorrelation",
]
