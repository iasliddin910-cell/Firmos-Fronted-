"""
8-BO'LIM: RISK ANALYSIS
======================
Risk Analysis va Mitigation
"""

import logging

logger = logging.getLogger(__name__)

class RiskCategory:
    ARCHITECTURE = 'architecture'
    OPERATIONAL = 'operational'
    EVOLUTION = 'evolution'
    SECURITY = 'security'

class RiskSeverity:
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'

RISKS = {
    'ARCH_001': {'title': 'God Orchestrator', 'severity': 'critical', 'invariant': 'Orchestrator faqat coordination qilsin'},
    'ARCH_002': {'title': 'Contract Chaos', 'severity': 'high', 'invariant': 'Typed contracts majburiy'},
    'ARCH_003': {'title': 'State Corruption', 'severity': 'critical', 'invariant': 'State faqat LifecycleManager orqali'},
    'OP_001': {'title': 'Queue Collapse', 'severity': 'high', 'invariant': 'Hard queue budgets'},
    'OP_002': {'title': 'Clone Bleed', 'severity': 'critical', 'invariant': 'Clone originalga write qilmasin'},
    'OP_003': {'title': 'Oversized Patch', 'severity': 'high', 'invariant': 'ChangeBudget majburiy'},
    'OP_004': {'title': 'Fake Improvement', 'severity': 'high', 'invariant': 'Baseline comparison majburiy'},
    'OP_005': {'title': 'Evaluation Gap', 'severity': 'high', 'invariant': '3 qavatli evaluation'},
    'EV_001': {'title': 'Reporting Laundering', 'severity': 'high', 'invariant': 'Gains/Risks/Unknowns majburiy'},
    'EV_002': {'title': 'Approval Bypass', 'severity': 'critical', 'invariant': 'Human decision for main'},
    'EV_003': {'title': 'Rollback Fiction', 'severity': 'critical', 'invariant': 'Rollback anchor majburiy'},
    'EV_004': {'title': 'Fork Explosion', 'severity': 'medium', 'invariant': 'Fork threshold yuqori'},
    'EV_005': {'title': 'Memory Rot', 'severity': 'medium', 'invariant': 'Decay va revalidation'},
    'RES_001': {'title': 'Resource Exhaustion', 'severity': 'high', 'invariant': 'Resource budget'},
    'SEC_001': {'title': 'Secret Containment', 'severity': 'critical', 'invariant': 'Scoped secrets'},
    'SEC_002': {'title': 'Tool Chaos', 'severity': 'high', 'invariant': 'Tool tests majburiy'},
}

class RiskRegister:
    def __init__(self):
        self.risks = RISKS
        logger.info(f'⚠️ RiskRegister: {len(self.risks)} risks')

    def get_risk(self, id):
        return self.risks.get(id)

    def get_all_invariants(self):
        return [r['invariant'] for r in self.risks.values()]

class PolicyGuard:
    def __init__(self):
        logger.info('🛡️ PolicyGuard initialized')

    def check_human_decision(self, record):
        return record.get('by') == 'human'

    def check_rollback_anchor(self, record):
        return bool(record.get('anchor'))

    def check_trust(self, trust, dest):
        thresholds = {'main': 0.8, 'canary': 0.6}
        return trust >= thresholds.get(dest, 0)

__all__ = ['RiskCategory', 'RiskSeverity', 'RiskRegister', 'PolicyGuard', 'RISKS']
