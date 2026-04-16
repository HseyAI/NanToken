import re
from typing import List, Dict, Optional
from .estimator import analyze_prompt_complexity


class ClarifyingQuestions:
    """Generate clarifying questions for ambiguous prompts."""
    
    def __init__(self, enabled: bool = True, always_ask: bool = False, threshold_tokens: int = 500):
        self.enabled = enabled
        self.always_ask = always_ask
        self.threshold_tokens = threshold_tokens
    
    def generate_questions(
        self,
        prompt: str,
        estimated_tokens: int = 0,
    ) -> List[Dict[str, str]]:
        """Generate clarifying questions based on prompt analysis."""
        if not self.enabled:
            return []
        
        if not self.always_ask and estimated_tokens < self.threshold_tokens:
            return []
        
        analysis = analyze_prompt_complexity(prompt)
        questions = []
        
        if analysis["has_code_request"] and not analysis["has_language_hint"]:
            questions.append({
                "id": "language",
                "question": "Which programming language?",
                "options": ["Python", "JavaScript", "Java", "C++", "Go", "Rust", "Other"],
                "required": False,
            })
        
        if "write" in prompt.lower() or "create" in prompt.lower():
            if not analysis["has_format_hint"]:
                questions.append({
                    "id": "format",
                    "question": "What output format do you prefer?",
                    "options": ["Plain code", "With comments", "JSON", "Markdown with explanation", "Simple explanation"],
                    "required": False,
                })
        
        if "implement" in prompt.lower() or "algorithm" in prompt.lower():
            questions.append({
                "id": "complexity",
                "question": "Any specific constraints?",
                "options": ["None", "Time complexity O(n)", "Space complexity O(1)", "Both", "Custom"],
                "required": False,
            })
        
        if analysis["is_ambiguous"]:
            questions.append({
                "id": "context",
                "question": "Can you provide more context about what you need?",
                "options": [],
                "required": True,
            })
        
        if "api" in prompt.lower() or "request" in prompt.lower():
            questions.append({
                "id": "framework",
                "question": "Which framework or library?",
                "options": ["None/standard library", "FastAPI", "Flask", "Django", "Express", "React", "Other"],
                "required": False,
            })
        
        if "database" in prompt.lower() or "sql" in prompt.lower():
            questions.append({
                "id": "db_type",
                "question": "Which database?",
                "options": ["PostgreSQL", "MySQL", "MongoDB", "SQLite", "Redis", "No preference"],
                "required": False,
            })
        
        if "test" in prompt.lower():
            questions.append({
                "id": "test_framework",
                "question": "Which testing framework?",
                "options": ["pytest", "unittest", "Jest", "JUnit", "No preference"],
                "required": False,
            })
        
        return questions[:5]
    
    def format_questions(self, questions: List[Dict[str, str]]) -> str:
        """Format questions for display."""
        if not questions:
            return ""
        
        lines = ["\n❓ Clarifying Questions:", "=" * 40]
        for i, q in enumerate(questions, 1):
            lines.append(f"\n{i}. {q['question']}")
            if q.get("options"):
                lines.append(f"   Options: {', '.join(q['options'])}")
            if q.get("required"):
                lines.append("   [Required]")
        
        return "\n".join(lines)
    
    def get_answers_summary(self, answers: Dict[str, str]) -> str:
        """Format answers summary."""
        if not answers:
            return ""
        
        lines = ["\n[Preferences] Your Preferences:", "=" * 40]
        for key, value in answers.items():
            lines.append(f"  • {key}: {value}")
        
        return "\n".join(lines)


def build_refined_prompt(
    original_prompt: str,
    answers: Dict[str, str],
    system_prompt: str = "",
) -> str:
    """Build refined prompt based on user answers."""
    additions = []
    
    if answers.get("language"):
        additions.append(f"Language: {answers['language']}")
    if answers.get("format"):
        additions.append(f"Format: {answers['format']}")
    if answers.get("complexity"):
        additions.append(f"Constraints: {answers['complexity']}")
    if answers.get("framework"):
        additions.append(f"Framework: {answers['framework']}")
    if answers.get("db_type"):
        additions.append(f"Database: {answers['db_type']}")
    if answers.get("test_framework"):
        additions.append(f"Testing: {answers['test_framework']}")
    if answers.get("context"):
        additions.append(f"Context: {answers['context']}")
    
    if not additions:
        return original_prompt
    
    refined = original_prompt.strip()
    if not refined.endswith("?"):
        refined += "."
    
    refined += f"\n\nRequirements: {', '.join(additions)}."
    
    return refined
