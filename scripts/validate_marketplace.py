"""
Marketplace & Skill Validator Script
Validates the structural compliance of marketplace.json and all SKILL.md files
against the agentskills.io format and Adobe Hackathon Round 3 requirements.
"""

import os
import sys
import json
import re
import ast

def validate_marketplace(root_dir: str):
    print("==================================================")
    print("  VALIDATING AGENT SKILL MARKETPLACE SKELETON")
    print("==================================================")
    
    errors = []
    warnings = []

    manifest_path = os.path.join(root_dir, "marketplace.json")
    if not os.path.isfile(manifest_path):
        errors.append("marketplace.json is missing from root directory.")
        return errors, warnings

    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception as e:
        errors.append(f"marketplace.json is not valid JSON: {e}")
        return errors, warnings

    print("[OK] marketplace.json is valid JSON.")

    skills = manifest.get("skills", [])
    if not skills:
        errors.append("marketplace.json contains no skills.")
        return errors, warnings

    entrypoints = [s for s in skills if s.get("entrypoint") is True]
    if len(entrypoints) == 0:
        errors.append("No skill is designated as entrypoint (entrypoint: true required).")
    elif len(entrypoints) > 1:
        errors.append(f"Multiple skills designated as entrypoint: {[s.get('id') for s in entrypoints]}. Exactly ONE required.")
    else:
        print(f"[OK] Exactly one entrypoint designated: '{entrypoints[0].get('id')}'.")

    # Validate each skill
    for s in skills:
        skill_id = s.get("id")
        skill_path = os.path.join(root_dir, s.get("path", ""))
        
        print(f"\nValidating skill: '{skill_id}' at '{s.get('path')}'...")
        
        if not os.path.isdir(skill_path):
            errors.append(f"Skill directory does not exist: {skill_path}")
            continue

        skill_md_path = os.path.join(skill_path, "SKILL.md")
        if not os.path.isfile(skill_md_path):
            errors.append(f"SKILL.md missing in skill directory: {skill_path}")
            continue

        with open(skill_md_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check YAML frontmatter
        frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
        if not frontmatter_match:
            errors.append(f"SKILL.md in {skill_id} lacks valid YAML frontmatter delimiters (---).")
        else:
            frontmatter_text = frontmatter_match.group(1)
            body_text = frontmatter_match.group(2)
            
            if "name:" not in frontmatter_text:
                errors.append(f"SKILL.md frontmatter in {skill_id} missing 'name:' field.")
            if "description:" not in frontmatter_text:
                errors.append(f"SKILL.md frontmatter in {skill_id} missing 'description:' field.")
            if "license:" not in frontmatter_text:
                warnings.append(f"SKILL.md frontmatter in {skill_id} missing 'license:' field.")
            
            # Check required markdown sections
            required_sections = ["## When to use", "## Inputs", "## Procedure", "## Output"]
            for section in required_sections:
                if section.lower() not in body_text.lower():
                    errors.append(f"SKILL.md in {skill_id} missing required section: '{section}'.")

            print(f"  [OK] SKILL.md format and sections valid.")

        # Check scripts directory
        scripts_dir = os.path.join(skill_path, "scripts")
        if os.path.isdir(scripts_dir):
            for script_file in os.listdir(scripts_dir):
                if script_file.endswith(".py"):
                    script_path = os.path.join(scripts_dir, script_file)
                    try:
                        with open(script_path, "r", encoding="utf-8") as sf:
                            ast.parse(sf.read())
                        print(f"  [OK] Script '{script_file}' parsed successfully (valid Python syntax).")
                    except Exception as pe:
                        errors.append(f"Python syntax error in {script_path}: {pe}")

        # Check references directory
        refs_dir = os.path.join(skill_path, "references")
        if os.path.isdir(refs_dir):
            for ref_file in os.listdir(refs_dir):
                if ref_file.endswith(".json"):
                    ref_path = os.path.join(refs_dir, ref_file)
                    try:
                        with open(ref_path, "r", encoding="utf-8") as rf:
                            json.load(rf)
                        print(f"  [OK] Reference '{ref_file}' parsed successfully (valid JSON).")
                    except Exception as je:
                        errors.append(f"JSON syntax error in reference {ref_path}: {je}")

    print("\n==================================================")
    print("  VALIDATION SUMMARY")
    print("==================================================")
    if errors:
        print(f"FAILED with {len(errors)} error(s):")
        for e in errors:
            print(f"  [ERROR] {e}")
        return False
    else:
        print("ALL CHECKS PASSED: Marketplace skeleton is 100% compliant!")
        if warnings:
            print(f"Warnings ({len(warnings)}):")
            for w in warnings:
                print(f"  [WARN] {w}")
        return True


if __name__ == "__main__":
    workspace_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    success = validate_marketplace(workspace_dir)
    sys.exit(0 if success else 1)
