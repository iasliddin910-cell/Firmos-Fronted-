"""
Intake Layer - Signal Reception and Processing
===============================================
Bu qatlam tashqi dunyodan kelgan signallarni qabul qiladi,
tartiblaydi va normalizatsiya qiladi.

Kelayotgan signal turlari:
- External observations
- Benchmark failures
- User feedback
- Regression alerts
- New tool opportunities
- Competitor capability signals
- Social pain signals
- Research conclusions
"""

import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import asdict

from ..data_contracts import (
    Observation, SignalType, SignalSource
)

logger = logging.getLogger(__name__)


class SignalIngest:
    """
    Signal Intake - Kiruvchi signallarni qabul qilish
    Bu birinchi nuqta - signal ler bu yerda qabul qilinadi
    """
    
    def __init__(self):
        self.observations: dict[str, Observation] = {}
        self.ingestion_stats = {
            "total_received": 0,
            "by_source": {},
            "by_type": {}
        }
        logger.info("📥 SignalIngest initialized")
    
    def ingest_observation(
        self,
        summary: str,
        source: SignalSource,
        signal_type: SignalType,
        evidence: Optional[dict] = None,
        tags: Optional[list[str]] = None,
        confidence: float = 0.5,
        expires_in_hours: Optional[int] = None
    ) -> Observation:
        """
        Yangi observation ni qabul qilish
        
        Args:
            summary: Qisqa tavsif
            source: Signal manbai
            signal_type: Signal turi
            evidence: Dalillar
            tags: Teglar
            confidence: Ishonchlilik
            expires_in_hours: Qancha vaqtda eskiradi
        
        Returns:
            Observation obyekti
        """
        obs_id = str(uuid.uuid4())[:12]
        
        # Expires at hisoblash
        expires_at = None
        if expires_in_hours:
            expires_at = datetime.now() + timedelta(hours=expires_in_hours)
        
        observation = Observation(
            id=obs_id,
            source=source,
            timestamp=datetime.now(),
            summary=summary,
            evidence=evidence or {},
            tags=tags or [],
            confidence=confidence,
            novelty=0.5,
            signal_type=signal_type,
            expires_at=expires_at
        )
        
        # Saqlash
        self.observations[obs_id] = observation
        
        # Stats yangilash
        self.ingestion_stats["total_received"] += 1
        source_key = source.value
        self.ingestion_stats["by_source"][source_key] = \
            self.ingestion_stats["by_source"].get(source_key, 0) + 1
        
        type_key = signal_type.value
        self.ingestion_stats["by_type"][type_key] = \
            self.ingestion_stats["by_type"].get(type_key, 0) + 1
        
        logger.info(f"📥 Observation received: {obs_id} from {source.value}")
        
        return observation
    
    def ingest_benchmark_failure(
        self,
        benchmark_name: str,
        failure_reason: str,
        score_drop: float,
        evidence: Optional[dict] = None
    ) -> Observation:
        """Benchmark muvaffaqiyatsizligi"""
        summary = f"Benchmark failure: {benchmark_name} - {failure_reason}"
        
        evidence = evidence or {}
        evidence["benchmark_name"] = benchmark_name
        evidence["score_drop"] = score_drop
        evidence["failure_reason"] = failure_reason
        
        return self.ingest_observation(
            summary=summary,
            source=SignalSource.BENCHMARK,
            signal_type=SignalType.BENCHMARK_FAILURE,
            evidence=evidence,
            tags=["benchmark", "failure", benchmark_name],
            confidence=0.9
        )
    
    def ingest_user_feedback(
        self,
        feedback: str,
        user_id: Optional[str] = None,
        context: Optional[dict] = None
    ) -> Observation:
        """Foydalanuvchi feedbacki"""
        evidence = context or {}
        if user_id:
            evidence["user_id"] = user_id
        
        return self.ingest_observation(
            summary=feedback,
            source=SignalSource.USER,
            signal_type=SignalType.USER_FEEDBACK,
            evidence=evidence,
            tags=["user", "feedback"],
            confidence=0.7
        )
    
    def ingest_regression_alert(
        self,
        module: str,
        issue_description: str,
        severity: str = "high"
    ) -> Observation:
        """Regression alert"""
        evidence = {
            "module": module,
            "severity": severity,
            "issue": issue_description
        }
        
        return self.ingest_observation(
            summary=f"Regression in {module}: {issue_description}",
            source=SignalSource.REGRESSION,
            signal_type=SignalType.REGRESSION_ALERT,
            evidence=evidence,
            tags=["regression", module, severity],
            confidence=0.8
        )
    
    def ingest_competitor_signal(
        self,
        competitor: str,
        capability: str,
        description: str,
        relevance: float = 0.7
    ) -> Observation:
        """Raqobatdosh signal"""
        evidence = {
            "competitor": competitor,
            "capability": capability,
            "description": description
        }
        
        return self.ingest_observation(
            summary=f"{competitor}: {capability} - {description}",
            source=SignalSource.COMPETITOR,
            signal_type=SignalType.COMPETITOR_CAPABILITY,
            evidence=evidence,
            tags=["competitor", capability],
            confidence=relevance
        )
    
    def ingest_research_conclusion(
        self,
        topic: str,
        conclusion: str,
        source_paper: Optional[str] = None
    ) -> Observation:
        """Research xulosa"""
        evidence = {
            "topic": topic,
            "conclusion": conclusion
        }
        if source_paper:
            evidence["source_paper"] = source_paper
        
        return self.ingest_observation(
            summary=f"Research: {topic} - {conclusion[:100]}",
            source=SignalSource.RESEARCH,
            signal_type=SignalType.RESEARCH_CONCLUSION,
            evidence=evidence,
            tags=["research", topic],
            confidence=0.6
        )
    
    def get_observation(self, obs_id: str) -> Optional[Observation]:
        """Observation olish"""
        return self.observations.get(obs_id)
    
    def get_all_observations(self) -> list[Observation]:
        """Barcha observations olish"""
        return list(self.observations.values())
    
    def get_active_observations(self) -> list[Observation]:
        """Faqat faol observations"""
        now = datetime.now()
        return [
            obs for obs in self.observations.values()
            if obs.expires_at is None or obs.expires_at > now
        ]
    
    def remove_observation(self, obs_id: str) -> bool:
        """Observation o'chirish"""
        if obs_id in self.observations:
            del self.observations[obs_id]
            logger.info(f"🗑️ Observation removed: {obs_id}")
            return True
        return False
    
    def get_stats(self) -> dict:
        """Ingestion statistikasi"""
        return {
            "total": self.ingestion_stats["total_received"],
            "active_count": len(self.get_active_observations()),
            "by_source": self.ingestion_stats["by_source"],
            "by_type": self.ingestion_stats["by_type"]
        }


