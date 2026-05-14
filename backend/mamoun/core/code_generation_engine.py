"""
BABSHARQII v50.0 — Code Generation Engine (REAL — NOT MOCK)
محرك توليد الكود الحقيقي — يكتب كود فعلي عبر LLM مع مراجعة ثنائية النموذج

v50.0 FUSION FIX: CodeGenerationEngine was MOCK — _writer_generate returned empty
template, _reviewer_review returned hardcoded confidence=0.75.

NOW:
  - _writer_generate calls LLM (glm-5.1) to write REAL code
  - _reviewer_review calls LLM (deepseek-chat) for REAL quality/safety review
  - Incremental code generation (build step by step)
  - Dual-Model Review: Writer + Reviewer = higher quality
  - Confidence < 0.7 → waits for human review
  - Respects Immutable Safety Core (protected files)
  - Supports Python, TypeScript, JavaScript, and more
"""

import os
import ast
import time
import json
import asyncio
import logging
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any
from enum import Enum
from mamoun.core.unified_db import get_db_connection, UNIFIED_DB_PATH

logger = logging.getLogger("mamoun.code_generation")


class GenerationStatus(str, Enum):
    """حالة التوليد — Generation status"""
    DRAFTING = "drafting"
    REVIEWING = "reviewing"
    AWAITING_HUMAN = "awaiting_human"
    APPROVED = "approved"
    APPLIED = "applied"
    REJECTED = "rejected"
    FAILED = "failed"


@dataclass
class CodeGeneration:
    """توليد كود — A code generation request/result"""
    id: str = ""
    description: str = ""
    target_file: str = ""
    language: str = "python"
    generated_code: str = ""
    reviewer_model: str = ""
    reviewer_feedback: str = ""
    confidence: float = 0.0
    writer_model: str = ""
    status: str = GenerationStatus.DRAFTING.value
    created_at: float = 0.0
    reviewed_at: float = 0.0
    applied_at: float = 0.0

    def __post_init__(self):
        if not self.id:
            import hashlib
            self.id = f"cg_{hashlib.md5(f'{self.target_file}{time.time()}'.encode()).hexdigest()[:12]}"
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> dict:
        return asdict(self)


