"""
OmniAgent X - Secret Isolation Guard
=====================================
Protect sensitive data from agent access

Features:
- Secret detection and blocking
- Environment variable protection
- File-based secret redaction
- Audit logging
- Secret access requests
"""
import os
import re
import logging
import json
import time
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass
from enum import Enum
import hashlib

logger = logging.getLogger(__name__)


# ==================== ENUMS ====================

class SecretType(Enum):
    """Types of secrets"""
    API_KEY = "api_key"
    PASSWORD = "password"
    TOKEN = "token"
    PRIVATE_KEY = "private_key"
    CREDENTIALS = "credentials"
    SECRET = "secret"


# ==================== DATA CLASSES ====================

@dataclass
class SecretPattern:
    """Pattern for detecting secrets"""
    name: str
    pattern: re.Pattern
    secret_type: SecretType
    severity: str  # high, medium, low


@dataclass
class SecretAccess:
    """Record of secret access attempt"""
    access_id: str
    secret_type: SecretType
    source: str  # file, env, command
    timestamp: float
    granted: bool
    reason: str


# ==================== SECRET DETECTOR ====================

class SecretDetector:
    """
    Detect secrets in text and files
    """
    
    # Patterns for common secrets
    PATTERNS = [
        SecretPattern(
            name="AWS Access Key",
            pattern=re.compile(r'AKIA[0-9A-Z]{16}'),
            secret_type=SecretType.API_KEY,
            severity="high"
        ),
        SecretPattern(
            name="GitHub Token",
            pattern=re.compile(r'gh[pousr]_[A-Za-z0-9_]{36,255}'),
            secret_type=SecretType.TOKEN,
            severity="high"
        ),
        SecretPattern(
            name="OpenAI API Key",
            pattern=re.compile(r'sk-[A-Za-z0-9]{32,}'),
            secret_type=SecretType.API_KEY,
            severity="high"
        ),
        SecretPattern(
            name="Generic API Key",
            pattern=re.compile(r'(?i)(api[_-]?key|apikey)\s*[:=]\s*[\'"]?[\w-]{20,}'),
            secret_type=SecretType.API_KEY,
            severity="medium"
        ),
        SecretPattern(
            name="Password in URL",
            pattern=re.compile(r'://[\w-]+:([^@]+)@'),
            secret_type=SecretType.PASSWORD,
            severity="high"
        ),
        SecretPattern(
            name="Private Key",
            pattern=re.compile(r'-----BEGIN (?:RSA |EC )?PRIVATE KEY-----'),
            secret_type=SecretType.PRIVATE_KEY,
            severity="critical"
        ),
        SecretPattern(
            name="JWT Token",
            pattern=re.compile(r'eyJ[A-Za-z0-9-_]+\.eyJ[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+'),
            secret_type=SecretType.TOKEN,
            severity="medium"
        ),
        SecretPattern(
            name="Generic Secret",
            pattern=re.compile(r'(?i)(password|passwd|pwd|secret)\s*[:=]\s*[\'"]?[^\s\'"]{8,}'),
            secret_type=SecretType.SECRET,
            severity="medium"
        ),
        SecretPattern(
            name="Bearer Token",
            pattern=re.compile(r'(?i)bearer\s+[A-Za-z0-9\-_\.]+'),
            secret_type=SecretType.TOKEN,
            severity="medium"
        ),
        SecretPattern(
            name="Telegram Token",
            pattern=re.compile(r'\d{8,10}:[A-Za-z0-9_-]{35}'),
            secret_type=SecretType.TOKEN,
            severity="high"
        ),
    ]
    
    # Protected environment variables
    PROTECTED_ENV_VARS = {
        "OPENAI_API_KEY", "API_KEY", "SECRET_KEY", "PRIVATE_KEY",
        "PASSWORD", "PASSWD", "TOKEN", "AUTH_TOKEN", "ACCESS_TOKEN",
        "GITHUB_TOKEN", "GITLAB_TOKEN", "TELEGRAM_BOT_TOKEN",
        "DATABASE_URL", "DB_PASSWORD", "DB_SECRET",
        "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY",
        "STRIPE_API_KEY", "STRIPE_SECRET",
    }
    
    def __init__(self):
        self.detected_secrets: List[Dict] = []
        
        logger.info("🔐 Secret Detector initialized")
    
    def scan_text(self, text: str) -> List[Dict]:
        """Scan text for secrets"""
        
        found = []
        
        for secret_pattern in self.PATTERNS:
            matches = secret_pattern.pattern.finditer(text)
            
            for match in matches:
                found.append({
                    "type": secret_pattern.secret_type.value,
                    "name": secret_pattern.name,
                    "severity": secret_pattern.severity,
                    "matched": match.group()[:20] + "...",  # Truncate
                    "position": match.span()
                })
        
        self.detected_secrets.extend(found)
        
        return found
    
    def scan_file(self, filepath: str) -> List[Dict]:
        """Scan file for secrets"""
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            return self.scan_text(content)
        
        except Exception as e:
            logger.error(f"Error scanning file {filepath}: {e}")
            return []
    
    def scan_command(self, command: str) -> List[Dict]:
        """Scan command for secrets"""
        
        return self.scan_text(command)
    
    def is_protected_env_var(self, var_name: str) -> bool:
        """Check if environment variable is protected"""
        
        return var_name.upper() in self.PROTECTED_ENV_VARS


