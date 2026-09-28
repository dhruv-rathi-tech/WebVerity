"""
Round 3 Submission Packaging Script.
Creates a clean, validated ZIP suitable for Adobe Hackathon Round 3 marketplace submission.

Excludes:
- .git/ and .github/
- __pycache__/ directories
- *.pyc compiled bytecode
- *.pyo optimized bytecode
- local environment files (.env, .venv, etc.)
- IDE artifacts (.vscode/, .idea/)
- temporary files and OS artifacts
- test output and cache files
- prompts/ (internal dev working directory, not marketplace files)

Includes:
- marketplace.json
- README.md
- skills/ (all 5 skills with SKILL.md, scripts/, references/)
- core/ (shared runtime modules required by skills)
- audit/ (canonical CLI entrypoint package)
- scripts/validate_marketplace.py (submission validator)
- docs/ (architecture documentation)
- tests/ (evaluation harness)
"""

import os
import sys
import json
import zipfile
import shutil
import tempfile
import argparse
import subprocess
from pathlib import Path

EXCLUDED_DIRS = {
    ".git", ".github", "__pycache__", ".venv", "venv", ".env",
    ".vscode", ".idea", "node_modules", ".mypy_cache", ".pytest_cache",
    "prompts",  # internal dev working notes, not marketplace content
}

EXCLUDED_EXTENSIONS = {".pyc", ".pyo", ".log", ".tmp", ".DS_Store", ".Thumbs.db", ".zip"}

EXCLUDED_FILES = {".gitignore", ".gitattributes", ".env", ".env.local"}

REQUIRED_MARKETPLACE_FILES = [
    "marketplace.json",
    "README.md",
    "requirements.txt",
    "skills/audit-orchestrator/SKILL.md",
    "skills/audit-orchestrator/scripts/orchestrate.py",
    "skills/audit-orchestrator/references/report-schema.json",
    "skills/crawl-render-audit/SKILL.md",
    "skills/crawl-render-audit/scripts/inspect_crawler.py",
    "skills/crawl-render-audit/references/bot-user-agents.json",
    "skills/structured-data-entity-audit/SKILL.md",
    "skills/structured-data-entity-audit/scripts/validate_schema.py",
    "skills/structured-data-entity-audit/references/schema-types.json",
    "skills/freshness-corroboration-audit/SKILL.md",
    "skills/freshness-corroboration-audit/scripts/check_freshness.py",
    "skills/freshness-corroboration-audit/references/temporal-rules.json",
    "skills/engagement-audit/SKILL.md",
    "skills/engagement-audit/scripts/inspect_engagement.py",
    "skills/engagement-audit/references/heading-rules.json",
    "core/models.py",
    "core/crawler.py",
    "core/classifier.py",
    "core/extractor.py",
    "core/robots.py",
    "core/sitemap.py",
    "core/url_utils.py",
    "core/diff_analyzer.py",
    "core/engagement_analyzer.py",
    "core/freshness_analyzer.py",
    "core/schema_analyzer.py",
    "core/renderer.py",
    "audit/__init__.py",
    "audit/__main__.py",
]

MAX_ZIP_SIZE_MB = 50.0


def should_exclude(path: str, rel_path: str) -> bool:
    """Determine if a file or directory should be excluded from the ZIP."""
    parts = Path(rel_path).parts

    # Check any path component against excluded dirs
    for part in parts:
        if part in EXCLUDED_DIRS:
            return True

    filename = os.path.basename(path)
    if filename in EXCLUDED_FILES:
        return True

    ext = os.path.splitext(filename)[1].lower()
    if ext in EXCLUDED_EXTENSIONS:
        return True

    return False


def create_submission_zip(root_dir: str, output_path: str) -> dict:
    """
    Creates the submission ZIP, excluding development artifacts.
    Returns a dict with packaging statistics.
    """
    included_files = []
    excluded_files = []
    total_uncompressed = 0

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for dirpath, dirnames, filenames in os.walk(root_dir):
            # Prune excluded dirs in-place to prevent descent
            dirnames[:] = [d for d in dirnames if not should_exclude(
                os.path.join(dirpath, d),
                os.path.relpath(os.path.join(dirpath, d), root_dir)
            )]

            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                rel_path = os.path.relpath(filepath, root_dir)

                if should_exclude(filepath, rel_path):
                    excluded_files.append(rel_path)
                    continue

                zf.write(filepath, rel_path)
                size = os.path.getsize(filepath)
                included_files.append((rel_path, size))
                total_uncompressed += size

    zip_size = os.path.getsize(output_path)
    return {
        "included_files": sorted(included_files, key=lambda x: -x[1]),
        "excluded_files": sorted(excluded_files),
        "file_count": len(included_files),
        "total_uncompressed_mb": round(total_uncompressed / (1024 * 1024), 3),
        "zip_size_mb": round(zip_size / (1024 * 1024), 3),
        "zip_size_bytes": zip_size,
    }