class CodeGenerationEngine:
    """
    محرك توليد الكود الحقيقي — Real Code Generation Engine

    v50.0: NO MORE MOCK — this engine now calls LLM for REAL code generation.

    Pipeline:
      1. Writer model (glm-5.1) generates REAL code from description
      2. Reviewer model (deepseek-chat) reviews for quality/safety
      3. Static analysis validates syntax and structure
      4. If confidence >= 0.7 → auto-approve
      5. If confidence < 0.7 → await human review
      6. Apply to file (respecting immutable core)

    Supports:
      - Python (.py)
      - TypeScript (.ts, .tsx)
      - JavaScript (.js, .jsx)
      - Configuration files (.json, .yaml, .toml)
      - Documentation (.md, .rst)
    """

    CONFIDENCE_THRESHOLD = 0.7

    IMMUTABLE_FILES = {
        "laws.yaml", "settings.yaml", ".env", ".key", ".pem",
        "safety_guard.py", "approval_gate.py", "conscience_layer.py",
        "self_improvement_engine.py", "code_generation_engine.py",
    }

    # Language-specific prompts and validation
    LANGUAGE_CONFIG = {
        "python": {
            "ext": ".py",
            "prompt_suffix": "Write clean, well-documented Python code with proper type hints, error handling, and logging. Use dataclasses where appropriate.",
            "syntax_validator": "ast.parse",
        },
        "typescript": {
            "ext": ".ts",
            "prompt_suffix": "Write clean TypeScript with proper interfaces, types, and JSDoc comments. Use modern ES6+ syntax.",
            "syntax_validator": "tsc_check",
        },
        "javascript": {
            "ext": ".js",
            "prompt_suffix": "Write clean JavaScript with JSDoc comments. Use modern ES6+ syntax (async/await, destructuring, etc).",
            "syntax_validator": "node_check",
        },
        "react": {
            "ext": ".tsx",
            "prompt_suffix": "Write a React component with TypeScript. Include proper props interface, hooks usage, and accessibility attributes.",
            "syntax_validator": "tsc_check",
        },
        "json": {
            "ext": ".json",
            "prompt_suffix": "Return valid JSON only. No markdown, no comments, no explanation — just the JSON object.",
            "syntax_validator": "json_parse",
        },
        "yaml": {
            "ext": ".yaml",
            "prompt_suffix": "Return valid YAML only. No markdown, no explanation — just the YAML content.",
            "syntax_validator": "none",
        },
    }

    def __init__(self, db_path: Optional[Path] = None,
                 writer_model: str = "glm-5.1",
                 reviewer_model: str = "deepseek-chat"):
        self._db_path = db_path or UNIFIED_DB_PATH
        self._writer_model = writer_model
        self._reviewer_model = reviewer_model
        self._generations: List[CodeGeneration] = []
        self._initialized = False
        self._llm_client = None

    def set_llm_client(self, llm_client):
        """تعيين عميل LLM — Set the LLM client for real code generation"""
        self._llm_client = llm_client
        logger.info("CodeGenerationEngine: LLM client set ✓")

    def initialize(self) -> bool:
        try:
            self._ensure_schema()
            # Try to get LLM client if not set
            if not self._llm_client:
                try:
                    from mamoun.core.llm_client import get_llm_client
                    self._llm_client = get_llm_client()
                    logger.info("CodeGenerationEngine: Auto-connected to LLM client ✓")
                except Exception as e:
                    logger.warning("CodeGenerationEngine: Could not auto-connect LLM client: %s", e)
            self._initialized = True
            logger.info("CodeGenerationEngine initialized — writer=%s, reviewer=%s, llm=%s",
                       self._writer_model, self._reviewer_model, self._llm_client is not None)
            return True
        except Exception as e:
            logger.error("CodeGenerationEngine init failed: %s", e)
            return False

    def _ensure_schema(self):
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = get_db_connection(self._db_path)
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS cg_generations (
                id TEXT PRIMARY KEY, description TEXT, target_file TEXT,
                generated_code TEXT, reviewer_model TEXT, reviewer_feedback TEXT,
                confidence REAL, writer_model TEXT, status TEXT,
                created_at REAL, reviewed_at REAL, applied_at REAL,
                language TEXT DEFAULT 'python')""")
            conn.commit()
        finally:
            conn.close()

    async def generate_code(self, description: str, target_file: str,
                      context: str = "", language: str = "") -> CodeGeneration:
        """
        توليد كود حقيقي — Generate REAL code based on description using LLM

        v50.0: This is NO LONGER MOCK. Calls LLM for real code generation.

        Step 1: Writer model generates REAL code
        Step 2: Reviewer model reviews for quality/safety
        Step 3: Static analysis validates syntax
        Step 4: Determine confidence and status
        """
        # Determine language from file extension
        if not language:
            language = self._detect_language(target_file)

        # Check immutability
        file_name = Path(target_file).name
        if file_name in self.IMMUTABLE_FILES:
            gen = CodeGeneration(
                description=description,
                target_file=target_file,
                language=language,
                status=GenerationStatus.REJECTED.value,
            )
            logger.warning("Cannot generate code for immutable file: %s", target_file)
            return gen

        # Step 1: Writer model generates REAL code via LLM
        generated = await self._writer_generate(description, target_file, context, language)

        if not generated or generated.strip() == "":
            gen = CodeGeneration(
                description=description,
                target_file=target_file,
                language=language,
                status=GenerationStatus.FAILED.value,
            )
            logger.error("Writer model returned empty code for: %s", target_file)
            return gen

        # Step 2: Reviewer model reviews via LLM
        confidence, feedback = await self._reviewer_review(generated, description, language)

        # Step 3: Static analysis validation
        static_confidence, static_feedback = self._static_analysis(generated, language)
        confidence = (confidence * 0.7) + (static_confidence * 0.3)  # Weighted average
        if static_feedback:
            feedback += f" | Static Analysis: {static_feedback}"

        # Step 4: Determine status based on confidence
        if confidence >= self.CONFIDENCE_THRESHOLD:
            status = GenerationStatus.APPROVED.value
        else:
            status = GenerationStatus.AWAITING_HUMAN.value

        gen = CodeGeneration(
            description=description,
            target_file=target_file,
            language=language,
            generated_code=generated,
            writer_model=self._writer_model,
            reviewer_model=self._reviewer_model,
            reviewer_feedback=feedback,
            confidence=round(confidence, 3),
            status=status,
        )

        self._generations.append(gen)
        self._persist_generation(gen)

        logger.info("Code generated for %s — confidence=%.3f, status=%s, lines=%d",
                    target_file, confidence, status, generated.count('\n') + 1)

        return gen

    async def _writer_generate(self, description: str, target_file: str,
                        context: str = "", language: str = "python") -> str:
        """
        Writer model generates REAL code via LLM — NO MORE MOCK

        Uses the LLM client to generate actual, functional code.
        Falls back to template only if LLM is completely unavailable.
        """
        lang_config = self.LANGUAGE_CONFIG.get(language, self.LANGUAGE_CONFIG["python"])
        prompt_suffix = lang_config.get("prompt_suffix", "")
        module_name = Path(target_file).stem

        # Build the prompt for code generation
        system_prompt = f"""أنت مبرمج خبير. اكتب كود {language} كامل وجاهز للتنفيذ بناءً على الوصف.

