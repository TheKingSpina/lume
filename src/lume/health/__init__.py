"""Health checks: self-test, conflict detection, accuracy tracking."""

from lume.health.adaptive import adaptive_history, apply_adaptive_boost
from lume.health.conflicts import ConflictDetector, FactConflict
from lume.health.self_test import SelfTestResult, SelfTestRunner

__all__ = [
    "SelfTestRunner",
    "SelfTestResult",
    "ConflictDetector",
    "FactConflict",
    "apply_adaptive_boost",
    "adaptive_history",
]
