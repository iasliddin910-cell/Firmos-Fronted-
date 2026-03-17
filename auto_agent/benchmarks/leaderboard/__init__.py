"""
Leaderboard Package - Multi-Axis Score Board Management
====================================================

Manages stable and experimental leaderboards.

Modules:
- leaderboard: Core leaderboard management

Usage:
    from leaderboard import LeaderboardManager, BoardEntry, BoardType, SliceType
"""

from .leaderboard import (
    LeaderboardManager,
    Leaderboard,
    BoardEntry,
    BoardType,
    SliceType,
    create_leaderboard_manager,
    create_entry_from_scorecard,
)

__all__ = [
    "LeaderboardManager",
    "Leaderboard",
    "BoardEntry",
    "BoardType",
    "SliceType",
    "create_leaderboard_manager",
    "create_entry_from_scorecard",
]

__version__ = "1.0.0"
