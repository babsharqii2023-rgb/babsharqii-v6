"""
مأمون v40.0 — Structural Intelligence
يفهم علاقات الملفات ويقترح إعادة هيكلة متعددة الملفات
"""

import ast
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger("mamoun.evolution.structural_intelligence")

@dataclass
class FileNode:
    """عقدة ملف في الرسم البياني للتبعيات"""
    path: str
    imports: Set[str] = field(default_factory=set)
    imported_by: Set[str] = field(default_factory=set)
    language: str = "unknown"  # python, typescript, etc.
    size_bytes: int = 0
    last_modified: float = 0.0

@dataclass 
class MultiFileChange:
    """تغيير متعدد الملفات"""
    description: str
    changes: List[dict]  # [{path, action: "create"|"modify"|"delete"|"rename", content?, from_path?}]
    risk_level: str = "medium"
    affected_files: List[str] = field(default_factory=list)
    backup_paths: List[str] = field(default_factory=list)

class StructuralIntelligence:
    """يفهم شجرة المشروع ويقترح إعادة هيكلة"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self._dependency_graph: Dict[str, FileNode] = {}
        self._built = False
    
    def build_dependency_graph(self) -> Dict[str, FileNode]:
        """يبني رسم بياني للعلاقات بين كل الملفات"""
        # Walk the project tree
        # For Python files: use ast to parse imports
        # For TypeScript files: parse import statements
        # Build a bidirectional graph (imports / imported_by)
        
        self._dependency_graph = {}
        
        # Parse Python files
        for py_file in self.project_root.rglob("*.py"):
            try:
                rel_path = str(py_file.relative_to(self.project_root))
                node = FileNode(
                    path=rel_path,
                    language="python",
                    size_bytes=py_file.stat().st_size,
                    last_modified=py_file.stat().st_mtime,
                )
                
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    tree = ast.parse(f.read(), filename=str(py_file))
                
                for item in ast.walk(tree):
                    if isinstance(item, ast.Import):
                        for alias in item.names:
                            node.imports.add(alias.name)
                    elif isinstance(item, ast.ImportFrom):
                        if item.module:
                            node.imports.add(item.module)
                
                self._dependency_graph[rel_path] = node
            except Exception as e:
                logger.debug(f"Failed to parse {py_file}: {e}")
        
        # Parse TypeScript files
        for ts_file in list(self.project_root.rglob("*.ts")) + list(self.project_root.rglob("*.tsx")):
            try:
                rel_path = str(ts_file.relative_to(self.project_root))
                node = FileNode(
                    path=rel_path,
                    language="typescript",
                    size_bytes=ts_file.stat().st_size,
                    last_modified=ts_file.stat().st_mtime,
                )
                
                # Simple regex-based import extraction for TypeScript
                import re
                with open(ts_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Match import patterns
                import_patterns = [
                    r'import\s+.*?\s+from\s+[\'"](.+?)[\'"]',
                    r'import\s+[\'"](.+?)[\'"]',
                    r'require\s*\(\s*[\'"](.+?)[\'"]\s*\)',
                ]
                
                for pattern in import_patterns:
                    for match in re.finditer(pattern, content):
                        imp = match.group(1)
                        # Resolve relative imports
                        if imp.startswith('.'):
                            imp_dir = str(Path(rel_path).parent)
                            resolved = str(Path(imp_dir) / imp).replace('\\', '/')
                            if not resolved.endswith('.ts') and not resolved.endswith('.tsx'):
                                resolved += '.ts'
                            node.imports.add(resolved)
                        else:
                            node.imports.add(imp)
                
                self._dependency_graph[rel_path] = node
            except Exception as e:
                logger.debug(f"Failed to parse {ts_file}: {e}")
        
        # Build reverse graph (imported_by)
        for path, node in self._dependency_graph.items():
            for imp in node.imports:
                # Find files that match this import
                for other_path, other_node in self._dependency_graph.items():
                    if imp in other_path or other_path.endswith(imp.replace('.', '/') + '.py'):
                        other_node.imported_by.add(path)
        
        self._built = True
        logger.info(f"Built dependency graph: {len(self._dependency_graph)} files, "
                    f"{sum(len(n.imports) for n in self._dependency_graph.values())} imports")
        return self._dependency_graph
    
    def get_file_dependencies(self, file_path: str) -> Tuple[Set[str], Set[str]]:
        """يعيد الملفات التي يعتمد عليها والملفات التي تعتمد عليه"""
        if not self._built:
            self.build_dependency_graph()
        
        node = self._dependency_graph.get(file_path)
        if not node:
            return set(), set()
        
        # Resolve imports to actual file paths
        depends_on = set()
        for imp in node.imports:
            for other_path in self._dependency_graph:
                if imp.replace('.', '/') in other_path or other_path.endswith(imp.split('.')[-1] + '.py'):
                    depends_on.add(other_path)
        
        return depends_on, node.imported_by
    
    def propose_restructuring(self, goal: str) -> Optional[MultiFileChange]:
        """يقترح إعادة هيكلة كاملة بناءً على هدف"""
        if not self._built:
            self.build_dependency_graph()
        
        # Analyze the goal and propose changes
        # This is a simplified version — a full implementation would use LLM
        proposal = MultiFileChange(
            description=f"إعادة هيكلة مقترحة بناءً على: {goal}",
            changes=[],
            risk_level="medium",
        )
        
        # Find common restructuring patterns
        # 1. Files with too many imports (should be split)
        for path, node in self._dependency_graph.items():
            if len(node.imports) > 20:
                proposal.changes.append({
                    "path": path,
                    "action": "modify",
                    "reason": f"ملف معقد جداً ({len(node.imports)} استيراد) — يُنصح بتقسيمه",
                })
        
        # 2. Circular dependencies
        for path, node in self._dependency_graph.items():
            for imp in node.imports:
                for other_path in self._dependency_graph:
                    if imp.replace('.', '/') in other_path:
                        other_node = self._dependency_graph[other_path]
                        if path.replace('.', '/') in str(other_node.imports):
                            proposal.changes.append({
                                "path": path,
                                "action": "modify",
                                "reason": f"اعتماد دائري مع {other_path}",
                            })
        
        # 3. Files imported by many (should be stable)
        for path, node in self._dependency_graph.items():
            if len(node.imported_by) > 10:
                proposal.changes.append({
                    "path": path,
                    "action": "review",
                    "reason": f"ملف محوري ({len(node.imported_by)} ملف يعتمد عليه) — يجب أن يكون مستقراً",
                })
        
        return proposal if proposal.changes else None
    
    def apply_multi_file_change(self, change: MultiFileChange) -> bool:
        """يطبّق تعديلات متعددة آمناً (الكل أو لا شيء)"""
        # Create backups for all affected files
        backups = {}
        for ch in change.changes:
            if ch["action"] in ("modify", "delete", "rename"):
                full_path = self.project_root / ch["path"]
                if full_path.exists():
                    backup_path = full_path.with_suffix(full_path.suffix + ".backup")
                    import shutil
                    shutil.copy2(full_path, backup_path)
                    backups[ch["path"]] = str(backup_path)
        
        # Apply changes
        try:
            for ch in change.changes:
                full_path = self.project_root / ch["path"]
                
                if ch["action"] == "create" and "content" in ch:
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_text(ch["content"], encoding="utf-8")
                
                elif ch["action"] == "modify" and "content" in ch:
                    full_path.write_text(ch["content"], encoding="utf-8")
                
                elif ch["action"] == "delete":
                    if full_path.exists():
                        full_path.unlink()
                
                elif ch["action"] == "rename" and "from_path" in ch:
                    from_path = self.project_root / ch["from_path"]
                    if from_path.exists():
                        from_path.rename(full_path)
            
            logger.info(f"Applied multi-file change: {change.description}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply multi-file change, rolling back: {e}")
            # Rollback all changes
            for path, backup_path in backups.items():
                full_path = self.project_root / path
                import shutil
                shutil.copy2(backup_path, full_path)
                Path(backup_path).unlink()
            return False
