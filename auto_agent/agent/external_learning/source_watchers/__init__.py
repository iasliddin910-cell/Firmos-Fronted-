"""
Source Watchers Module
=====================

This module contains watchers for various external sources:
- Frontier AI systems (ChatGPT, Devin, DeepSeek, etc.)
- Social media (Reddit, Twitter, GitHub, YouTube)
- Documentation and release notes
- Benchmark leaderboards
- Account-based research (optional)
"""

from .frontier_observer import FrontierObserver
from .social_signal_observer import SocialSignalObserver
from .docs_release_watcher import DocsReleaseWatcher
from .benchmark_watcher import BenchmarkWatcher
from .account_research_worker import AccountResearchWorker

__all__ = [
    "FrontierObserver",
    "SocialSignalObserver",
    "DocsReleaseWatcher",
    "BenchmarkWatcher",
    "AccountResearchWorker"
]