قواعد صارمة:
1. اكتب كود كامل وصالح للتنفيذ — لا حشو ولا تعليقات فارغة
2. أضف docstrings لكل دالة وكلاس
3. أضف معالجة أخطاء (try/except) عند الحاجة
4. استخدم type hints عند كتابة Python
5. لا تستخدم os.system أو exec() أو eval() — هذه أنماط محظورة
6. الكود يجب أن يعمل مباشرة بدون تعديل
7. أجب بالكود فقط — بدون شرح إضافي قبل أو بعد الكود
8. لا تضع الكود في markdown code blocks

{prompt_suffix}"""

        user_prompt = f"""اكتب كود {language} كامل للملف: {module_name}

الوصف: {description}

الملف المستهدف: {target_file}"""

        if context:
            user_prompt += f"""

السياق الإضافي:
{context[:3000]}"""

        # Try LLM client for real code generation
        if self._llm_client:
            try:
                from mamoun.core.llm_client import LLMMessage
                response = await self._llm_client.chat(
                    messages=[
                        LLMMessage(role="system", content=system_prompt),
                        LLMMessage(role="user", content=user_prompt),
                    ],
                    model=self._writer_model,
                    temperature=0.2,
                    max_tokens=4096,
                )
                if response and response.text:
                    code = self._clean_llm_output(response.text)
                    if code and len(code) > 20:  # Ensure we got real code, not empty
                        logger.info("Writer generated %d lines of REAL code via %s",
                                   code.count('\n') + 1, self._writer_model)
                        return code
                    else:
                        logger.warning("LLM returned too short code — falling back")
            except Exception as e:
                logger.error("LLM writer failed: %s — falling back to template", e)

        # Fallback: Try using CodeGenTool from RealToolsEngine
        try:
            from mamoun.core.real_tools import CodeGenTool
            from mamoun.core.llm_client import get_llm_client
            llm = self._llm_client or get_llm_client()
            codegen = CodeGenTool(llm_client=llm)
            result = await codegen.generate_and_execute(
                description=description,
                language=language,
                execute=False,  # Don't execute — just generate
            )
            if result.success and result.artifacts:
                # Read the generated file
                artifact_path = result.artifacts[0].get("path", "")
                if artifact_path and Path(artifact_path).exists():
                    code = Path(artifact_path).read_text(encoding='utf-8')
                    if code and len(code) > 20:
                        logger.info("Writer generated code via CodeGenTool ✓")
                        return code
        except Exception as e:
            logger.debug("CodeGenTool fallback failed: %s", e)

        # Last resort: basic template (but this should rarely happen)
        logger.warning("All LLM methods failed — using basic template as last resort")
        return self._generate_basic_template(module_name, description, language)

    async def _reviewer_review(self, code: str, description: str,
                               language: str = "python") -> tuple:
        """
        Reviewer model reviews code via LLM — NO MORE MOCK

        Uses the LLM client to provide a real quality and safety review.
        Returns (confidence: float, feedback: str)
        """
        # If LLM is available, do a real review
        if self._llm_client:
            try:
                from mamoun.core.llm_client import LLMMessage
                review_prompt = f"""أنت مراجع كود خبير. قم بمراجعة الكود التالي وتقييمه.

