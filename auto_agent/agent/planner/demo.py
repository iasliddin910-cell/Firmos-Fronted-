#!/usr/bin/env python3
"""
Change Planner Demo
==================
Bu skript Change Planner & Patch Strategy Engine ni ishga tushiradi.

Ishlatish:
    cd agent/planner
    python3 demo.py
"""

import asyncio
import sys
import os

# Add project to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from agent.planner import (
    ChangePlanner, PlanningResult,
    GoalSpec, EditContract, EditPlan, ProofObligation,
    RiskAssessment, PatchFamily, ChangeType, ChangePhase, RiskLevel
)


async def run_demo():
    """Demo of Change Planner."""
    
    print("=" * 70)
    print("🧠 OmniAgent X - Change Planner & Patch Strategy Engine Demo")
    print("=" * 70)
    print()
    
    # Initialize planner
    planner = ChangePlanner()
    
    # Test cases
    test_cases = [
        {
            'request': 'fix the authentication bug in login function',
            'description': 'Bugfix - kichik tuzatish'
        },
        {
            'request': 'optimize API latency: reduce p95 from 500ms to 200ms',
            'description': 'Performance optimization'
        },
        {
            'request': 'rename UserService class to AccountService across all files',
            'description': 'Semantic refactor - class rename'
        },
        {
            'request': 'migrate from requests to httpx library',
            'description': 'Dependency migration'
        },
        {
            'request': 'implement new caching algorithm for better performance',
            'description': 'Behavioral rewrite'
        }
    ]
    
    # Mock code analysis
    code_analysis = {
        'files': ['api.py', 'handler.py', 'database.py', 'auth.py', 'cache.py'],
        'symbols': {
            'login': {'critical': True},
            'authenticate': {'security_sensitive': True},
            'cache_get': {'hot_path': True}
        },
        'functions': {
            'handle_request': {'hot_path': True},
            'process_response': {},
            'validate_token': {'security': True}
        },
        'classes': {
            'UserService': {'parent_classes': ['BaseService']},
            'CacheManager': {}
        },
        'call_graph': {
            'login': ['authenticate', 'validate_token'],
            'handle_request': ['process_response']
        },
        'security_sensitive': True
    }
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*70}")
        print(f"📌 Test {i}: {test['description']}")
        print(f"{'='*70}")
        print(f"Request: {test['request']}")
        
        # Run planning
        result = await planner.plan(test['request'], code_analysis)
        
        if result.success:
            print(f"\n✅ Planning muvaffaqiyatli!")
            print(f"\n📋 Contract:")
            print(f"   ID: {result.contract.contract_id}")
            print(f"   Type: {result.contract.change_type.value}")
            print(f"   Family: {result.contract.patch_family.value}")
            
            print(f"\n📊 Plans:")
            for plan in result.plans:
                phases = [p.value for p in plan.phases]
                print(f"   {plan.plan_type:12s} | Score: {plan.total_score:5.1f} | Phases: {phases}")
            
            if result.risk_assessment:
                print(f"\n⚠️  Risk:")
                print(f"   Level: {result.risk_assessment.risk_level.value}")
                print(f"   Score: {result.risk_assessment.risk_score:.1f}")
                print(f"   Reversible: {result.risk_assessment.reversible}")
        else:
            print(f"❌ Xatolik: {result.error}")
    
    # Print metrics
    print(f"\n{'='*70}")
    print("📈 Planner Metrics")
    print(f"{'='*70}")
    metrics = planner.get_metrics()
    print(f"Jami rejalashtirishlar: {metrics['planning_count']}")
    
    print(f"\n{'='*70}")
    print("🎉 Demo yakunlandi!")
    print(f"{'='*70}")


if __name__ == '__main__':
    asyncio.run(run_demo())