def validate_extracted_zip(zip_path: str, validator_root: str) -> dict:
    """
    Extracts the ZIP to a temp directory and runs:
    1. Required file presence checks
    2. marketplace validator from the extracted directory
    3. CLI smoke test (--help)
    """
    results = {
        "required_files": {},
        "marketplace_validator": None,
        "cli_smoke_test": None,
        "errors": [],
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        # Extract ZIP
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmpdir)

        # 1. Required file presence
        for req_file in REQUIRED_MARKETPLACE_FILES:
            full_path = os.path.join(tmpdir, req_file)
            exists = os.path.isfile(full_path)
            results["required_files"][req_file] = "PRESENT" if exists else "MISSING"
            if not exists:
                results["errors"].append(f"MISSING required file: {req_file}")

        # 2. Marketplace validator (copy validate_marketplace.py to tmpdir and run)
        validator_src = os.path.join(validator_root, "scripts", "validate_marketplace.py")
        if os.path.isfile(validator_src):
            validator_dst = os.path.join(tmpdir, "scripts", "validate_marketplace.py")
            # Validator is already in the ZIP since scripts/validate_marketplace.py is included
            if os.path.isfile(validator_dst):
                try:
                    proc = subprocess.run(
                        [sys.executable, "scripts/validate_marketplace.py"],
                        capture_output=True, text=True, cwd=tmpdir, timeout=30
                    )
                    results["marketplace_validator"] = {
                        "exit_code": proc.returncode,
                        "stdout": proc.stdout.strip(),
                        "stderr": proc.stderr.strip(),
                        "passed": proc.returncode == 0,
                    }
                except Exception as e:
                    results["marketplace_validator"] = {"error": str(e), "passed": False}

        # 3. CLI smoke test: python -m audit --help
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "audit", "--help"],
                capture_output=True, text=True, cwd=tmpdir, timeout=30
            )
            results["cli_smoke_test"] = {
                "exit_code": proc.returncode,
                "stdout": proc.stdout.strip()[:500],
                "stderr": proc.stderr.strip()[:200],
                "passed": proc.returncode == 0 and "usage" in proc.stdout.lower(),
            }
        except Exception as e:
            results["cli_smoke_test"] = {"error": str(e), "passed": False}

    return results


def main():
    parser = argparse.ArgumentParser(description="Package Round 3 submission ZIP.")
    parser.add_argument("--root", default=".", help="Repository root directory (default: .)")
    parser.add_argument("--output", default="brand-ai-readiness-audit-round3.zip", help="Output ZIP filename")
    args = parser.parse_args()

    root_dir = os.path.abspath(args.root)
    output_path = os.path.abspath(args.output)

    print("=" * 60)
    print("  ROUND 3 SUBMISSION PACKAGING")
    print("=" * 60)
    print(f"  Source: {root_dir}")
    print(f"  Output: {output_path}")
    print()

    # Step 1: Create ZIP
    print("[1/3] Creating submission ZIP...")
    stats = create_submission_zip(root_dir, output_path)

    print(f"  Files included:      {stats['file_count']}")
    print(f"  Uncompressed size:   {stats['total_uncompressed_mb']} MB")
    print(f"  Compressed ZIP size: {stats['zip_size_mb']} MB")

    if stats["zip_size_mb"] > MAX_ZIP_SIZE_MB:
        print(f"\n  [FAIL] ZIP size {stats['zip_size_mb']} MB exceeds {MAX_ZIP_SIZE_MB} MB limit!")
        return 1
    else:
        print(f"  [OK] ZIP size within {MAX_ZIP_SIZE_MB} MB limit.")

    # Step 2: Validate extracted ZIP
    print("\n[2/3] Validating extracted ZIP contents...")
    validation = validate_extracted_zip(output_path, root_dir)

    missing = [f for f, s in validation["required_files"].items() if s == "MISSING"]
    if missing:
        print(f"  [FAIL] Missing required files:")
        for f in missing:
            print(f"    - {f}")
        return 1
    else:
        print(f"  [OK] All {len(REQUIRED_MARKETPLACE_FILES)} required files present in ZIP.")

    mp_val = validation.get("marketplace_validator")
    if mp_val:
        if mp_val.get("passed"):
            print("  [OK] Marketplace validator passed from extracted ZIP.")
        else:
            print(f"  [FAIL] Marketplace validator failed: {mp_val}")
    else:
        print("  [SKIP] Marketplace validator not found in extracted ZIP.")

    cli_test = validation.get("cli_smoke_test")
    if cli_test:
        if cli_test.get("passed"):
            print("  [OK] CLI smoke test (python -m audit --help) passed from extracted ZIP.")
        else:
            print(f"  [FAIL] CLI smoke test failed: {cli_test}")
    else:
        print("  [SKIP] CLI smoke test not run.")

    # Step 3: Print top 10 largest files
    print("\n[3/3] Top 10 largest files in submission:")
    for rel, size in stats["included_files"][:10]:
        print(f"  {size:>10,} bytes   {rel}")

    print()
    print("=" * 60)
    if not missing and (not mp_val or mp_val.get("passed")) and (not cli_test or cli_test.get("passed")):
        print("  PACKAGING COMPLETE — ZIP IS VALID AND SUBMISSION-READY")
    else:
        print("  PACKAGING COMPLETE — REVIEW WARNINGS ABOVE")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
