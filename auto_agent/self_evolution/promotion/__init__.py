"""
Promotion Layer - Promotion Execution and Branch Management
"""

import uuid
import logging
import shutil
from datetime import datetime
from typing import Optional
from pathlib import Path

from ..data_contracts import (
    PromotionRecord, DestinationType
)

logger = logging.getLogger(__name__)


class PromotionExecutor:
    """Promotion Executor - Promotion ni amalga oshirish"""
    
    def __init__(self, workspace_path: str):
        self.workspace_path = Path(workspace_path)
        self.promotions: dict[str, PromotionRecord] = {}
        logger.info("🚀 PromotionExecutor initialized")
    
    def promote(
        self,
        candidate_id: str,
        clone_id: str,
        destination: DestinationType,
        approved_by: str,
        artifacts_hash: str = ""
    ) -> PromotionRecord:
        record_id = f"promo_{str(uuid.uuid4())[:12]}"
        
        promoted_from = "candidate"
        promoted_to = destination.value
        rollback_anchor = f"anchor_{str(uuid.uuid4())[:12]}"
        
        record = PromotionRecord(
            id=record_id,
            destination=destination,
            approved_by=approved_by,
            promoted_from=promoted_from,
            promoted_to=promoted_to,
            artifacts_hash=artifacts_hash,
            rollback_anchor=rollback_anchor
        )
        
        self.promotions[record_id] = record
        logger.info(f"🚀 Promoted {clone_id} to {destination.value}")
        
        return record
    
    def rollback(self, record_id: str) -> bool:
        logger.info(f"🚀 Rollback: {record_id}")
        return True


class PromotionLayer:
    """Promotion Layer - To'liq promotion tizimi"""
    
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        self.executor = PromotionExecutor(workspace_path)
        logger.info("🚀 PromotionLayer initialized")
    
    def promote(self, candidate_id: str, clone_id: str, destination: DestinationType, approved_by: str) -> PromotionRecord:
        return self.executor.promote(candidate_id, clone_id, destination, approved_by)
    
    def rollback(self, record_id: str) -> bool:
        return self.executor.rollback(record_id)


def create_promotion_layer(workspace_path: str) -> PromotionLayer:
    return PromotionLayer(workspace_path)
