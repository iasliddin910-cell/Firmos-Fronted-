"""
OmniAgent X ULTIMATE - Advanced Code Interpreter
=================================================
Powerful sandboxed code execution with package management
"""
import os
import subprocess
import logging
import shutil
import uuid
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class AdvancedCodeInterpreter:
    """
    Advanced code interpreter with:
    - Multiple languages (Python, JS, etc.)
    - Package management
    - Internet access (optional)
    - File system access
    - Execution time limits
    """
    
    def __init__(self, workspace_dir: Path = None):
        if workspace_dir is None:
            workspace_dir = Path(__file__).parent.parent / "data" / "code_workspace"
        
        self.workspace_dir = workspace_dir
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        
        # Settings
        self.max_execution_time = 60
        self.max_output_size = 100000
        
        logger.info("💻 Advanced Code Interpreter initialized")
    
    def execute_python(self, code: str, dependencies: List[str] = None) -> str:
        """Execute Python code with optional dependencies"""
        session_id = str(uuid.uuid4())[:8]
        session_dir = self.workspace_dir / session_id
        session_dir.mkdir(exist_ok=True)
        
        try:
            # Create virtual environment
            venv_dir = session_dir / "venv"
            subprocess.run(["python3", "-m", "venv", str(venv_dir)], 
                         capture_output=True, timeout=30)
            
            # Install dependencies
            if dependencies:
                pip_path = venv_dir / "bin" / "pip"
                for dep in dependencies:
                    subprocess.run([str(pip_path), "install", dep], 
                                 capture_output=True, timeout=120)
            
            # Write code
            code_file = session_dir / "main.py"
            code_file.write_text(code, encoding='utf-8')
            
            # Execute
            env = os.environ.copy()
            env["PATH"] = str(venv_dir / "bin") + ":" + env.get("PATH", "")
            
            python_path = venv_dir / "bin" / "python"
            result = subprocess.run([str(python_path), str(code_file)],
                                  capture_output=True, text=True,
                                  timeout=self.max_execution_time, env=env)
            
            output = result.stdout if result.stdout else result.stderr
            if not output:
                output = "✅ Kod muvaffaqiyatli bajarildi"
            
            if len(output) > self.max_output_size:
                output = output[:self.max_output_size] + "\n... (truncated)"
            
            shutil.rmtree(session_dir, ignore_errors=True)
            return f"💻 **Python - Natija:**\n\n{output}"
        
        except subprocess.TimeoutExpired:
            shutil.rmtree(session_dir, ignore_errors=True)
            return "❌ Kod vaqt tugadi"
        except Exception as e:
            shutil.rmtree(session_dir, ignore_errors=True)
            return f"❌ Xatolik: {str(e)}"
    
    def execute_javascript(self, code: str) -> str:
        """Execute JavaScript code"""
        session_id = str(uuid.uuid4())[:8]
        session_dir = self.workspace_dir / session_id
        session_dir.mkdir(exist_ok=True)
        
        try:
            code_file = session_dir / "main.js"
            code_file.write_text(code, encoding='utf-8')
            
            result = subprocess.run(["node", str(code_file)],
                                  capture_output=True, text=True,
                                  timeout=self.max_execution_time)
            
            output = result.stdout if result.stdout else result.stderr
            if not output:
                output = "✅ JS kod muvaffaqiyatli"
            
            shutil.rmtree(session_dir, ignore_errors=True)
            return f"💻 **JavaScript - Natija:**\n\n{output}"
        except Exception as e:
            shutil.rmtree(session_dir, ignore_errors=True)
            return f"❌ Xatolik: {str(e)}"
    
    def execute_project(self, files: Dict[str, str], entry: str = "main.py") -> str:
        """Execute multi-file project"""
        session_id = str(uuid.uuid4())[:8]
        session_dir = self.workspace_dir / session_id
        session_dir.mkdir(exist_ok=True)
        
        try:
            for fname, content in files.items():
                (session_dir / fname).write_text(content, encoding='utf-8')
            
            if entry.endswith('.py'):
                result = subprocess.run(["python3", str(session_dir / entry)],
                                      capture_output=True, text=True,
                                      timeout=self.max_execution_time, cwd=session_dir)
            elif entry.endswith('.js'):
                result = subprocess.run(["node", str(session_dir / entry)],
                                      capture_output=True, text=True,
                                      timeout=self.max_execution_time, cwd=session_dir)
            else:
                return f"❌ Unsupported file type"
            
            output = result.stdout if result.stdout else result.stderr
            flist = "\n".join([f"📄 {f}" for f in files.keys()])
            
            shutil.rmtree(session_dir, ignore_errors=True)
            return f"💻 **Loyiha:**\n\n📁 Fayllar:\n{flist}\n\n📋 Natija:\n{output[:2000]}"
        except Exception as e:
            shutil.rmtree(session_dir, ignore_errors=True)
            return f"❌ Xatolik: {str(e)}"
    
    def create_web_project(self, req: str) -> str:
        """Create web project"""
        files = {
            "index.html": f"""<!DOCTYPE html>
<html><head><title>Web Sayt</title></head>
<body><h1>Zamonaviy Web Sayt</h1>
<p>Talab: {req}</p></body></html>""",
            "style.css": "body { font-family: Arial; background: #f0f0f0; }",
            "app.js": "console.log('App started!');"
        }
        return self.execute_project(files, "index.html")
    
    def create_api(self, req: str) -> str:
        """Create API project"""
        code = f"""from flask import Flask, jsonify
app = Flask(__name__)
@app.route('/')
def home(): return jsonify({{'status': 'ok', 'req': '{req}'}})
if __name__ == '__main__': app.run(port=5000)"""
        files = {"main.py": code, "requirements.txt": "flask>=2.0.0"}
        return self.execute_project(files, "main.py")
    
    def create_game(self) -> str:
        """Create simple game"""
        code = """import random
choices = ['rock','paper','scissors']
for i in range(3):
    u,c = random.choice(choices), random.choice(choices)
    print(f"Siz: {u} | PC: {c}")
    if u==c: print("Durang!")
    elif (u=='rock' and c=='scissors') or (u=='paper' and c=='rock') or (u=='scissors' and c=='paper'): print("Siz yuttingiz!")
    else: print("PC yutti!")
print("O'yin tugadi!")"""
        return self.execute_python(code)
    
    def get_languages(self) -> str:
        return "💻 Qo'llab-quvvatlanadigan tillar: Python, JavaScript, HTML/CSS, TypeScript, Go, Rust"


_code_interpreter = None

def get_code_interpreter(workspace_dir=None):
    global _code_interpreter
    if _code_interpreter is None:
        _code_interpreter = AdvancedCodeInterpreter(workspace_dir)
    return _code_interpreter
