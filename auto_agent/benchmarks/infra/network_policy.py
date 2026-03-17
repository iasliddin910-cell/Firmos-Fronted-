"""
NetworkPolicyEnforcer - Network Policy Enforcement
=============================================

Tarmoq siyosatini majburiy qilish.

Bu modul:
- none: internet kerak emas
- localhost_only: faqat local
- allowlist_only: ruxsat etilgan domainlar
- replay_only: record/replay only

Definition of Done:
3. Task-level network policy ishlaydi.
"""

from dataclasses import dataclass
from typing import List, Set, Optional
from enum import Enum


class NetworkPolicy(str, Enum):
    """Network policy types."""
    NONE = "none"           # No network access
    LOCALHOST_ONLY = "localhost_only"  # Only localhost
    ALLOWLIST_ONLY = "allowlist_only"  # Only allowlisted domains
    REPLAY_ONLY = "replay_only"  # Recorded replay only
    FULL = "full"         # Full access (testing only)


@dataclass
class NetworkPolicyConfig:
    """Network policy configuration."""
    policy: NetworkPolicy
    allowlist_domains: List[str] = None
    allowlist_ips: List[str] = None
    block_ranges: List[str] = None


class NetworkViolation(Exception):
    """Network violation."""
    pass


class NetworkPolicyEnforcer:
    """
    Network policy enforcer.
    
    Definition of Done:
    3. Task-level network policy ishlaydi.
    """
    
    def __init__(self, config: NetworkPolicyConfig = None):
        self.config = config or NetworkPolicyConfig(
            policy=NetworkPolicy.LOCALHOST_ONLY,
            allowlist_domains=[],
            allowlist_ips=[],
        )
        
        self._allowed_domains = set(config.allowlist_domains) if config.allowlist_domains else set()
        self._allowed_ips = set(config.allowlist_ips) if config.allowlist_ips else set()
    
    def check_connection(self, host: str, port: int = None) -> bool:
        """Connection ruxsatini tekshirish."""
        policy = self.config.policy
        
        if policy == NetworkPolicy.NONE:
            raise NetworkViolation("Network access denied")
        
        elif policy == NetworkPolicy.LOCALHOST_ONLY:
            if host in ["localhost", "127.0.0.1", "::1"]:
                return True
            raise NetworkViolation(f"Connection to {host} denied. Only localhost allowed.")
        
        elif policy == NetworkPolicy.ALLOWLIST_ONLY:
            # Check IP
            if host in self._allowed_ips:
                return True
            
            # Check domain
            for allowed in self._allowed_domains:
                if host == allowed or host.endswith(f".{allowed}"):
                    return True
            
            raise NetworkViolation(f"Connection to {host} not in allowlist")
        
        elif policy == NetworkPolicy.REPLAY_ONLY:
            # Only allow recorded/replay URLs
            if host in self._allowed_ips or host in self._allowed_domains:
                return True
            raise NetworkViolation("Only replay connections allowed")
        
        elif policy == NetworkPolicy.FULL:
            return True
        
        return True
    
    def should_allow(self, url: str) -> bool:
        """URL ruxsatmi?"""
        # Extract host from URL
        from urllib.parse import urlparse
        
        try:
            parsed = urlparse(url)
            host = parsed.hostname or ""
            port = parsed.port
            
            return self.check_connection(host, port)
        except Exception:
            return False
    
    def get_policy_for_task(self, task_metadata: dict) -> NetworkPolicy:
        """Task metadata'dan policy olish."""
        return task_metadata.get("network_policy", NetworkPolicy.LOCALHOST_ONLY)


def create_network_enforcer(policy: NetworkPolicy = NetworkPolicy.LOCALHOST_ONLY) -> NetworkPolicyEnforcer:
    """Network policy enforcer yaratish."""
    config = NetworkPolicyConfig(policy=policy)
    return NetworkPolicyEnforcer(config)
