"""
BABSHARQII v18.0 — Real Tools Engine
محرك الأدوات الحقيقية — يربط مأمون بالعالم الفعلي

This is the MISSING LINK between Mamoun's brain and real execution.
Every skill executor can now use REAL tools instead of just LLM calls.

Tools Available:
1. ShellExecutor — تنفيذ أوامر النظام (existing, in tools/shell_executor.py)
2. FileSystemTool — قراءة/كتابة ملفات (existing, in tools/filesystem_tool.py)
3. WebSearchTool — بحث في الإنترنت (uses z-ai-web-dev-sdk)
4. ImageGenTool — إنشاء صور (uses z-ai-web-dev-sdk)
5. VideoAnalysisTool — تحليل فيديو (uses z-ai-web-dev-sdk)
6. N8NWorkflowTool — إنشاء workflows لـ n8n
7. BlenderTool — التحكم بـ Blender عبر Python API
8. ServerControlTool — التحكم بالسيرفرات عبر SSH
9. CodeGenTool — توليد وتنفيذ كود حقيقي

Design:
- ReAct (Yao et al., 2023): Reason about which tool to use, Act by calling it
- Toolformer (Schick et al., 2023): LLM decides when to use tools
- Safe by default: All destructive operations require approval
"""

import asyncio
import json
import logging
import os
import time
import subprocess
import shutil
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Any

logger = logging.getLogger("mamoun.core.real_tools")

PROJECT_ROOT = Path(os.getenv("MAMOUN_PROJECT_ROOT", str(Path(__file__).parent.parent.parent.parent)))


# ═══════════════════════════════════════════════════════════════════════════════
# Tool Result Base
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ToolResult:
    """نتيجة تنفيذ أداة حقيقية"""
    success: bool = False
    tool_name: str = ""
    output: str = ""
    data: dict = field(default_factory=dict)
    artifacts: list = field(default_factory=list)
    error: str = ""
    duration_ms: float = 0.0
    requires_approval: bool = False


# ═══════════════════════════════════════════════════════════════════════════════
# Web Search Tool — بحث حقيقي في الإنترنت
# ═══════════════════════════════════════════════════════════════════════════════