class TriageEngine:
    """
    Triage Engine - Signalarni baholash va saralash
    Bu yerda signal lar "upgrade qilishga arziydimi?" degan savoldan o'tadi
    """
    
    def __init__(self):
        self.watchlist: set[str] = set()
        self.rejected: set[str] = set()
        self.pending_review: set[str] = set()
        logger.info("🔍 TriageEngine initialized")
    
    def triage_observation(self, observation: Observation) -> str:
        """
        Observation ni triage qilish
        
        Returns:
            "watchlist" - kuzatib turish
            "reject" - rad etish
            "candidate_create" - candidate yaratish
            "research_more" - ko'proq tadqiqot
        """
        # Credibility check
        credibility = self._check_credibility(observation)
        observation.credibility_score = credibility
        
        # Novelty check
        novelty = self._check_novelty(observation)
        observation.novelty = novelty
        
        # ROI check
        roi = self._calculate_roi(observation)
        observation.roi_score = roi
        
        # Apply rules
        
        # Rule 1: Past xatolar bo'lsa - reject
        if observation.signal_type == SignalType.BENCHMARK_FAILURE:
            if credibility > 0.7:
                observation.triage_result = "candidate_create"
                self.pending_review.add(observation.id)
                logger.info(f"✅ Benchmark failure approved for candidate: {observation.id}")
                return "candidate_create"
        
        # Rule 2: Past ishonch bo'lsa - reject
        if credibility < 0.3:
            observation.triage_result = "reject"
            self.rejected.add(observation.id)
            logger.info(f"❌ Low credibility rejected: {observation.id}")
            return "reject"
        
        # Rule 3: Past novelty - watchlist
        if novelty < 0.3:
            observation.triage_result = "watchlist"
            self.watchlist.add(observation.id)
            logger.info(f"👀 Low novelty added to watchlist: {observation.id}")
            return "watchlist"
        
        # Rule 4: Yuqori ROI - candidate
        if roi > 0.7 and credibility > 0.5:
            observation.triage_result = "candidate_create"
            self.pending_review.add(observation.id)
            logger.info(f"✅ High ROI approved for candidate: {observation.id}")
            return "candidate_create"
        
        # Rule 5: O'rtacha holat - research more
        observation.triage_result = "research_more"
        logger.info(f"🔬 Marked for research: {observation.id}")
        return "research_more"
    
    def _check_credibility(self, observation: Observation) -> float:
        """
        Signal ishonchliligini tekshirish
        
        Manba bo'yicha boshlang'ich ball
        """
        source_credibility = {
            SignalSource.BENCHMARK: 0.9,
            SignalSource.USER: 0.7,
            SignalSource.OBSERVATION: 0.5,
            SignalSource.REGRESSION: 0.8,
            SignalSource.COMPETITOR: 0.6,
            SignalSource.SOCIAL: 0.4,
            SignalSource.RESEARCH: 0.6,
            SignalSource.INTERNAL: 0.7
        }
        
        base_score = source_credibility.get(observation.source, 0.5)
        
        # Confidence modifier
        confidence_modifier = (observation.confidence - 0.5) * 0.3
        
        # Evidence modifier
        evidence_modifier = 0.0
        if observation.evidence:
            evidence_modifier = min(len(observation.evidence) * 0.05, 0.2)
        
        final_score = base_score + confidence_modifier + evidence_modifier
        return max(0.0, min(1.0, final_score))
    
    def _check_novelty(self, observation: Observation) -> float:
        """
        Signal yangiligini tekshirish
        
        Eski taglar bilan solishtirish
        """
        # Oddiy implementatsiya - real tizimda ML model kerak bo'ladi
        
        # Signal type bo'yicha default novelty
        type_novelty = {
            SignalType.BENCHMARK_FAILURE: 0.7,
            SignalType.USER_FEEDBACK: 0.5,
            SignalType.REGRESSION_ALERT: 0.6,
            SignalType.COMPETITOR_CAPABILITY: 0.8,
            SignalType.SOCIAL_PAIN: 0.4,
            SignalType.RESEARCH_CONCLUSION: 0.7,
            SignalType.NEW_TOOL_OPPORTUNITY: 0.9,
            SignalType.EXTERNAL_OBSERVATION: 0.5
        }
        
        base_novelty = type_novelty.get(observation.signal_type, 0.5)
        
        # Taglar soni (ko'proq teglar - kamroq novelty)
        if observation.tags:
            tag_penalty = len(observation.tags) * 0.02
            base_novelty = max(0.1, base_novelty - tag_penalty)
        
        return max(0.0, min(1.0, base_novelty))
    
    def _calculate_roi(self, observation: Observation) -> float:
        """
        ROI (Return on Investment) hisoblash
        
        Bu signal gaupgrade qilishga arziydimi?
        """
        # Signal type bo'yicha potential ROI
        type_roi = {
            SignalType.BENCHMARK_FAILURE: 0.8,
            SignalType.USER_FEEDBACK: 0.7,
            SignalType.REGRESSION_ALERT: 0.9,
            SignalType.COMPETITOR_CAPABILITY: 0.6,
            SignalType.SOCIAL_PAIN: 0.5,
            SignalType.RESEARCH_CONCLUSION: 0.6,
            SignalType.NEW_TOOL_OPPORTUNITY: 0.8,
            SignalType.EXTERNAL_OBSERVATION: 0.4
        }
        
        base_roi = type_roi.get(observation.signal_type, 0.5)
        
        # Confidence boost
        confidence_boost = observation.confidence * 0.2
        
        # Novelty boost
        novelty_boost = observation.novelty * 0.1
        
        final_roi = base_roi + confidence_boost + novelty_boost
        return max(0.0, min(1.0, final_roi))
    
    def get_watchlist(self) -> list[str]:
        """Watchlist olish"""
        return list(self.watchlist)
    
    def get_pending_review(self) -> list[str]:
        """Review uchun kutyotganlar"""
        return list(self.pending_review)
    
    def get_rejected(self) -> list[str]:
        """Rad etilganlar"""
        return list(self.rejected)