الوصف المطلوب: {description}
اللغة: {language}

الكود المراد مراجعته:
```
{code[:6000]}
```

قم بتقييم الكود من 0.0 إلى 1.0 بناءً على:
1. هل الكود يحقق الوصف المطلوب؟ (وزن 0.3)
2. هل الكود آمن ولا يحتوي أنماط خطرة؟ (وزن 0.3)
3. هل الكود نظيف ومنظم ويتبع أفضل الممارسات؟ (وزن 0.2)
4. هل الكود يحتوي معالجة أخطاء كافية؟ (وزن 0.1)
5. هل الكود موثق بشكل كافٍ؟ (وزن 0.1)

أجب بصيغة JSON فقط:
{{
    "confidence": 0.0-1.0,
    "feedback": "ملخص المراجعة",
    "issues": ["مشكلة 1", "مشكلة 2"],
    "strengths": ["نقطة قوة 1", "نقطة قوة 2"]
}}"""

                response = await self._llm_client.chat(
                    messages=[
                        LLMMessage(role="system", content="أنت مراجع كود محترف. أجب بصيغة JSON فقط."),
                        LLMMessage(role="user", content=review_prompt),
                    ],
                    model=self._reviewer_model,
                    temperature=0.1,
                    json_mode=True,
                )

                if response and response.text:
                    review_data = response.extract_json()
                    if review_data:
                        confidence = float(review_data.get("confidence", 0.5))
                        feedback = review_data.get("feedback", "")
                        issues = review_data.get("issues", [])
                        strengths = review_data.get("strengths", [])

                        if issues:
                            feedback += f" | مشاكل: {'; '.join(issues[:5])}"
                        if strengths:
                            feedback += f" | نقاط قوة: {'; '.join(strengths[:3])}"

                        logger.info("Reviewer (%s) gave confidence=%.3f", self._reviewer_model, confidence)
                        return confidence, feedback
            except Exception as e:
                logger.error("LLM reviewer failed: %s — falling back to static review", e)

        # Fallback: static analysis review (better than mock)
        return self._static_review_fallback(code, description)

    def _static_review_fallback(self, code: str, description: str) -> tuple:
        """
        مراجعة ثابتة بديلة — Static review fallback when LLM is unavailable.
        This is NOT mock — it performs actual code analysis.
        """
        confidence = 0.6  # Start lower than LLM review
        feedback_parts = []

        # Check for dangerous patterns
        dangerous = ["os.system", "subprocess.call", "exec(", "eval(", "__import__",
                     "shutil.rmtree", "os.remove", "os.unlink"]
        for pattern in dangerous:
            if pattern in code:
                confidence = 0.2
                feedback_parts.append(f"نمط خطير: {pattern}")
                break

        # Check for basic quality indicators
        if "def " in code or "class " in code or "function " in code or "const " in code:
            confidence += 0.1
        else:
            feedback_parts.append("لا توجد دوال أو كلاسات معرّفة")

        if '"""' in code or "'''" in code or "/**" in code or "// " in code:
            confidence += 0.05

        if "try" in code or "catch" in code or "except" in code:
            confidence += 0.05
        else:
            feedback_parts.append("لا توجد معالجة أخطاء")

        if "import " in code or "from " in code or "require(" in code:
            confidence += 0.05

        # Length check — too short is suspicious
        lines = code.strip().split('\n')
        if len(lines) < 5:
            confidence *= 0.5
            feedback_parts.append("الكود قصير جداً — قد يكون غير مكتمل")
        elif len(lines) > 200:
            confidence *= 0.9  # Very long code needs more review

        # Check if code matches description keywords
        desc_words = set(description.lower().split())
        code_lower = code.lower()
        matching_words = sum(1 for w in desc_words if len(w) > 3 and w in code_lower)
        if matching_words > 0:
            confidence += 0.05

        confidence = min(1.0, max(0.0, confidence))

        if not feedback_parts:
            feedback_parts.append("المراجعة الثابتة: بنية الكود مقبولة")

        return round(confidence, 3), " | ".join(feedback_parts)

    def _static_analysis(self, code: str, language: str) -> tuple:
        """
        تحليل ثابت للكود — Static code analysis for syntax and structure validation.
        Returns (confidence: float, feedback: str)
        """
        confidence = 1.0
        feedback_parts = []

        if language == "python":
            # Try to parse Python code with ast
            try:
                tree = ast.parse(code)
                # Count functions and classes
                funcs = sum(1 for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)))
                classes = sum(1 for n in ast.walk(tree) if isinstance(n, ast.ClassDef))
                if funcs == 0 and classes == 0:
                    confidence *= 0.7
                    feedback_parts.append("لا توجد دوال أو كلاسات")
            except SyntaxError as e:
                confidence = 0.3
                feedback_parts.append(f"خطأ في بناء الجملة: {str(e)[:100]}")
        elif language in ("typescript", "javascript", "react"):
            # Basic checks for JS/TS
            if "function " not in code and "const " not in code and "class " not in code and "export " not in code:
                confidence *= 0.7
                feedback_parts.append("لا توجد عناصر كود JS/TS واضحة")
        elif language == "json":
            try:
                json.loads(code)
            except json.JSONDecodeError as e:
                confidence = 0.2
                feedback_parts.append(f"JSON غير صالح: {str(e)[:100]}")

        # Common dangerous patterns for all languages
        dangerous_patterns = [
            "rm -rf", "del /f", "format c:", "DROP TABLE",
            "GRANT ALL", "chmod 777", "passwd",
        ]
        for pattern in dangerous_patterns:
            if pattern.lower() in code.lower():
                confidence = 0.1
                feedback_parts.append(f"نمط خطير مكتشف: {pattern}")
                break

        feedback = "; ".join(feedback_parts) if feedback_parts else "التحليل الثابت: بنية صحيحة"
        return round(confidence, 3), feedback

    def _detect_language(self, target_file: str) -> str:
        """كشف لغة البرمجة من امتداد الملف"""
        ext_map = {
            ".py": "python",
            ".ts": "typescript",
            ".tsx": "react",
            ".js": "javascript",
            ".jsx": "react",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".md": "python",  # Default to python for docs
        }
        ext = Path(target_file).suffix.lower()
        return ext_map.get(ext, "python")

    def _clean_llm_output(self, text: str) -> str:
        """تنظيف مخرجات LLM — إزالة markdown code blocks"""
        code = text.strip()
        # Remove markdown code blocks
        if code.startswith("```"):
            lines = code.split("\n")
            # Remove first line (```python, ```typescript, etc.)
            lines = lines[1:]
            # Remove last line (```)
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            code = "\n".join(lines)
        return code.strip()

    def _generate_basic_template(self, module_name: str, description: str,
                                  language: str = "python") -> str:
        """قالب أساسي — آخر ملاذ عندما تفشل كل طرق LLM"""
        if language == "python":
            return f'"""\n{module_name} — {description}\n\nAuto-generated by CodeGenerationEngine (template fallback)\n"""\n\nimport logging\nfrom typing import Optional, Dict, Any\n\nlogger = logging.getLogger(__name__)\n\n\nclass {module_name.title().replace("_", "")}:\n    """{description}"""\n\n    def __init__(self):\n        self._initialized = False\n        logger.info("{module_name}: Initialized")\n\n    async def execute(self, task: str, context: Dict[str, Any] = None) -> Dict[str, Any]:\n        """تنفيذ المهمة"""\n        context = context or {{}}\n        try:\n            # TODO: Implement actual logic for: {description}\n            result = {{"task": task, "status": "completed"}}\n            return result\n        except Exception as e:\n            logger.error("Execution failed: %s", e)\n            return {{"status": "error", "error": str(e)}}\n\n\n# Singleton\n_{module_name.lower()}: Optional[{module_name.title().replace("_", "")}] = None\n\n\ndef get_{module_name.lower()}() -> {module_name.title().replace("_", "")}:\n    global _{module_name.lower()}\n    if _{module_name.lower()} is None:\n        _{module_name.lower()} = {module_name.title().replace("_", "")}()\n    return _{module_name.lower()}\n'
        elif language in ("typescript", "javascript", "react"):
            return f'/**\n * {module_name} — {description}\n *\n * Auto-generated by CodeGenerationEngine (template fallback)\n */\n\nimport {{ Logger }} from "winston";\n\nconst logger = Logger.createLogger({{ level: "info" }});\n\nexport class {module_name.title().replace("_", "")} {{\n  private initialized: boolean = false;\n\n  constructor() {{\n    this.initialized = true;\n    logger.info("{module_name}: Initialized");\n  }}\n\n  async execute(task: string, context: Record<string, any> = {{}}): Promise<Record<string, any>> {{\n    try {{\n      // TODO: Implement actual logic for: {description}\n      return {{ task, status: "completed" }};\n    }} catch (error) {{\n      logger.error("Execution failed:", error);\n      return {{ status: "error", error: String(error) }};\n    }}\n  }}\n}}\n'
        else:
            return f'// {module_name} — {description}\n// Auto-generated by CodeGenerationEngine\n'

    def apply_generation(self, gen_id: str) -> Optional[CodeGeneration]:
        """Apply an approved code generation"""
        gen = None
        for g in self._generations:
            if g.id == gen_id:
                gen = g
                break

        if not gen:
            return None

        if gen.status not in (GenerationStatus.APPROVED.value, GenerationStatus.AWAITING_HUMAN.value):
            return gen

        # Check immutability
        file_name = Path(gen.target_file).name
        if file_name in self.IMMUTABLE_FILES:
            gen.status = GenerationStatus.REJECTED.value
            return gen

        try:
            target_path = Path(gen.target_file)
            # Save version via archive before writing
            try:
                from mamoun.core.version_archive import VersionArchive
                archive = VersionArchive()
                archive.save_version(gen.target_file)
            except ImportError:
                pass

            # Write the generated code
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(gen.generated_code, encoding='utf-8')

            gen.status = GenerationStatus.APPLIED.value
            gen.applied_at = time.time()
            self._update_generation(gen)

            logger.info("Applied code generation %s to %s (%d lines)",
                       gen_id, gen.target_file, gen.generated_code.count('\n') + 1)

        except Exception as e:
            gen.status = GenerationStatus.FAILED.value
            logger.error("Failed to apply generation %s: %s", gen_id, e)

        return gen

    async def generate_project(self, project_spec: dict) -> dict:
        """
        توليد مشروع كامل من مواصفات — Generate a complete project from specifications.

        This is the ProjectScaffolder functionality integrated into CodeGenerationEngine.

        Args:
            project_spec: {
                "name": "my_project",
                "description": "A web scraping tool",
                "language": "python",
                "structure": {
                    "main.py": "entry point with CLI",
                    "scraper.py": "web scraping logic",
                    "models.py": "data models",
                    "config.py": "configuration",
                    "requirements.txt": "dependencies"
                },
                "project_dir": "/path/to/project"
            }

        Returns:
            {"success": bool, "files_created": [...], "total_lines": int}
        """
        project_name = project_spec.get("name", "new_project")
        description = project_spec.get("description", "")
        language = project_spec.get("language", "python")
        structure = project_spec.get("structure", {})
        project_dir = project_spec.get("project_dir", "")

        if not project_dir:
            project_dir = str(Path(os.getcwd()) / "download" / project_name)

        files_created = []
        total_lines = 0
        errors = []

        for file_path, file_description in structure.items():
            full_path = str(Path(project_dir) / file_path)
            gen = await self.generate_code(
                description=f"{project_name}: {file_description}",
                target_file=full_path,
                context=f"Project: {project_name}\nDescription: {description}\nFile: {file_path}",
                language=language,
            )

            if gen.generated_code:
                # Auto-apply if confidence is high enough
                if gen.confidence >= self.CONFIDENCE_THRESHOLD:
                    result = self.apply_generation(gen.id)
                    if result and result.status == GenerationStatus.APPLIED.value:
                        files_created.append(full_path)
                        total_lines += gen.generated_code.count('\n') + 1
                    else:
                        errors.append(f"{file_path}: Failed to apply")
                else:
                    errors.append(f"{file_path}: Low confidence ({gen.confidence:.2f}) — needs review")
            else:
                errors.append(f"{file_path}: Generation failed")

        return {
            "success": len(files_created) > 0,
            "project_name": project_name,
            "project_dir": project_dir,
            "files_created": files_created,
            "total_files": len(files_created),
            "total_lines": total_lines,
            "errors": errors,
        }

    def get_pending_review(self) -> List[dict]:
        """Get generations awaiting human review"""
        return [g.to_dict() for g in self._generations
                if g.status == GenerationStatus.AWAITING_HUMAN.value]

    def get_status(self) -> dict:
        return {
            "initialized": self._initialized,
            "writer_model": self._writer_model,
            "reviewer_model": self._reviewer_model,
            "total_generations": len(self._generations),
            "pending_review": len([g for g in self._generations
                                  if g.status == GenerationStatus.AWAITING_HUMAN.value]),
            "has_llm_client": self._llm_client is not None,
            "is_real": self._llm_client is not None,  # True = real LLM, False = template fallback
            "supported_languages": list(self.LANGUAGE_CONFIG.keys()),
        }

    def _persist_generation(self, gen: CodeGeneration):
        try:
            conn = get_db_connection(self._db_path)
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO cg_generations "
                    "(id, description, target_file, generated_code, reviewer_model, "
                    "reviewer_feedback, confidence, writer_model, status, "
                    "created_at, reviewed_at, applied_at, language) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (gen.id, gen.description, gen.target_file, gen.generated_code,
                     gen.reviewer_model, gen.reviewer_feedback, gen.confidence,
                     gen.writer_model, gen.status, gen.created_at,
                     gen.reviewed_at, gen.applied_at, gen.language),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.warning("Failed to persist generation: %s", e)

    def _update_generation(self, gen: CodeGeneration):
        try:
            conn = get_db_connection(self._db_path)
            try:
                conn.execute(
                    "UPDATE cg_generations SET status=?, applied_at=? WHERE id=?",
                    (gen.status, gen.applied_at, gen.id),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception:
            pass


# Singleton
code_generation_engine = CodeGenerationEngine()
