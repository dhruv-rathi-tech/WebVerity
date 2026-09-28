"""
WebVerity Audit Module Package.
Provides canonical programmatic and CLI access to the WebVerity AI-Readiness & Website Intelligence pipeline.
Forwards directly to the designated entrypoint skill: skills/audit-orchestrator.
"""

import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import importlib.util

_orch_path = os.path.join(_ROOT, "skills", "audit-orchestrator", "scripts", "orchestrate.py")
_spec = importlib.util.spec_from_file_location("orchestrate", _orch_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

AuditOrchestrator = _mod.AuditOrchestrator
orchestrate_audit = _mod.orchestrate_audit
render_markdown_report = _mod.render_markdown_report
main = _mod.main

__all__ = [
    "AuditOrchestrator",
    "orchestrate_audit",
    "render_markdown_report",
    "main",
]