class SignalCourt:
    """
    Signal Court -Signalarni qattiq tekshirish
    Bu yerda muhim signallar qo'shimcha tekshiruvdan o'tadi
    """
    
    def __init__(self):
        self.appeals: dict[str, dict] = {}
        logger.info("⚖️ SignalCourt initialized")
    
    def review_observation(self, observation: Observation) -> dict:
        """
        Observation ni to'liq review qilish
        
        Returns:
            Review natijalari
        """
        review_result = {
            "observation_id": observation.id,
            "approved": False,
            "reasons": [],
            "risk_level": "low",
            "priority": 0
        }
        
        # 1. Evidence tekshirish
        if not observation.evidence:
            review_result["reasons"].append("No evidence provided")
            review_result["priority"] -= 1
        else:
            review_result["reasons"].append("Has evidence")
            review_result["priority"] += 2
        
        # 2. Confidence tekshirish
        if observation.confidence < 0.5:
            review_result["reasons"].append("Low confidence")
            review_result["priority"] -= 2
        else:
            review_result["reasons"].append("Good confidence")
            review_result["priority"] += 1
        
        # 3. Signal type bo'yicha maxsus tekshiruvlar
        if observation.signal_type == SignalType.BENCHMARK_FAILURE:
            if "score_drop" in observation.evidence:
                score_drop = observation.evidence.get("score_drop", 0)
                if score_drop > 0.1:
                    review_result["approved"] = True
                    review_result["risk_level"] = "medium"
                    review_result["priority"] += 3
                    review_result["reasons"].append("Significant benchmark regression")
        
        elif observation.signal_type == SignalType.USER_FEEDBACK:
            review_result["approved"] = True
            review_result["priority"] += 1
            review_result["reasons"].append("User feedback is valuable")
        
        elif observation.signal_type == SignalType.REGRESSION_ALERT:
            severity = observation.evidence.get("severity", "low")
            if severity in ["high", "critical"]:
                review_result["approved"] = True
                review_result["risk_level"] = "high"
                review_result["priority"] += 4
                review_result["reasons"].append(f"Severe regression: {severity}")
        
        # 4. Final decision
        if review_result["priority"] >= 2:
            review_result["approved"] = True
        
        logger.info(f"⚖️ Review result for {observation.id}: approved={review_result['approved']}")
        
        return review_result
    
    def appeal_rejection(self, observation_id: str, reason: str) -> bool:
        """
        Rad etilgan signalni appeal qilish
        """
        self.appeals[observation_id] = {
            "reason": reason,
            "appealed_at": datetime.now().isoformat(),
            "status": "pending"
        }
        logger.info(f"⚖️ Appeal filed for {observation_id}")
        return True


def create_intake_system():
    """
    Intake system yaratish
    
    Barcha intake komponentlarini birlashtiradi
    """
    return {
        "ingest": SignalIngest(),
        "triage": TriageEngine(),
        "court": SignalCourt()
    }
