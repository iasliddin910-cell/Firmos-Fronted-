"""
External Learning System - The Eyes and Ears of Self-Upgrading Agent
====================================================================
This module observes external AI systems and trends to generate
upgrade candidates for the agent.

Layer Architecture:
1. Source Watchers - Observe various external sources
2. Signal Pipeline - Extract and score signals
3. Research Memory - Store and track observations
4. Upgrade Generation - Create actionable upgrade candidates
"""

from .external_learning_system import ExternalLearningSystem, create_external_learning_system

__all__ = [
    "ExternalLearningSystem",
    "create_external_learning_system"
]
