"""
TransferScore - Transfer Evaluation
==============================

Transfer evaluation - internal dan externalga.

Bu modul:
- Internal delta
- External delta
- Transfer ratio
- Overfit detection
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any


@dataclass
class TransferMetrics:
    """Transfer metrikalari."""
    internal_before: float
    internal_after: float
    internal_delta: float
    
    external_before: float
    external_after: float
    external_delta: float
    
    # Transfer ratio
    transfer_ratio: float  # external_delta / internal_delta
    
    # Assessment
    is_overfit: bool = False
    is_underfit: bool = False
    is_good_transfer: bool = False


class TransferScorer:
    """
    Transfer scorer.
    """
    
    def __init__(self):
        self.overfit_threshold = 0.5  # If transfer_ratio < 0.5 = overfit
        self.underfit_threshold = 1.5  # If transfer_ratio > 1.5 = underfit
        self.good_transfer_min = 0.7
    
    def score_transfer(
        self,
        internal_before: float,
        internal_after: float,
        external_before: float,
        external_after: float,
    ) -> TransferMetrics:
        """Transferni baholash."""
        internal_delta = internal_after - internal_before
        external_delta = external_after - external_before
        
        # Calculate transfer ratio
        if internal_delta > 0:
            transfer_ratio = external_delta / internal_delta
        else:
            transfer_ratio = 0.0
        
        # Determine assessment
        is_overfit = (
            internal_delta > 0 and 
            external_delta <= 0 and 
            transfer_ratio < self.overfit_threshold
        )
        
        is_underfit = (
            external_delta > internal_delta and
            transfer_ratio > self.underfit_threshold
        )
        
        is_good = (
            transfer_ratio >= self.good_transfer_min and
            external_delta > 0
        )
        
        return TransferMetrics(
            internal_before=internal_before,
            internal_after=internal_after,
            internal_delta=internal_delta,
            external_before=external_before,
            external_after=external_after,
            external_delta=external_delta,
            transfer_ratio=transfer_ratio,
            is_overfit=is_overfit,
            is_underfit=is_underfit,
            is_good_transfer=is_good,
        )


def create_transfer_scorer() -> TransferScorer:
    """Transfer scorer yaratish."""
    return TransferScorer()
