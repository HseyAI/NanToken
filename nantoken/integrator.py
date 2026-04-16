import os
import re
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass


@dataclass
class FileAnalysis:
    path: str
    language: str
    lines: int
    tokens_estimate: int
    has_code: bool
    imports: List[str]
    functions: List[str]


class CodeIntegrator:
    """Integrate with code files - analyze, create, update."""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.language_extensions = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
            ".java": "java",
            ".go": "go",
            ".rs": "rust",
            ".c": "c",
            ".cpp": "cpp",
            ".cs": "csharp",
            ".rb": "ruby",
            ".php": "php",
            ".swift": "swift",
            ".kt": "kotlin",
            ".scala": "scala",
            ".sql": "sql",
            ".sh": "bash",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".json": "json",
            ".xml": "xml",
            ".html": "html",
            ".css": "css",
        }
    
    def find_code_files(self, extensions: Optional[List[str]] = None) -> List[str]:
        """Find all code files in project."""
        if extensions is None:
            extensions = list(self.language_extensions.keys())
        
        files = []
        for ext in extensions:
            files.extend(self.project_root.rglob(f"*{ext}"))
        
        return [str(f) for f in files if not self._is_ignored(f)]
    
    def _is_ignored(self, path: Path) -> bool:
        """Check if path should be ignored."""
        ignore_patterns = [
            "node_modules",
            ".git",
            "__pycache__",
            ".venv",
            "venv",
            "env",
            ".idea",
            ".vscode",
            "dist",
            "build",
            "target",
            ".pytest_cache",
            ".mypy_cache",
        ]
        
        for pattern in ignore_patterns:
            if pattern in str(path):
                return True
        return False
    
    def analyze_file(self, file_path: str) -> FileAnalysis:
        """Analyze a code file."""
        path = Path(file_path)
        
        if not path.exists():
            return FileAnalysis(
                path=file_path,
                language="unknown",
                lines=0,
                tokens_estimate=0,
                has_code=False,
                imports=[],
                functions=[],
            )
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except:
            content = ""
        
        ext = path.suffix
        language = self.language_extensions.get(ext, "unknown")
        
        lines = len(content.split("\n"))
        tokens_estimate = int(lines * 0.75)
        
        imports = self._extract_imports(content, language)
        functions = self._extract_functions(content, language)
        
        has_code = bool(imports or functions or lines > 5)
        
        return FileAnalysis(
            path=str(path),
            language=language,
            lines=lines,
            tokens_estimate=tokens_estimate,
            has_code=has_code,
            imports=imports,
            functions=functions,
        )
    
    def _extract_imports(self, content: str, language: str) -> List[str]:
        """Extract imports/requires from code."""
        imports = []
        
        if language == "python":
            for line in content.split("\n"):
                if re.match(r"^(import|from)\s+", line.strip()):
                    imports.append(line.strip())
        
        elif language in ["javascript", "typescript"]:
            for line in content.split("\n"):
                if re.match(r"^(import|require|export)\s+", line.strip()):
                    imports.append(line.strip())
        
        elif language == "java":
            for line in content.split("\n"):
                if re.match(r"^import\s+", line.strip()):
                    imports.append(line.strip())
        
        elif language == "go":
            for line in content.split("\n"):
                if re.match(r"^import\s+", line.strip()) or line.strip().startswith("package "):
                    imports.append(line.strip())
        
        return imports[:20]
    
    def _extract_functions(self, content: str, language: str) -> List[str]:
        """Extract function/method definitions from code."""
        functions = []
        
        if language == "python":
            for line in content.split("\n"):
                match = re.match(r"^(def|class|async def)\s+(\w+)", line)
                if match:
                    functions.append(match.group(2))
        
        elif language in ["javascript", "typescript"]:
            for line in content.split("\n"):
                match = re.match(r"^(function|const|let|var)\s+(\w+)\s*=?", line)
                if match:
                    functions.append(match.group(2))
                match = re.match(r"^\s*(async\s+)?(function|const|let)\s+(\w+)", line)
                if match:
                    functions.append(match.group(3))
        
        elif language == "java":
            for line in content.split("\n"):
                match = re.match(r"(public|private|protected)?\s*(static)?\s*(\w+)\s+(\w+)\s*\(", line)
                if match:
                    functions.append(match.group(4))
        
        return functions[:20]
    
    def create_file(
        self,
        file_path: str,
        content: str,
        overwrite: bool = False,
    ) -> Tuple[bool, str]:
        """Create a new code file."""
        path = Path(file_path)
        
        if path.exists() and not overwrite:
            return False, f"File already exists: {file_path}"
        
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return True, f"Created: {file_path}"
        except Exception as e:
            return False, f"Error creating file: {str(e)}"
    
    def update_file(
        self,
        file_path: str,
        new_content: str,
        append: bool = False,
    ) -> Tuple[bool, str]:
        """Update an existing code file."""
        path = Path(file_path)
        
        if not path.exists():
            return self.create_file(file_path, new_content)
        
        try:
            if append:
                with open(path, "a", encoding="utf-8") as f:
                    f.write("\n" + new_content)
            else:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new_content)
            return True, f"Updated: {file_path}"
        except Exception as e:
            return False, f"Error updating file: {str(e)}"
    
    def get_project_stats(self) -> Dict:
        """Get project statistics."""
        files = self.find_code_files()
        
        stats = {
            "total_files": len(files),
            "by_language": {},
            "total_lines": 0,
            "total_tokens_estimate": 0,
        }
        
        for file_path in files:
            analysis = self.analyze_file(file_path)
            lang = analysis.language
            
            if lang not in stats["by_language"]:
                stats["by_language"][lang] = {"files": 0, "lines": 0}
            
            stats["by_language"][lang]["files"] += 1
            stats["by_language"][lang]["lines"] += analysis.lines
            stats["total_lines"] += analysis.lines
            stats["total_tokens_estimate"] += analysis.tokens_estimate
        
        return stats
    
    def suggest_file_name(self, prompt: str) -> Optional[str]:
        """Suggest a file name based on the prompt."""
        prompt_lower = prompt.lower()
        
        if "test" in prompt_lower:
            if "python" in prompt_lower or "pytest" in prompt_lower:
                return "test_main.py"
            elif "javascript" in prompt_lower or "jest" in prompt_lower:
                return "main.test.js"
        
        if "api" in prompt_lower or "server" in prompt_lower:
            if "python" in prompt_lower or "fastapi" in prompt_lower:
                return "main.py"
            elif "javascript" in prompt_lower or "express" in prompt_lower:
                return "index.js"
        
        if "script" in prompt_lower:
            return "script.py"
        
        if "config" in prompt_lower:
            return "config.yaml"
        
        return None


def format_file_report(analysis: FileAnalysis) -> str:
    """Format file analysis as readable report."""
    lines = [
        f"[File] {analysis.path}",
        f"   Language: {analysis.language}",
        f"   Lines: {analysis.lines:,}",
        f"   Est. tokens: {analysis.tokens_estimate:,}",
    ]
    
    if analysis.functions:
        lines.append(f"   Functions: {', '.join(analysis.functions[:5])}")
    
    if analysis.imports:
        lines.append(f"   Imports: {', '.join(analysis.imports[:3])}")
    
    return "\n".join(lines)
