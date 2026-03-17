"""
CleanEnvBuilder - Clean Environment Builder
======================================

Toza muhit yaratish.

Bu modul:
- Minimal env
- No user creds
- No unrelated tokens
- No host secrets
- Secret scrub

Definition of Done:
4. Secrets task env/log/trace'ga tushmaydi.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional
import os
import re


@dataclass
class EnvConfig:
    """Environment configuration."""
    # Allowed env vars
    allowed_vars: List[str] = field(default_factory=list)
    
    # Blocked patterns
    blocked_patterns: List[str] = field(default_factory=lambda: [
        r"API_KEY",
        r"SECRET",
        r"TOKEN",
        r"PASSWORD",
        r"AUTH",
        r"PRIVATE",
        r"CREDENTIAL",
    ])
    
    # Task-specific vars
    task_vars: Dict[str, str] = field(default_factory=dict)
    
    # System vars to always include
    safe_system_vars: List[str] = field(default_factory=lambda: [
        "PATH",
        "HOME",
        "USER",
        "LANG",
        "LC_ALL",
        "PYTHONPATH",
    ])


class SecretDetected(Exception):
    """Secret detected in env."""
    pass


class CleanEnvBuilder:
    """
    Clean environment builder.
    
    Definition of Done:
    4. Secrets task env/log/trace'ga tushmaydi.
    """
    
    def __init__(self, config: EnvConfig = None):
        self.config = config or EnvConfig()
        
        # Compile blocked patterns
        self._blocked_patterns = [
            re.compile(pattern, re.IGNORECASE) 
            for pattern in self.config.blocked_patterns
        ]
    
    def build_env(
        self,
        additional_vars: Dict[str, str] = None,
    ) -> Dict[str, str]:
        """Toza environment yaratish."""
        env = {}
        
        # Add safe system vars
        for var in self.config.safe_system_vars:
            if var in os.environ:
                env[var] = os.environ[var]
        
        # Add allowed vars
        for var in self.config.allowed_vars:
            if var in os.environ:
                env[var] = os.environ[var]
        
        # Add task vars
        for key, value in self.config.task_vars.items():
            env[key] = value
        
        # Add additional vars
        if additional_vars:
            for key, value in additional_vars.items():
                # Check for secrets
                if self._contains_secret(key, value):
                    raise SecretDetected(f"Secret detected in var: {key}")
                env[key] = value
        
        return env
    
    def _contains_secret(self, key: str, value: str) -> bool:
        """Secret bormi?"""
        # Check key
        for pattern in self._blocked_patterns:
            if pattern.search(key):
                return True
        
        # Check value patterns
        if value and len(value) > 5:
            # Check for common secret patterns
            secret_patterns = [
                r"sk-",  # OpenAI
                r"ghp_",  # GitHub
                r"glpat-",  # GitLab
                r"AKIA",  # AWS
            ]
            for pattern in secret_patterns:
                if re.search(pattern, value):
                    return True
        
        return False
    
    def scrub_value(self, value: str) -> str:
        """Value'dan secret olib tashlash."""
        # Replace potential secrets with ***
        patterns = [
            (r"sk-[a-zA-Z0-9]+", "sk-***"),
            (r"ghp_[a-zA-Z0-9]+", "ghp_***"),
            (r"glpat-[a-zA-Z0-9]+", "glpat-***"),
            (r"AKIA[ A-Z0-9]+", "AKIA***"),
        ]
        
        for pattern, replacement in patterns:
            value = re.sub(pattern, replacement, value)
        
        return value
    
    def scrub_dict(self, data: Dict[str, str]) -> Dict[str, str]:
        """Dict'dagi secretsni tozalash."""
        scrubbed = {}
        for key, value in data.items():
            if self._contains_secret(key, value):
                scrubbed[key] = "***REDACTED***"
            else:
                scrubbed[key] = self.scrub_value(value)
        return scrubbed


def create_clean_env(
    task_vars: Dict[str, str] = None,
    allowed_vars: List[str] = None,
) -> Dict[str, str]:
    """Clean environment yaratish."""
    config = EnvConfig(
        allowed_vars=allowed_vars or [],
        task_vars=task_vars or {},
    )
    builder = CleanEnvBuilder(config)
    return builder.build_env()
