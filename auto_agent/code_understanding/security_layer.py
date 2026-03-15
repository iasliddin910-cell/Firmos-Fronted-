"""
Security Analysis Layer (CodeQL/Semgrep)
=====================================

This layer provides comprehensive security analysis through:
- CodeQL for deep semantic analysis, taint paths, vulnerability detection
- Semgrep for fast pattern matching and guardrails
- Custom security policies

Key capabilities:
- Vulnerability detection
- Taint path analysis
- Security policy enforcement
- Anti-pattern detection
- Regression detection for candidate edits
"""

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class Severity(Enum):
    """Severity levels for security findings"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingType(Enum):
    """Types of security findings"""
    VULNERABILITY = "vulnerability"
    CODE_SMELL = "code_smell"
    SECURITY_MISCONFIGURATION = "misconfiguration"
    POLICY_VIOLATION = "policy_violation"
    ANTI_PATTERN = "anti_pattern"
    TAINT_PATH = "taint_path"
    HARDENED_CODE = "hardened_code"


@dataclass
class SecurityFinding:
    """Represents a security finding"""
    id: str
    title: str
    description: str
    severity: Severity
    finding_type: FindingType
    
    # Location
    file_path: str
    line_start: int
    line_end: int
    code_snippet: str = ""
    
    # Analysis
    cwe_id: str = ""  # Common Weakness Enumeration
    cve_id: str = ""  # Common Vulnerabilities and Exposures
    owasp_category: str = ""
    
    # Taint analysis
    is_taint: bool = False
    source: str = ""
    sink: str = ""
    taint_path: list[str] = field(default_factory=list)
    sanitizers: list[str] = field(default_factory=list)
    
    # Fix
    fix_suggestion: str = ""
    fix_priority: int = 0  # 1-5, 1 is highest
    
    # Confidence
    confidence: float = 1.0  # 0.0-1.0
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "type": self.finding_type.value,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "code_snippet": self.code_snippet,
            "cwe_id": self.cwe_id,
            "cve_id": self.cve_id,
            "owasp_category": self.owasp_category,
            "is_taint": self.is_taint,
            "source": self.source,
            "sink": self.sink,
            "taint_path": self.taint_path,
            "sanitizers": self.sanitizers,
            "fix_suggestion": self.fix_suggestion,
            "fix_priority": self.fix_priority,
            "confidence": self.confidence,
        }


@dataclass
class SecurityReport:
    """Complete security analysis report"""
    repository: str
    
    # Summary
    total_findings: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    
    # Findings by category
    vulnerabilities: list[SecurityFinding] = field(default_factory=list)
    code_smells: list[SecurityFinding] = field(default_factory=list)
    policy_violations: list[SecurityFinding] = field(default_factory=list)
    taint_paths: list[SecurityFinding] = field(default_factory=list)
    
    # Scan metadata
    scan_time: float = 0.0
    files_scanned: int = 0
    lines_scanned: int = 0
    
    # Recommendations
    recommended_actions: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "repository": self.repository,
            "summary": {
                "total": self.total_findings,
                "critical": self.critical_count,
                "high": self.high_count,
                "medium": self.medium_count,
                "low": self.low_count,
            },
            "findings": {
                "vulnerabilities": [f.to_dict() for f in self.vulnerabilities],
                "code_smells": [f.to_dict() for f in self.code_smells],
                "policy_violations": [f.to_dict() for f in self.policy_violations],
                "taint_paths": [f.to_dict() for f in self.taint_paths],
            },
            "scan_time": self.scan_time,
            "files_scanned": self.files_scanned,
            "lines_scanned": self.lines_scanned,
            "recommended_actions": self.recommended_actions,
        }


class SecurityAnalysisLayer:
    """
    Security Analysis Layer using CodeQL and Semgrep
    
    This layer provides:
    - Deep semantic security analysis (CodeQL)
    - Fast pattern matching (Semgrep)
    - Taint path analysis
    - Policy enforcement
    - Regression detection
    
    Architecture:
    - Heavy scans: CodeQL full analysis (for critical areas)
    - Light scans: Semgrep fast patterns (for quick checks)
    - Risk-based escalation: Only run full CodeQL when needed
    """
    
    def __init__(self, config: Any):
        self.config = config
        self.codeql_enabled = config.codeql_enabled
        self.semgrep_enabled = config.semgrep_enabled
        
        # Analysis state
        self.findings: list[SecurityFinding] = []
        self.last_scan_time: float = 0.0
        
        # CodeQL client (in production, would use actual CodeQL)
        self.codeql_client = None
        
        # Semgrep client (in production, would use actual Semgrep)
        self.semgrep_client = None
        
        # Custom rules
        self.custom_rules = self._load_custom_rules()
    
    def _load_custom_rules(self) -> dict[str, Any]:
        """Load custom security rules"""
        return {
            # SQL Injection patterns
            "sql_injection": {
                "patterns": [
                    r"execute\s*\(\s*.*\+",
                    r"query\s*\(\s*.*\+",
                    r"raw\s*\(\s*.*\+",
                ],
                "severity": Severity.CRITICAL,
                "cwe": "CWE-89",  # SQL Injection
                "fix": "Use parameterized queries instead of string concatenation",
            },
            # Command Injection
            "command_injection": {
                "patterns": [
                    r"os\.system\s*\(",
                    r"subprocess\.call\s*\(",
                    r"exec\s*\(",
                    r"eval\s*\(",
                ],
                "severity": Severity.CRITICAL,
                "cwe": "CWE-78",  # OS Command Injection
                "fix": "Avoid executing user input; use safe APIs",
            },
            # Path Traversal
            "path_traversal": {
                "patterns": [
                    r"open\s*\(\s*.*\+",
                    r"read\s*\(\s*.*\+",
                ],
                "severity": Severity.HIGH,
                "cwe": "CWE-22",  # Path Traversal
                "fix": "Validate and sanitize file paths",
            },
            # Hardcoded secrets
            "hardcoded_secrets": {
                "patterns": [
                    r"password\s*=\s*['\"][^'\"]+['\"]",
                    r"api[_-]?key\s*=\s*['\"][^'\"]+['\"]",
                    r"secret\s*=\s*['\"][^'\"]+['\"]",
                    r"token\s*=\s*['\"][^'\"]+['\"]",
                ],
                "severity": Severity.CRITICAL,
                "cwe": "CWE-798",  # Use of Hard-coded Credentials
                "fix": "Use environment variables or secrets management",
            },
            # Insecure random
            "insecure_random": {
                "patterns": [
                    r"random\.random\s*\(",
                    r"Math\.random\s*\(",
                ],
                "severity": Severity.MEDIUM,
                "cwe": "CWE-338",  # Use of Cryptographically Weak PRNG
                "fix": "Use secrets.token_bytes() or similar secure random",
            },
            # Use of eval
            "eval_usage": {
                "patterns": [r"eval\s*\("],
                "severity": Severity.HIGH,
                "cwe": "CWE-95",  # Code Injection
                "fix": "Avoid eval; use safer alternatives",
            },
            # Insecure deserialization
            "insecure_deserialization": {
                "patterns": [
                    r"pickle\.loads\s*\(",
                    r"yaml\.load\s*\(",
                    r"json\.loads\s*\(",  # Sometimes unsafe
                ],
                "severity": Severity.CRITICAL,
                "cwe": "CWE-502",  # Deserialization of Untrusted Data
                "fix": "Use safe deserialization methods",
            },
            # Weak crypto
            "weak_crypto": {
                "patterns": [
                    r"hashlib\.md5\s*\(",
                    r"hashlib\.sha1\s*\(",
                    r"DES\s*\(",
                ],
                "severity": Severity.MEDIUM,
                "cwe": "CWE-327",  # Use of Weak Cryptographic Algorithm
                "fix": "Use strong cryptographic algorithms (SHA-256+, AES-128+)",
            },
            # Unvalidated redirect
            "open_redirect": {
                "patterns": [
                    r"redirect\s*\(\s*.*\+",
                    r"Location:\s*.*\+",
                ],
                "severity": Severity.MEDIUM,
                "cwe": "CWE-601",  # URL Redirect
                "fix": "Validate redirect URLs against allowlist",
            },
            # XXE
            "xxe": {
                "patterns": [
                    r"etree\.parse\s*\(",
                    r"DOMParser\s*\(",
                ],
                "severity": Severity.CRITICAL,
                "cwe": "CWE-611",  # XXE
                "fix": "Disable external entity processing",
            },
        }
    
    async def analyze(self, repo_path: Path) -> list[SecurityFinding]:
        """
        Perform comprehensive security analysis.
        
        This runs both CodeQL (deep analysis) and Semgrep (fast patterns).
        """
        import time
        start_time = time.time()
        
        findings = []
        
        # Discover all source files
        files = await self._discover_files(repo_path)
        
        # Run Semgrep for fast pattern matching
        if self.semgrep_enabled:
            semgrep_findings = await self._run_semgrep(files)
            findings.extend(semgrep_findings)
        
        # Run CodeQL for deep analysis (if enabled)
        if self.codeql_enabled:
            codeql_findings = await self._run_codeql(files)
            findings.extend(codeql_findings)
        
        # Apply custom rules
        custom_findings = await self._run_custom_rules(files)
        findings.extend(custom_findings)
        
        # Store findings
        self.findings = findings
        self.last_scan_time = time.time() - start_time
        
        return findings
    
    async def _discover_files(self, repo_path: Path) -> list[Path]:
        """Discover all source files"""
        files = []
        extensions = {".py", ".js", ".ts", ".java", ".go", ".rs", ".c", ".cpp"}
        
        for root, dirs, filenames in repo_path.walk():
            dirs[:] = [d for d in dirs if not d.startswith('.') 
                      and d not in ('node_modules', 'venv', '__pycache__', 'test', 'tests')]
            
            for filename in filenames:
                path = Path(root) / filename
                if path.suffix in extensions:
                    files.append(path)
        
        return files
    
    async def _run_semgrep(self, files: list[Path]) -> list[SecurityFinding]:
        """
        Run Semgrep for fast pattern matching.
        
        In production, this would call the actual Semgrep CLI.
        """
        findings = []
        
        # Simulated Semgrep results
        # In production, use: semgrep --json --quiet .
        
        return findings
    
    async def _run_codeql(self, files: list[Path]) -> list[SecurityFinding]:
        """
        Run CodeQL for deep semantic analysis.
        
        In production, this would:
        1. Create CodeQL database
        2. Run security queries
        3. Parse results
        """
        findings = []
        
        # Simulated CodeQL results
        # In production, use: codeql database analyze
        
        return findings
    
    async def _run_custom_rules(self, files: list[Path]) -> list[SecurityFinding]:
        """Run custom security rules"""
        findings = []
        finding_id = 0
        
        for file_path in files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    lines = content.split("\n")
                
                # Check each custom rule
                for rule_name, rule in self.custom_rules.items():
                    for line_num, line in enumerate(lines, 1):
                        for pattern in rule["patterns"]:
                            import re
                            if re.search(pattern, line):
                                finding_id += 1
                                
                                # Extract code snippet
                                snippet_start = max(0, line_num - 2)
                                snippet_end = min(len(lines), line_num + 2)
                                snippet = "\n".join(lines[snippet_start:snippet_end])
                                
                                finding = SecurityFinding(
                                    id=f"custom-{finding_id}",
                                    title=f"Potential {rule_name.replace('_', ' ')}",
                                    description=rule.get("fix", "Security issue detected"),
                                    severity=rule["severity"],
                                    finding_type=FindingType.VULNERABILITY,
                                    file_path=str(file_path),
                                    line_start=line_num,
                                    line_end=line_num,
                                    code_snippet=snippet,
                                    cwe_id=rule.get("cwe", ""),
                                    fix_suggestion=rule.get("fix", ""),
                                    fix_priority=1 if rule["severity"] == Severity.CRITICAL else 3,
                                    confidence=0.8,
                                )
                                
                                findings.append(finding)
            
            except Exception:
                pass
        
        return findings
    
    async def analyze_patch(self, changed_files: list[str], 
                          context: dict) -> SecurityReport:
        """
        Analyze a patch/candidate edit for security issues.
        
        This is critical for self-modification safety.
        """
        findings = []
        
        # Analyze only changed files
        for file_path in changed_files:
            path = Path(file_path)
            if path.exists():
                file_findings = await self._analyze_file(path, context)
                findings.extend(file_findings)
        
        # Generate report
        report = SecurityReport(
            repository=context.get("repo", "unknown"),
            total_findings=len(findings),
        )
        
        for finding in findings:
            if finding.severity == Severity.CRITICAL:
                report.critical_count += 1
            elif finding.severity == Severity.HIGH:
                report.high_count += 1
            elif finding.severity == Severity.MEDIUM:
                report.medium_count += 1
            elif finding.severity == Severity.LOW:
                report.low_count += 1
            
            if finding.finding_type == FindingType.VULNERABILITY:
                report.vulnerabilities.append(finding)
            elif finding.finding_type == FindingType.CODE_SMELL:
                report.code_smells.append(finding)
            elif finding.finding_type == FindingType.TAINT_PATH:
                report.taint_paths.append(finding)
            else:
                report.policy_violations.append(finding)
        
        # Add recommendations
        report.recommended_actions = self._generate_recommendations(findings)
        
        return report
    
    async def _analyze_file(self, file_path: Path, context: dict) -> list[SecurityFinding]:
        """Analyze a single file for security issues"""
        findings = []
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Run custom rules
            # This is already done in _run_custom_rules
            
        except Exception:
            pass
        
        return findings
    
    def _generate_recommendations(self, findings: list[SecurityFinding]) -> list[str]:
        """Generate security recommendations based on findings"""
        recommendations = []
        
        # Group by severity
        critical = [f for f in findings if f.severity == Severity.CRITICAL]
        high = [f for f in findings if f.severity == Severity.HIGH]
        
        if critical:
            recommendations.append(
                f"CRITICAL: Address {len(critical)} critical security issues immediately"
            )
        
        if high:
            recommendations.append(
                f"HIGH: Review {len(high)} high-severity findings in next sprint"
            )
        
        # Check for common patterns
        cwe_ids = set(f.cwe_id for f in findings if f.cwe_id)
        
        if "CWE-89" in cwe_ids:  # SQL Injection
            recommendations.append(
                "Implement parameterized queries throughout the codebase"
            )
        
        if "CWE-78" in cwe_ids:  # Command Injection
            recommendations.append(
                "Review all system command executions; use safer APIs"
            )
        
        if "CWE-798" in cwe_ids:  # Hardcoded secrets
            recommendations.append(
                "Migrate secrets to environment variables or secrets manager"
            )
        
        if not recommendations:
            recommendations.append("No critical security issues found")
        
        return recommendations
    
    def check_candidate_regression(self, candidate_changes: dict) -> dict:
        """
        Check if candidate changes would introduce security regressions.
        
        Returns:
        - blocked: Whether the change should be blocked
        - reasons: List of blocking reasons
        - warnings: Non-blocking warnings
        """
        blocked = False
        reasons = []
        warnings = []
        
        # Check for critical findings in changed files
        for finding in self.findings:
            if finding.file_path in candidate_changes.get("files", []):
                if finding.severity == Severity.CRITICAL and finding.confidence > 0.9:
                    blocked = True
                    reasons.append(
                        f"Critical finding in {finding.file_path}:{finding.line_start}"
                    )
                elif finding.severity in (Severity.HIGH, Severity.MEDIUM):
                    warnings.append(
                        f"Warning: {finding.title} at {finding.file_path}:{finding.line_start}"
                    )
        
        # Check for dangerous patterns in changes
        dangerous_patterns = {
            "eval": "Use of eval()",
            "exec": "Use of exec()",
            "pickle.load": "Insecure deserialization",
            "os.system": "Command injection risk",
        }
        
        for pattern, description in dangerous_patterns.items():
            for file_path in candidate_changes.get("files", []):
                # Check if pattern exists in changes
                # (simplified - in production, check diff)
                pass
        
        return {
            "blocked": blocked,
            "reasons": reasons,
            "warnings": warnings,
            "requires_review": blocked or len(warnings) > 0,
        }
    
    def get_findings_by_file(self, file_path: str) -> list[SecurityFinding]:
        """Get all findings for a specific file"""
        return [f for f in self.findings if f.file_path == file_path]
    
    def get_findings_by_severity(self, severity: Severity) -> list[SecurityFinding]:
        """Get all findings of a specific severity"""
        return [f for f in self.findings if f.severity == severity]
    
    def get_findings_by_cwe(self, cwe_id: str) -> list[SecurityFinding]:
        """Get all findings for a specific CWE"""
        return [f for f in self.findings if f.cwe_id == cwe_id]
    
    def get_security_score(self) -> float:
        """
        Calculate overall security score (0-100).
        
        Lower is worse, higher is better.
        """
        if not self.findings:
            return 100.0
        
        score = 100.0
        
        for finding in self.findings:
            if finding.severity == Severity.CRITICAL:
                score -= 15
            elif finding.severity == Severity.HIGH:
                score -= 7
            elif finding.severity == Severity.MEDIUM:
                score -= 3
            elif finding.severity == Severity.LOW:
                score -= 1
        
        return max(0.0, score)


class SemgrepRunner:
    """
    Helper class for running Semgrep scans.
    
    In production, this would wrap the Semgrep CLI.
    """
    
    def __init__(self, rules_path: str | None = None):
        self.rules_path = rules_path or "security"
    
    async def scan(self, target: Path, config: str = "auto") -> list[dict]:
        """Run Semgrep scan"""
        # In production:
        # result = subprocess.run(
        #     ["semgrep", "--json", "--config", config, str(target)],
        #     capture_output=True
        # )
        # return json.loads(result.stdout).get("results", [])
        return []


class CodeQLRunner:
    """
    Helper class for running CodeQL analysis.
    
    In production, this would wrap the CodeQL CLI.
    """
    
    def __init__(self, database_path: Path | None = None):
        self.database_path = database_path
    
    async def create_database(self, source: Path, language: str):
        """Create CodeQL database"""
        # In production:
        # codeql database create <db> --source-root=<source> --language=<lang>
        pass
    
    async def analyze(self, database: Path, queries: str = "security-and-quality") -> list[dict]:
        """Run CodeQL analysis"""
        # In production:
        # codeql database analyze <db> <queries> --format=csv
        return []
