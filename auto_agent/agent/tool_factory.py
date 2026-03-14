"""OmniAgent X - Enhanced Tool Factory with safety, versioning, rollback"""

import os, json, logging, time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import re, ast

logger = logging.getLogger(__name__)

class ToolStatus(Enum):
    PROPOSED, GENERATING, TESTING, BENCHMARKING, APPROVED, ACTIVE, DEPRECATED, REJECTED, ROLLBACK =         "proposed", "generating", "testing", "benchmarking", "approved", "active", "deprecated", "rejected", "rollback"

class BenchmarkResult(Enum):
    PASS, FAIL, TIMEOUT, ERROR = "pass", "fail", "timeout", "error"

class SafetyLevel(Enum):
    SAFE, RESTRICTED, DANGEROUS = "safe", "restricted", "dangerous"

@dataclass
class ToolSpec:
    name: str; description: str; category: str
    parameters: Dict[str, Any]; returns: Dict[str, Any]
    examples: List[Dict] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    safety_level: SafetyLevel = SafetyLevel.SAFE
    required_permissions: List[str] = field(default_factory=list)

@dataclass
class ToolVersion:
    version: str; code: str; tests: str
    benchmark_results: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    status: ToolStatus = ToolStatus.TESTING
    created_by: str = "system"; changelog: str = ""; breaking: bool = False

@dataclass
class ToolMetadata:
    name: str; description: str; category: str; current_version: str
    versions: List[str] = field(default_factory=list)
    status: ToolStatus = ToolStatus.PROPOSED
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    created_by: str = "system"
    usage_count: int = 0; success_rate: float = 1.0; avg_latency: float = 0.0
    tags: List[str] = field(default_factory=list)

class SafetyValidator:
    DANGEROUS = [r"os\.system\(", r"subprocess\.", r"eval\(", r"exec\(", r"__import__\(", r"open\([^)]*['\"]w['\"]"]
    RESTRICTED = [r"requests\.", r"urllib\.", r"http\.", r"open\("]
    
    def __init__(self):
        self.dr = [re.compile(p) for p in self.DANGEROUS]
        self.rr = [re.compile(p) for p in self.RESTRICTED]
    
    def validate(self, code: str) -> Dict:
        issues, warnings = [], []
        for p in self.dr:
            if p.findall(code): issues.append({"type": "dangerous", "pattern": p.pattern})
        for p in self.rr:
            if p.findall(code): warnings.append({"type": "restricted", "pattern": p.pattern})
        try: ast.parse(code)
        except SyntaxError as e: issues.append({"type": "syntax_error", "message": str(e)})
        level = SafetyLevel.DANGEROUS if issues else (SafetyLevel.RESTRICTED if warnings else SafetyLevel.SAFE)
        return {"safe": not issues, "safety_level": level, "issues": issues, "warnings": warnings}

class BenchmarkEngine:
    def __init__(self, wd="/tmp/tool_benchmarks"): self.wd = Path(wd); self.wd.mkdir(parents=True, exist_ok=True)
    def run_benchmark(self, name: str, code: str) -> Dict:
        res = {"tool_name": name, "tests": [], "passed": False, "pass_rate": 0.0, "timestamp": time.time()}
        tests = [{"n": "syntax", "t": "syntax"}, {"n": "imports", "t": "import"}]
        passed = 0
        for t in tests:
            try:
                if t["t"] == "syntax": ast.parse(code); st = "pass"
                else: st = "pass" if not any(p in code for p in ["__import__", "exec", "eval"]) else "fail"
            except Exception as e: st = "fail"
            res["tests"].append({"name": t["n"], "status": st})
            if st == "pass": passed += 1
        res["pass_rate"] = passed / max(1, len(tests))
        res["passed"] = res["pass_rate"] >= 0.8
        return res

class VersionManager:
    def __init__(self, vd="/tmp/tool_versions"): self.vd = Path(vd); self.vd.mkdir(parents=True, exist_ok=True)
    def parse_v(self, v: str) -> tuple: return tuple(int(p) for p in v.lstrip("v").split(".") if p.isdigit()) + (0,)*(3-len(v.split(".")))
    def next_v(self, cv: str, ct: str="patch") -> str:
        m, mi, p = self.parse_v(cv)
        return f"{m+1}.0.0" if ct=="major" else f"{m}.{mi+1}.0" if ct=="minor" else f"{m}.{mi}.{p+1}"
    def save_v(self, name: str, ver: ToolVersion) -> bool:
        try:
            d = self.vd / name; d.mkdir(parents=True, exist_ok=True)
            with open(d / f"v{ver.version}.json", "w") as f:
                json.dump({"version": ver.version, "code": ver.code, "tests": ver.tests, "br": ver.benchmark_results, "ca": ver.created_at, "status": ver.status.value, "cb": ver.created_by}, f)
            return True
        except Exception as e: logger.error(f"Save error: {e}"); return False
    def load_v(self, name: str, v: str) -> Optional[ToolVersion]:
        try:
            with open(self.vd / name / f"v{v}.json") as f: d = json.load(f)
            return ToolVersion(d["version"], d["code"], d["tests"], d.get("br",{}), d.get("ca",time.time()), ToolStatus(d.get("status","testing")), d.get("cb","system"))
        except: return None
    def list_v(self, name: str) -> List[str]:
        d = self.vd / name
        return sorted([f.stem[1:] for f in d.glob("v*.json")] if d.exists() else [], key=self.parse_v, reverse=True)

