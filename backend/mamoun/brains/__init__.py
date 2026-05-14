"""
BABSHARQII v40.0 — The 5 Brains Package

Enhanced (v40.0 Mamoun):
- Manifest compatibility check function for environment validation
"""

import json
import logging
import platform
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def check_manifest_compatibility() -> dict:
    """
    فحص توافق البيئة الحالية مع متطلبات البيان.
    
    Check if current environment meets manifest requirements.
    Returns a compatibility report with:
    - overall_compatible: bool
    - checks: list of individual check results
    - warnings: list of non-critical issues
    - errors: list of critical issues
    """
    manifest_path = Path(__file__).parent.parent.parent.parent / "agent_manifest.json"
    
    report = {
        "overall_compatible": True,
        "checks": [],
        "warnings": [],
        "errors": [],
        "manifest_found": False,
        "manifest_version": None,
    }
    
    # Load manifest
    manifest = None
    if manifest_path.exists():
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            report["manifest_found"] = True
            report["manifest_version"] = manifest.get("version", "unknown")
        except Exception as e:
            report["errors"].append(f"فشل قراءة البيان: {str(e)}")
            report["overall_compatible"] = False
            return report
    else:
        report["warnings"].append("لم يتم العثور على ملف البيان (agent_manifest.json)")
        report["overall_compatible"] = False
        return report
    
    if not manifest:
        return report
    
    requirements = manifest.get("requirements", {})
    
    # Check Python version
    python_req = requirements.get("python", "3.11+")
    python_version = platform.python_version()
    python_major, python_minor = sys.version_info[:2]
    
    # Parse requirement (e.g., "3.11+" means >= 3.11)
    req_min_version = python_req.rstrip("+")
    req_parts = req_min_version.split(".")
    req_major = int(req_parts[0])
    req_minor = int(req_parts[1]) if len(req_parts) > 1 else 0
    
    python_ok = (python_major, python_minor) >= (req_major, req_minor)
    report["checks"].append({
        "name": "Python Version",
        "name_ar": "إصدار بايثون",
        "required": python_req,
        "current": python_version,
        "passed": python_ok,
    })
    if not python_ok:
        report["errors"].append(
            f"إصدار بايثون غير متوافق: المطلوب {python_req}، الحالي {python_version}"
        )
        report["overall_compatible"] = False
    
    # Check Node.js version
    node_req = requirements.get("nodejs", "20+")
    node_version = _get_node_version()
    node_ok = False
    if node_version:
        node_parts = node_version.split(".")
        node_major = int(node_parts[0]) if node_parts[0].isdigit() else 0
        req_node = node_req.rstrip("+")
        req_node_major = int(req_node.split(".")[0])
        node_ok = node_major >= req_node_major
    else:
        node_ok = False
        node_version = "غير مثبت"
    
    report["checks"].append({
        "name": "Node.js Version",
        "name_ar": "إصدار Node.js",
        "required": node_req,
        "current": node_version,
        "passed": node_ok,
    })
    if not node_ok:
        report["warnings"].append(
            f"Node.js غير متوافق أو غير مثبت: المطلوب {node_req}، الحالي {node_version}"
        )
    
    # Check Docker availability
    docker_req = requirements.get("docker", "optional")
    docker_available = _check_docker()
    report["checks"].append({
        "name": "Docker",
        "name_ar": "داكر",
        "required": docker_req,
        "current": "متوفر" if docker_available else "غير متوفر",
        "passed": True if docker_req == "optional" else docker_available,
    })
    if not docker_available and docker_req != "optional":
        report["errors"].append("داكر غير متوفر ولكنه مطلوب")
        report["overall_compatible"] = False
    elif not docker_available:
        report["warnings"].append("داكر غير متوفر — عزل الصندوق الرملي لن يعمل")
    
    # Check gVisor availability
    gvisor_available = _check_gvisor()
    report["checks"].append({
        "name": "gVisor (runsc)",
        "name_ar": "جي فيزر",
        "required": "optional",
        "current": "متوفر" if gvisor_available else "غير متوفر",
        "passed": True,  # Optional
    })
    if not gvisor_available:
        report["warnings"].append("gVisor غير متوفر — سيتم استخدام runc كبديل مع seccomp")
    
    # Check brain count matches manifest
    manifest_brains = manifest.get("capabilities", {}).get("brains", [])
    report["checks"].append({
        "name": "Brain Count",
        "name_ar": "عدد الأدمغة",
        "required": str(len(manifest_brains)),
        "current": "5",  # We have 5 brains
        "passed": len(manifest_brains) == 5,
    })
    
    # Check safety features
    safety = manifest.get("safety", {})
    report["checks"].append({
        "name": "Safety Features",
        "name_ar": "ميزات الأمان",
        "required": f"{safety.get('immutable_laws', 0)} immutable laws",
        "current": "5 laws",
        "passed": safety.get("immutable_laws", 0) == 5,
    })
    
    return report


def _get_node_version() -> Optional[str]:
    """الحصول على إصدار Node.js."""
    try:
        import subprocess
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            # Output is like "v20.11.0"
            return result.stdout.strip().lstrip("v")
    except Exception:
        pass
    return None


def _check_docker() -> bool:
    """فحص توفر Docker."""
    try:
        import subprocess
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except Exception:
        pass
    return False


def _check_gvisor() -> bool:
    """فحص توفر gVisor (runsc)."""
    try:
        import subprocess
        result = subprocess.run(
            ["which", "runsc"],
            capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except Exception:
        pass
    return False