# ==================== SECRET GUARD ====================

class SecretGuard:
    """
    Guard for protecting secrets
    """
    
    def __init__(self):
        self.detector = SecretDetector()
        self.access_log: List[SecretAccess] = []
        self.blocked_accesses: Set[str] = set()
        
        # Redaction pattern
        self.redaction_pattern = re.compile(r'[A-Za-z0-9\-_]{8,}')
        
        logger.info("🔐 Secret Guard initialized")
    
    def redact(self, text: str) -> str:
        """Redact secrets from text"""
        
        redacted = text
        
        for secret_pattern in self.detector.PATTERNS:
            redacted = secret_pattern.pattern.sub('[REDACTED]', redacted)
        
        return redacted
    
    def redact_dict(self, data: Dict) -> Dict:
        """Recursively redact secrets in dictionary"""
        
        redacted = {}
        
        for key, value in data.items():
            if self.detector.is_protected_env_var(key):
                redacted[key] = "[REDACTED]"
            elif isinstance(value, dict):
                redacted[key] = self.redact_dict(value)
            elif isinstance(value, str):
                redacted[key] = self.redact(value)
            else:
                redacted[key] = value
        
        return redacted
    
    def check_env_access(self, var_name: str, source: str = "agent") -> bool:
        """Check if agent can access environment variable"""
        
        if self.detector.is_protected_env_var(var_name):
            # Log access attempt
            access = SecretAccess(
                access_id=hashlib.md5(f"{var_name}{time.time()}".encode()).hexdigest()[:12],
                secret_type=SecretType.SECRET,
                source=source,
                timestamp=time.time(),
                granted=False,
                reason="Protected environment variable"
            )
            
            self.access_log.append(access)
            self.blocked_accesses.add(var_name)
            
            logger.warning(f"🔒 Blocked access to protected env var: {var_name}")
            
            return False
        
        return True
    
    def get_env(self, var_name: str, default: Any = None) -> Any:
        """Get environment variable with protection"""
        
        if not self.check_env_access(var_name, "get_env"):
            return default
        
        return os.getenv(var_name, default)
    
    def get_all_env(self) -> Dict[str, str]:
        """Get all non-protected environment variables"""
        
        env = {}
        
        for key, value in os.environ.items():
            if not self.detector.is_protected_env_var(key):
                env[key] = value
        
        return env
    
    def filter_command(self, command: str) -> str:
        """Filter secrets from command"""
        
        # Check for secret access
        for secret_pattern in self.detector.PATTERNS:
            if secret_pattern.pattern.search(command):
                logger.warning(f"🔒 Command contains potential secret pattern: {secret_pattern.name}")
        
        return self.redact(command)
    
    def get_access_log(self, limit: int = 100) -> List[Dict]:
        """Get access log"""
        
        return [
            {
                "access_id": a.access_id,
                "secret_type": a.secret_type.value,
                "source": a.source,
                "timestamp": a.timestamp,
                "granted": a.granted,
                "reason": a.reason
            }
            for a in self.access_log[-limit:]
        ]
    
    def get_stats(self) -> Dict:
        """Get guard statistics"""
        
        total = len(self.access_log)
        blocked = sum(1 for a in self.access_log if not a.granted)
        
        return {
            "total_accesses": total,
            "blocked_accesses": blocked,
            "protected_vars": len(self.detector.PROTECTED_ENV_VARS),
            "secret_patterns": len(self.detector.PATTERNS)
        }


# ==================== SECRET MANAGER ====================

class SecretManager:
    """
    Manage secrets securely
    """
    
    def __init__(self, workspace_dir: str = None):
        self.workspace_dir = workspace_dir or os.getcwd()
        self.guard = SecretGuard()
        
        # Secret storage (encrypted in production)
        self.secrets_file = os.path.join(self.workspace_dir, ".secrets.enc")
        
        logger.info("🔐 Secret Manager initialized")
    
    def get_secret(self, key: str) -> Optional[str]:
        """Get a secret"""
        
        # Check if allowed
        if not self.guard.check_env_access(key, "get_secret"):
            return None
        
        # Try environment first
        value = os.getenv(key)
        
        if value:
            return value
        
        # Try secrets file
        # (In production, this would be decrypted)
        return None
    
    def set_secret(self, key: str, value: str):
        """Set a secret"""
        
        # Don't allow setting protected keys
        if self.guard.detector.is_protected_env_var(key):
            raise ValueError(f"Cannot set protected key: {key}")
        
        # Set in environment
        os.environ[key] = value
    
    def list_secrets(self) -> List[str]:
        """List available secrets (not values)"""
        
        secrets = []
        
        # From environment (non-protected)
        for key in os.environ:
            if not self.guard.detector.is_protected_env_var(key):
                secrets.append(key)
        
        return sorted(secrets)
    
    def delete_secret(self, key: str) -> bool:
        """Delete a secret"""
        
        if key in os.environ:
            del os.environ[key]
            return True
        
        return False


# ==================== FACTORY ====================

def create_secret_guard() -> SecretGuard:
    """Create secret guard"""
    return SecretGuard()

def create_secret_manager(workspace_dir: str = None) -> SecretManager:
    """Create secret manager"""
    return SecretManager(workspace_dir)