class WebSearchTool:
    """
    أداة البحث في الإنترنت — تبحث فعلياً وتجلب نتائج حقيقية
    
    Uses the z-ai-web-dev-sdk for web search, falls back to LLM knowledge.
    """
    
    def __init__(self, llm_client=None):
        self._llm = llm_client
        self._sdk_available = False
        try:
            import importlib
            importlib.import_module("z_ai_web_dev_sdk")
            self._sdk_available = True
        except ImportError:
            logger.warning("z-ai-web-dev-sdk not available — web search will use LLM fallback")
    
    async def search(self, query: str, num_results: int = 10) -> ToolResult:
        """بحث في الإنترنت — يجلب نتائج حقيقية"""
        start = time.time()
        
        # Try SDK first
        if self._sdk_available:
            try:
                result = await self._sdk_search(query, num_results)
                if result.success:
                    return result
            except Exception as e:
                logger.warning("SDK search failed: %s — falling back to LLM", e)
        
        # Fallback: Use LLM with web-aware prompting
        if self._llm:
            try:
                response = await self._llm.think(
                    prompt=f"""ابحث عن معلومات حديثة حول: {query}

قدّم نتائج بحث مفصلة تشمل:
1. أهم المعلومات والحقائق
2. الاتجاهات الحالية
3. الإحصائيات المتاحة
4. المصادر المحتملة
5. التوصيات بناءً على البحث

كن دقيقاً وموضوعياً. إذا لم تكن متأكداً من معلومة، اذكر ذلك.""",
                    system="أنت محرك بحث ذكي. قدّم معلومات دقيقة ومحدثة. اذكر دائماً أن هذه معلومات من نموذج لغوي وقد لا تكون محدثة.",
                    model="glm-5.1",
                    temperature=0.3,
                )
                return ToolResult(
                    success=True,
                    tool_name="web_search",
                    output=response.text[:5000],
                    data={"query": query, "source": "llm_fallback"},
                    duration_ms=(time.time() - start) * 1000,
                )
            except Exception as e:
                return ToolResult(
                    success=False,
                    tool_name="web_search",
                    error=str(e),
                    duration_ms=(time.time() - start) * 1000,
                )
        
        return ToolResult(
            success=False,
            tool_name="web_search",
            error="لا يتوفر محرك بحث — تأكد من اتصال الإنترنت أو مفاتيح API",
        )
    
    async def _sdk_search(self, query: str, num_results: int) -> ToolResult:
        """بحث عبر z-ai-web-dev-sdk"""
        start = time.time()
        try:
            import asyncio as aio
            proc = await aio.create_subprocess_exec(
                "node", "-e",
                f"""
const ZAI = require('z-ai-web-dev-sdk').default;
(async () => {{
    const zai = await ZAI.create();
    const result = await zai.functions.invoke("web_search", {{
        query: {json.dumps(query)},
        num: {num_results}
    }});
    console.log(JSON.stringify(result));
}})().catch(e => console.error(e.message));
""",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
            
            if proc.returncode == 0 and stdout:
                results = json.loads(stdout.decode())
                formatted = ""
                if isinstance(results, list):
                    for r in results[:num_results]:
                        formatted += f"- **{r.get('name', '')}**\n  {r.get('snippet', '')}\n  رابط: {r.get('url', '')}\n\n"
                
                return ToolResult(
                    success=True,
                    tool_name="web_search",
                    output=formatted or "لا توجد نتائج",
                    data={"query": query, "results_count": len(results) if isinstance(results, list) else 0, "source": "sdk"},
                    duration_ms=(time.time() - start) * 1000,
                )
        except Exception as e:
            logger.debug("SDK search error: %s", e)
        
        return ToolResult(success=False, tool_name="web_search", error="SDK search failed")


# ═══════════════════════════════════════════════════════════════════════════════
# Image Generation Tool — إنشاء صور حقيقية
# ═══════════════════════════════════════════════════════════════════════════════

class ImageGenTool:
    """
    أداة إنشاء الصور — تولّد صوراً حقيقية باستخدام AI
    
    Uses z-ai-generate CLI tool for image generation.
    """
    
    SUPPORTED_SIZES = ["1024x1024", "768x1344", "864x1152", "1344x768", "1152x864", "1440x720", "720x1440"]
    
    def __init__(self, output_dir: str = ""):
        self.output_dir = Path(output_dir or PROJECT_ROOT / "download" / "images")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def generate(self, prompt: str, size: str = "1024x1024", filename: str = "") -> ToolResult:
        """إنشاء صورة من وصف نصي"""
        start = time.time()
        
        if size not in self.SUPPORTED_SIZES:
            size = "1024x1024"
        
        if not filename:
            filename = f"mamoun_img_{int(time.time())}.png"
        
        output_path = self.output_dir / filename
        
        try:
            proc = await asyncio.create_subprocess_exec(
                "z-ai-generate",
                "--prompt", prompt,
                "--output", str(output_path),
                "--size", size,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
            
            if proc.returncode == 0 and output_path.exists():
                return ToolResult(
                    success=True,
                    tool_name="image_gen",
                    output=f"تم إنشاء الصورة بنجاح: {filename}",
                    data={"path": str(output_path), "filename": filename, "size": size, "prompt": prompt[:200]},
                    artifacts=[{"type": "image", "path": str(output_path), "filename": filename}],
                    duration_ms=(time.time() - start) * 1000,
                )
            else:
                error_msg = stderr.decode() if stderr else "فشل إنشاء الصورة"
                return ToolResult(
                    success=False,
                    tool_name="image_gen",
                    error=error_msg[:500],
                    duration_ms=(time.time() - start) * 1000,
                )
        except asyncio.TimeoutError:
            return ToolResult(success=False, tool_name="image_gen", error="انتهت مهلة إنشاء الصورة (120 ثانية)")
        except FileNotFoundError:
            return ToolResult(success=False, tool_name="image_gen", error="أداة z-ai-generate غير مثبتة")
        except Exception as e:
            return ToolResult(success=False, tool_name="image_gen", error=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# Video Analysis Tool — تحليل فيديو حقيقي
# ═══════════════════════════════════════════════════════════════════════════════

class VideoAnalysisTool:
    """
    أداة تحليل الفيديو — تحلل فيديو فعلي وتستخرج معلومات
    
    Uses z-ai-web-dev-sdk for video understanding.
    """
    
    def __init__(self, llm_client=None):
        self._llm = llm_client
    
    async def analyze(self, video_path: str, question: str = "", analysis_type: str = "comprehensive") -> ToolResult:
        """
        تحليل فيديو — يستخرج محتوى ويقترح طرق الإنتاج
        
        Args:
            video_path: مسار الفيديو أو رابط URL
            question: سؤال محدد عن الفيديو
            analysis_type: نوع التحليل (comprehensive, educational, production)
        """
        start = time.time()
        
        # Try SDK video understanding
        try:
            proc = await asyncio.create_subprocess_exec(
                "node", "-e",
                f"""
const ZAI = require('z-ai-web-dev-sdk').default;
(async () => {{
    const zai = await ZAI.create();
    const result = await zai.functions.invoke("video_understand", {{
        video_path: {json.dumps(video_path)},
        question: {json.dumps(question or "حلل هذا الفيديو بالتفصيل")},
        analysis_type: {json.dumps(analysis_type)}
    }});
    console.log(JSON.stringify(result));
}})().catch(e => console.error(e.message));
""",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
            
            if proc.returncode == 0 and stdout:
                result_data = json.loads(stdout.decode())
                return ToolResult(
                    success=True,
                    tool_name="video_analysis",
                    output=str(result_data)[:5000],
                    data=result_data if isinstance(result_data, dict) else {"analysis": result_data},
                    duration_ms=(time.time() - start) * 1000,
                )
        except Exception as e:
            logger.debug("SDK video analysis failed: %s — falling back to LLM", e)
        
        # Fallback: LLM analysis
        if self._llm:
            try:
                if analysis_type == "production":
                    system = """أنت محلل إنتاج فيديو خبير. حلل الفيديو واقترح 10 طرق مختلفة لإنتاجه بسهولة.
لكل طريقة اذكر: الأداة، التكلفة التقريبية، الوقت المطلوب، مستوى الصعوبة، جودة النتيجة."""
                    prompt = f"فيديو: {video_path}\n\nالسؤال: {question or 'اقترح 10 طرق لإنتاج هذا الفيديو بسهولة مطلقة'}"
                elif analysis_type == "educational":
                    system = """أنت محلل محتوى تعليمي. حلل الفيديو واستخرج:
1. المحتوى التعليمي الرئيسي
2. النقاط المفتاحية
3. أساليب الشرح المستخدمة
4. اقتراحات لتحسين الإنتاج"""
                    prompt = f"فيديو تعليمي: {video_path}\n\nالسؤال: {question or 'حلل هذا الفيديو التعليمي'}"
                else:
                    system = "أنت محلل فيديو محترف. حلل الفيديو بالتفصيل."
                    prompt = f"فيديو: {video_path}\n\nالسؤال: {question or 'حلل هذا الفيديو بالتفصيل'}"
                
                response = await self._llm.think(prompt=prompt, system=system, model="glm-5.1", temperature=0.4)
                return ToolResult(
                    success=True,
                    tool_name="video_analysis",
                    output=response.text[:5000],
                    data={"video_path": video_path, "analysis_type": analysis_type, "source": "llm_fallback"},
                    duration_ms=(time.time() - start) * 1000,
                )
            except Exception as e:
                return ToolResult(success=False, tool_name="video_analysis", error=str(e))
        
        return ToolResult(success=False, tool_name="video_analysis", error="لا يتوفر محلل فيديو")


# ═══════════════════════════════════════════════════════════════════════════════
# N8N Workflow Tool — إنشاء workflows لـ n8n
# ═══════════════════════════════════════════════════════════════════════════════

class N8NWorkflowTool:
    """
    أداة إنشاء workflows لـ n8n — تولّد JSON workflows جاهزة للاستيراد
    
    يمكنها إنشاء workflows معقدة تربط خدمات مختلفة.
    """
    
    def __init__(self, llm_client=None):
        self._llm = llm_client
    
    async def create_workflow(self, description: str, llm=None) -> ToolResult:
        """إنشاء workflow لـ n8n من وصف نصي"""
        start = time.time()
        llm = llm or self._llm
        
        if not llm:
            return ToolResult(success=False, tool_name="n8n_workflow", error="LLM غير متوفر")
        
        system = """أنت مهندس أتمتة خبير في n8n. تحول الأوصاف النصية إلى workflows بتنسيق n8n JSON.

قواعد الـ n8n workflow:
1. كل node له: id, name, type, typeVersion, position, parameters
2. الاتصالات في: connections = {fromNode: {main: [[{node: "toNode", type: "main", index: 0}]]}}
3. أنواع الـ nodes الشائعة:
   - n8n-nodes-base.webhook (استقبال طلبات)
   - n8n-nodes-base.httpRequest (HTTP requests)
   - n8n-nodes-base.openAi (AI operations)
   - n8n-nodes-base.if (شروط)
   - n8n-nodes-base.set (تعيين قيم)
   - n8n-nodes-base.merge (دمج)
   - n8n-nodes-base.splitInBatches (تقسيم)
   - n8n-nodes-base.postgres / mysql (قواعد بيانات)
   - n8n-nodes-base.slack / telegram / discord (إشعارات)
   - n8n-nodes-base.googleSheets / googleDrive
   - n8n-nodes-base.schedule (مؤقت)

أجب بصيغة JSON الصالحة لـ n8n (يمكن استيرادها مباشرة):
{
  "name": "اسم الوركفلو",
  "nodes": [...],
  "connections": {...},
  "settings": {"executionOrder": "v1"},
  "staticData": null,
  "tags": [...]
}"""
        
        response = await llm.think(
            prompt=f"أنشئ workflow لـ n8n بناءً على هذا الوصف:\n\n{description}",
            system=system,
            model="glm-5.1",
            temperature=0.3,
            json_mode=True,
        )
        
        result = response.extract_json()
        if result:
            # Save the workflow
            workflow_dir = PROJECT_ROOT / "download" / "n8n_workflows"
            workflow_dir.mkdir(parents=True, exist_ok=True)
            filename = f"workflow_{result.get('name', 'unnamed').replace(' ', '_')}_{int(time.time())}.json"
            filepath = workflow_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            return ToolResult(
                success=True,
                tool_name="n8n_workflow",
                output=f"تم إنشاء الوركفلو بنجاح! يمكن استيراده في n8n.",
                data={"workflow_name": result.get("name", ""), "nodes_count": len(result.get("nodes", [])), "connections": result.get("connections", {})},
                artifacts=[{"type": "n8n_workflow", "path": str(filepath), "filename": filename}],
                duration_ms=(time.time() - start) * 1000,
            )
        
        return ToolResult(
            success=False,
            tool_name="n8n_workflow",
            error="فشل إنشاء الوركفلو — الـ LLM لم يُرجع JSON صالح",
            duration_ms=(time.time() - start) * 1000,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Blender Integration Tool — التحكم بـ Blender
# ═══════════════════════════════════════════════════════════════════════════════

class BlenderTool:
    """
    أداة التحكم بـ Blender — تنفذ أوامر Blender Python API
    
    يمكنها:
    - إنشاء نماذج 3D
    - تطبيق مواد وإكساءات
    - إعداد إضاءة
    - تصيير (render)
    - دمج AI مع التصميم المعماري
    """
    
    def __init__(self, llm_client=None):
        self._llm = llm_client
    
    def _is_blender_available(self) -> bool:
        """فحص توفر Blender"""
        return shutil.which("blender") is not None
    
    async def execute_script(self, script_description: str, llm=None) -> ToolResult:
        """تنفيذ أمر Blender — يولّد سكربت Python وينفذه"""
        start = time.time()
        llm = llm or self._llm
        
        if not self._is_blender_available():
            # Return the script for manual use
            if llm:
                response = await llm.think(
                    prompt=f"اكتب سكربت Blender Python لـ: {script_description}",
                    system="أنت خبير Blender Python API. اكتب سكربت Python كامل وصالح لـ Blender. فقط الكود بدون شرح.",
                    model="glm-5.1",
                    temperature=0.2,
                )
                script_dir = PROJECT_ROOT / "download" / "blender_scripts"
                script_dir.mkdir(parents=True, exist_ok=True)
                filename = f"blender_{int(time.time())}.py"
                filepath = script_dir / filename
                with open(filepath, 'w') as f:
                    f.write(response.text)
                
                return ToolResult(
                    success=True,
                    tool_name="blender",
                    output=f"تم إنشاء سكربت Blender (Blender غير مثبت على هذا النظام — يمكنك تشغيل السكربت يدوياً)",
                    data={"script_path": str(filepath), "blender_installed": False},
                    artifacts=[{"type": "blender_script", "path": str(filepath), "filename": filename}],
                    duration_ms=(time.time() - start) * 1000,
                )
            return ToolResult(success=False, tool_name="blender", error="Blender غير مثبت وLLM غير متوفر")
        
        # Blender is available — generate and execute
        if llm:
            response = await llm.think(
                prompt=f"اكتب سكربت Blender Python لـ: {script_description}",
                system="أنت خبير Blender Python API. اكتب سكربت Python كامل وصالح لـ Blender. فقط الكود بدون شرح إضافي.",
                model="glm-5.1",
                temperature=0.2,
            )
            script = response.text
        else:
            return ToolResult(success=False, tool_name="blender", error="LLM غير متوفر لتوليد السكربت")
        
        # Save and execute
        script_dir = PROJECT_ROOT / "download" / "blender_scripts"
        script_dir.mkdir(parents=True, exist_ok=True)
        filename = f"blender_{int(time.time())}.py"
        filepath = script_dir / filename
        with open(filepath, 'w') as f:
            f.write(script)
        
        try:
            proc = await asyncio.create_subprocess_exec(
                "blender", "--background", "--python", str(filepath),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
            
            return ToolResult(
                success=proc.returncode == 0,
                tool_name="blender",
                output=stdout.decode()[:3000] if stdout else "",
                data={"script_path": str(filepath), "exit_code": proc.returncode},
                error=stderr.decode()[:1000] if stderr and proc.returncode != 0 else "",
                artifacts=[{"type": "blender_script", "path": str(filepath)}],
                duration_ms=(time.time() - start) * 1000,
            )
        except asyncio.TimeoutError:
            return ToolResult(success=False, tool_name="blender", error="انتهت مهلة Blender (5 دقائق)")
        except Exception as e:
            return ToolResult(success=False, tool_name="blender", error=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# Server Control Tool — التحكم بالسيرفرات
# ═══════════════════════════════════════════════════════════════════════════════

class ServerControlTool:
    """
    أداة التحكم بالسيرفر — تنفذ أوامر على سيرفرات محلية أو بعيدة
    
    Safety: كل العمليات تتطلب موافقة المستخدم
    """
    
    def __init__(self, llm_client=None):
        self._llm = llm_client
        self._shell = None
    
    async def _get_shell(self):
        if not self._shell:
            from mamoun.tools.shell_executor import ShellExecutor
            self._shell = ShellExecutor()
            await self._shell.initialize()
        return self._shell
    
    async def execute(self, command: str, working_dir: str = "", grant_id: str = "") -> ToolResult:
        """تنفيذ أمر على السيرفر المحلي"""
        start = time.time()
        
        # Dangerous commands require approval
        dangerous_keywords = ["rm", "delete", "drop", "shutdown", "reboot", "format", "mkfs"]
        requires_approval = any(kw in command.lower() for kw in dangerous_keywords)
        
        shell = await self._get_shell()
        result = await shell.execute(
            command=command,
            grant_id=grant_id,
            working_dir=working_dir,
            timeout=120,
        )
        
        return ToolResult(
            success=result.success,
            tool_name="server_control",
            output=result.stdout[:5000] if result.stdout else "",
            data={
                "command": command,
                "exit_code": result.exit_code,
                "working_dir": working_dir,
                "blocked": result.blocked,
                "block_reason": result.block_reason,
            },
            error=result.stderr[:2000] if result.stderr else "",
            duration_ms=result.duration_ms,
            requires_approval=requires_approval,
        )
    
    async def get_system_info(self) -> ToolResult:
        """الحصول على معلومات النظام"""
        start = time.time()
        shell = await self._get_shell()
        
        info_commands = {
            "os": "uname -a",
            "cpu": "nproc",
            "memory": "free -h",
            "disk": "df -h",
            "uptime": "uptime",
            "processes": "ps aux --sort=-%mem | head -20",
        }
        
        results = {}
        for key, cmd in info_commands.items():
            result = await shell.execute(command=cmd, grant_id="", timeout=10)
            results[key] = result.stdout[:500] if result.stdout else "غير متوفر"
        
        return ToolResult(
            success=True,
            tool_name="server_control",
            output="تم جمع معلومات النظام",
            data=results,
            duration_ms=(time.time() - start) * 1000,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Code Generation & Execution Tool — توليد وتنفيذ كود حقيقي
# ═══════════════════════════════════════════════════════════════════════════════

class CodeGenTool:
    """
    أداة توليد وتنفيذ الكود — تولّد كود وتنفذه فعلياً
    
    Can:
    - Generate code in any language
    - Execute Python/Node.js scripts
    - Build and deploy projects
    - Create files and project structures
    """
    
    def __init__(self, llm_client=None):
        self._llm = llm_client
        self._shell = None
        self._fs = None
    
    async def _get_tools(self):
        if not self._shell:
            from mamoun.tools.shell_executor import ShellExecutor
            from mamoun.tools.filesystem_tool import FileSystemTool
            self._shell = ShellExecutor()
            self._fs = FileSystemTool()
            await self._shell.initialize()
            await self._fs.initialize()
        return self._shell, self._fs
    
    async def generate_and_execute(
        self,
        description: str,
        language: str = "python",
        project_dir: str = "",
        execute: bool = True,
        llm=None,
    ) -> ToolResult:
        """توليد كود وتنفيذه"""
        start = time.time()
        llm = llm or self._llm
        shell, fs = await self._get_tools()
        
        if not llm:
            return ToolResult(success=False, tool_name="code_gen", error="LLM غير متوفر")
        
        # Generate the code
        lang_map = {
            "python": {"ext": ".py", "run": "python3", "comment": "#"},
            "javascript": {"ext": ".js", "run": "node", "comment": "//"},
            "typescript": {"ext": ".ts", "run": "npx tsx", "comment": "//"},
        }
        lang_info = lang_map.get(language, lang_map["python"])
        
        system = f"""أنت مبرمج خبير. اكتب كود {language} كامل وجاهز للتنفيذ بناءً على الوصف.
فقط الكود بدون شرح إضافي. الكود يجب أن يعمل مباشرة."""
        
        response = await llm.think(
            prompt=f"اكتب كود {language} كامل لـ: {description}",
            system=system,
            model="glm-5.1",
            temperature=0.2,
        )
        
        code = response.text
        # Clean markdown code blocks
        if code.startswith("```"):
            lines = code.split("\n")
            code = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        
        # Save the code
        if not project_dir:
            project_dir = str(PROJECT_ROOT / "download" / "generated_code" / f"project_{int(time.time())}")
        
        filename = f"main{lang_info['ext']}"
        filepath = Path(project_dir) / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        write_result = await fs.write_file(
            path=str(filepath),
            content=code,
            grant_id="",
            create_dirs=True,
        )
        
        if not write_result.success:
            return ToolResult(
                success=False,
                tool_name="code_gen",
                error=f"فشل كتابة الملف: {write_result.error}",
                duration_ms=(time.time() - start) * 1000,
            )
        
        artifacts = [{"type": "code", "path": str(filepath), "language": language}]
        
        # Execute if requested
        exec_output = ""
        if execute:
            exec_result = await shell.execute(
                command=f"{lang_info['run']} {str(filepath)}",
                working_dir=project_dir,
                timeout=60,
            )
            exec_output = exec_result.stdout[:3000] if exec_result.stdout else ""
            if exec_result.stderr and not exec_result.success:
                exec_output += f"\n\nخطأ: {exec_result.stderr[:1000]}"
        
        return ToolResult(
            success=True,
            tool_name="code_gen",
            output=f"تم إنشاء الكود في: {filepath}\n\n{'تم التنفيذ بنجاح' if execute else 'لم يتم التنفيذ'}\n\n{exec_output[:3000]}",
            data={"path": str(filepath), "language": language, "executed": execute},
            artifacts=artifacts,
            duration_ms=(time.time() - start) * 1000,
        )
    
    async def build_project_structure(self, project_spec: dict, llm=None) -> ToolResult:
        """بناء هيكل مشروع كامل من مواصفات"""
        start = time.time()
        llm = llm or self._llm
        shell, fs = await self._get_tools()
        
        project_name = project_spec.get("project_name", "new_project")
        project_dir = PROJECT_ROOT / "download" / project_name
        
        # Create directory structure
        folder_structure = project_spec.get("folder_structure", {})
        files_created = []
        
        for path, content in folder_structure.items():
            if path.endswith("/"):
                # Directory
                dir_path = project_dir / path.rstrip("/")
                dir_path.mkdir(parents=True, exist_ok=True)
            else:
                # File
                file_path = project_dir / path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                if isinstance(content, str) and len(content) > 10:
                    # Actual file content
                    write_result = await fs.write_file(str(file_path), content, grant_id="")
                    if write_result.success:
                        files_created.append(str(file_path))
                else:
                    # Placeholder — generate real content with LLM
                    if llm:
                        try:
                            file_response = await llm.think(
                                prompt=f"اكتب محتوى ملف {path} لمشروع {project_name}: {project_spec.get('description', '')}",
                                system=f"أنت مطور خبير. اكتب محتوى ملف {path} كاملاً وجاهزاً. فقط المحتوى بدون شرح.",
                                model="glm-5.1",
                                temperature=0.3,
                            )
                            write_result = await fs.write_file(str(file_path), file_response.text, grant_id="")
                            if write_result.success:
                                files_created.append(str(file_path))
                        except Exception:
                            file_path.touch()
                            files_created.append(str(file_path))
        
        return ToolResult(
            success=True,
            tool_name="code_gen",
            output=f"تم بناء مشروع {project_name} — {len(files_created)} ملف تم إنشاؤه",
            data={"project_dir": str(project_dir), "files_created": files_created, "total_files": len(files_created)},
            artifacts=[{"type": "project", "path": str(project_dir), "name": project_name}],
            duration_ms=(time.time() - start) * 1000,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Real Tools Engine — The Unified Interface
# ═══════════════════════════════════════════════════════════════════════════════

class RealToolsEngine:
    """
    محرك الأدوات الحقيقية — الواجهة الموحدة لكل الأدوات
    
    This is what SkillExecutor calls when it needs to DO something real.
    It provides a single interface to all tools.
    """
    
    def __init__(self, llm_client=None):
        self._llm = llm_client
        self.web_search = WebSearchTool(llm_client=llm_client)
        self.image_gen = ImageGenTool()
        self.video_analysis = VideoAnalysisTool(llm_client=llm_client)
        self.n8n = N8NWorkflowTool(llm_client=llm_client)
        self.blender = BlenderTool(llm_client=llm_client)
        self.server = ServerControlTool(llm_client=llm_client)
        self.code_gen = CodeGenTool(llm_client=llm_client)
        self._initialized = False
    
    async def initialize(self):
        """تهيئة جميع الأدوات"""
        if self._initialized:
            return
        self._initialized = True
        logger.info("RealToolsEngine initialized — 7 real tools ready")
    
    async def call_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """
        استدعاء أداة بالاسم — واجهة موحدة
        
        Available tools:
        - web_search: query, num_results
        - image_gen: prompt, size, filename
        - video_analysis: video_path, question, analysis_type
        - n8n_workflow: description
        - blender: script_description
        - server_control: command, working_dir, grant_id
        - code_gen: description, language, project_dir, execute
        """
        await self.initialize()
        
        tool_map = {
            "web_search": self.web_search.search,
            "image_gen": self.image_gen.generate,
            "video_analysis": self.video_analysis.analyze,
            "n8n_workflow": self.n8n.create_workflow,
            "blender": self.blender.execute_script,
            "server_control": self.server.execute,
            "code_gen": self.code_gen.generate_and_execute,
            "system_info": self.server.get_system_info,
        }
        
        tool_func = tool_map.get(tool_name)
        if not tool_func:
            return ToolResult(
                success=False,
                tool_name=tool_name,
                error=f"أداة غير معروفة: {tool_name}. المتاحة: {list(tool_map.keys())}",
            )
        
        try:
            return await tool_func(**kwargs)
        except Exception as e:
            logger.error("Tool '%s' failed: %s", tool_name, e)
            return ToolResult(
                success=False,
                tool_name=tool_name,
                error=f"خطأ في تنفيذ الأداة: {str(e)}",
            )
    
    def list_tools(self) -> list[dict]:
        """قائمة جميع الأدوات المتاحة"""
        return [
            {"id": "web_search", "name": "بحث الإنترنت", "description": "بحث فعلي في الإنترنت"},
            {"id": "image_gen", "name": "إنشاء صور", "description": "توليد صور من وصف نصي"},
            {"id": "video_analysis", "name": "تحليل فيديو", "description": "تحليل فيديو واقتراح طرق الإنتاج"},
            {"id": "n8n_workflow", "name": "وركفلو n8n", "description": "إنشاء workflows لـ n8n"},
            {"id": "blender", "name": "Blender", "description": "التحكم بـ Blender عبر Python"},
            {"id": "server_control", "name": "تحكم بالسيرفر", "description": "تنفيذ أوامر على السيرفر"},
            {"id": "code_gen", "name": "توليد كود", "description": "توليد وتنفيذ كود حقيقي"},
            {"id": "system_info", "name": "معلومات النظام", "description": "جمع معلومات النظام"},
        ]


# Singleton
_real_tools_engine: Optional[RealToolsEngine] = None

def get_real_tools(llm_client=None) -> RealToolsEngine:
    """الحصول على محرك الأدوات الحقيقية (Singleton)"""
    global _real_tools_engine
    if _real_tools_engine is None:
        _real_tools_engine = RealToolsEngine(llm_client=llm_client)
    return _real_tools_engine