class RollbackManager:
    def __init__(self, rd="/tmp/tool_rollbacks"): self.rd = Path(rd); self.rd.mkdir(parents=True, exist_ok=True); self.max = 10
    def create(self, name: str, ver: str, data: Dict, reason: str, by: str) -> bool:
        try:
            with open(self.rd / f"{name}_{ver}_{int(time.time())}.json", "w") as f:
                json.dump({"version": ver, "ca": time.time(), "reason": reason, "by": by, "data": data}, f)
            return True
        except: return False
    def rollback(self, name: str, ver: str) -> Optional[Dict]:
        for f in self.rd.glob(f"{name}_*.json"):
            with open(f) as d: d = json.load(d)
            if d["version"] == ver: return d["data"]
        return None
    def list_r(self, name: str) -> List[Dict]:
        return sorted([json.load(open(f)) for f in self.rd.glob(f"{name}_*.json")], key=lambda x: x.get("ca",0), reverse=True)

class ToolFactory:
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.sv, self.be, self.vm, self.rm = SafetyValidator(), BenchmarkEngine(), VersionManager(), RollbackManager()
        self.tools: Dict[str, Dict] = {}
        self.wd = Path("/tmp/tool_factory"); self.wd.mkdir(parents=True, exist_ok=True)
        logger.info("ToolFactory ready: safety, versioning, rollback")

    def create_tool(self, spec: ToolSpec, code: str, tests: str="") -> Dict:
        result = {"success": False, "tool_name": spec.name, "stages": [], "errors": []}
        sr = self.sv.validate(code)
        result["stages"].append("safety_check")
        if not sr["safe"]: result["errors"].append({"stage": "safety_check", "issues": sr["issues"]}); result["status"] = ToolStatus.REJECTED; return result
        br = self.be.run_benchmark(spec.name, code)
        result["stages"].append("benchmark")
        if not br["passed"]: result["errors"].append({"stage": "benchmark", "results": br}); result["status"] = ToolStatus.REJECTED; return result
        ver = ToolVersion("0.1.0", code, tests, br, status=ToolStatus.APPROVED)
        self.vm.save_v(spec.name, ver)
        self.tools[spec.name] = {"spec": spec, "ver": ver, "meta": ToolMetadata(spec.name, spec.description, spec.category, "0.1.0", ["0.1.0"], ToolStatus.ACTIVE)}
        result["success"] = True; result["status"] = ToolStatus.ACTIVE
        return result

    def update_tool(self, name: str, code: str, tests: str="", ct: str="patch") -> Dict:
        if name not in self.tools: return {"success": False, "error": "Tool not found"}
        td = self.tools[name]
        cv = td["ver"].version
        nv = self.vm.next_v(cv, ct)
        sr = self.sv.validate(code)
        if not sr["safe"]: return {"success": False, "error": "Safety failed", "issues": sr["issues"]}
        br = self.be.run_benchmark(name, code)
        if not br["passed"]: return {"success": False, "error": "Benchmark failed", "results": br}
        breaking = bool(set(re.findall(r"def (\w+)\(", code)) - set(re.findall(r"def (\w+)\(", td["ver"].code)))
        ver = ToolVersion(nv, code, tests, br, status=ToolStatus.ACTIVE, breaking=breaking)
        self.rm.create(name, cv, {"code": td["ver"].code}, f"Update to {nv}", "system")
        self.vm.save_v(name, ver)
        td["ver"] = ver; td["meta"].current_version = nv; td["meta"].versions.append(nv); td["meta"].updated_at = time.time()
        return {"success": True, "new_version": nv, "breaking": breaking}

    def rollback_tool(self, name: str, ver: str=None) -> Dict:
        if name not in self.tools: return {"success": False, "error": "Tool not found"}
        vs = self.vm.list_v(name)
        if not ver:
            if len(vs) < 2: return {"success": False, "error": "No previous version"}
            ver = vs[1]
        rd = self.rm.rollback(name, ver)
        if not rd: return {"success": False, "error": f"No rollback for v{ver}"}
        ov = self.vm.load_v(name, ver)
        if ov:
            td = self.tools[name]
            self.rm.create(name, td["ver"].version, {"code": td["ver"].code}, "Rollback", "system")
            td["ver"] = ov; td["meta"].current_version = ver; td["meta"].status = ToolStatus.ROLLBACK
            return {"success": True, "version": ver}
        return {"success": False, "error": "Rollback failed"}

    def get_tool_info(self, name: str) -> Optional[Dict]:
        if name not in self.tools: return None
        td = self.tools[name]
        return {"name": name, "description": td["meta"].description, "category": td["meta"].category, "current_version": td["meta"].current_version, "versions": self.vm.list_v(name), "status": td["meta"].status.value, "rollbacks": self.rm.list_r(name)}

    def list_tools(self) -> List[str]: return list(self.tools.keys())

    def delete_tool(self, name: str) -> Dict:
        if name not in self.tools: return {"success": False, "error": "Tool not found"}
        td = self.tools[name]
        self.rm.create(name, td["ver"].version, {"code": td["ver"].code}, "Deletion", "system")
        del self.tools[name]
        return {"success": True}

def create_tool_factory(api_key=None): return ToolFactory(api_key)
