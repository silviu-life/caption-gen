#!/usr/bin/env python3
"""Validate all 93 Carl Jung TikTok narration scripts."""

import os
import re
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
EXCLUDED_FILES = {"validate_scripts.py", "MASTER_OUTLINE.md", "rename_scripts.py",
                  "gold-standard-short.txt", "gold-standard-medium.txt", "gold-standard-long.txt"}

# Clinical labels that should NOT appear
CLINICAL_LABELS = [
    r"\bnarcissist\b", r"\bnarcissism\b", r"\bnarcissistic\b",
    r"\bbpd\b", r"\bborderline\b", r"\bbipolar\b",
    r"\bsociopath\b", r"\bpsychopath\b", r"\bdiagnos",
    r"\bdisorder\b", r"\bmental illness\b",
]

# Personal/diary language that should NOT appear
PERSONAL_MARKERS = [
    r"\bmy therapist\b", r"\bmy ex\b", r"\bmy girlfriend\b", r"\bmy boyfriend\b",
    r"\bmy wife\b", r"\bmy husband\b", r"\bmy mother told me\b",
    r"\bI felt\b", r"\bI realized\b", r"\bI discovered\b", r"\bI noticed\b",
    r"\bI remember\b", r"\bI was\b",
]

# Stage directions that should NOT appear
STAGE_DIRECTIONS = [
    r"\[pause\]", r"\[beat\]", r"\[silence\]",
    r"^#", r"^Title:", r"^Theme:", r"^Script:",
]


def validate_script(filepath):
    """Validate a single script file. Returns list of issues."""
    issues = []
    text = filepath.read_text().strip()

    if not text:
        issues.append("EMPTY FILE")
        return issues

    words = text.split()
    word_count = len(words)

    # Word count check
    if word_count < 65:
        issues.append(f"TOO SHORT: {word_count} words (min 65)")
    if word_count > 240:
        issues.append(f"TOO LONG: {word_count} words (max 240)")

    # Check for exclamation marks
    if "!" in text:
        issues.append("Contains exclamation mark(s)")

    # Check for clinical labels
    text_lower = text.lower()
    for pattern in CLINICAL_LABELS:
        if re.search(pattern, text_lower):
            issues.append(f"CLINICAL LABEL found: {pattern}")

    # Check for personal diary language
    for pattern in PERSONAL_MARKERS:
        if re.search(pattern, text, re.IGNORECASE):
            issues.append(f"PERSONAL LANGUAGE found: {pattern}")

    # Check for stage directions / metadata
    for line in text.split("\n"):
        for pattern in STAGE_DIRECTIONS:
            if re.search(pattern, line.strip()):
                issues.append(f"STAGE DIRECTION/METADATA found: {pattern}")

    # Check Jung is mentioned
    if "jung" not in text_lower and "carl jung" not in text_lower:
        issues.append("NO JUNG REFERENCE found")

    return issues


def main():
    script_files = sorted([
        f for f in SCRIPTS_DIR.glob("*.txt")
        if f.name not in EXCLUDED_FILES
    ])

    print(f"\n{'='*60}")
    print(f"VALIDATING {len(script_files)} SCRIPTS")
    print(f"{'='*60}\n")

    total_issues = 0
    word_counts = []
    files_with_issues = []

    for f in script_files:
        issues = validate_script(f)
        text = f.read_text().strip()
        wc = len(text.split()) if text else 0
        word_counts.append(wc)

        if issues:
            total_issues += len(issues)
            files_with_issues.append((f.name, issues, wc))

    # Print results
    if files_with_issues:
        print("ISSUES FOUND:\n")
        for name, issues, wc in files_with_issues:
            print(f"  {name} ({wc}w):")
            for issue in issues:
                print(f"    - {issue}")
            print()
    else:
        print("  No issues found.\n")

    # Summary stats
    print(f"{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"  Total scripts: {len(script_files)}")
    print(f"  Scripts with issues: {len(files_with_issues)}")
    print(f"  Total issues: {total_issues}")

    if word_counts:
        short = sum(1 for w in word_counts if w <= 110)
        medium = sum(1 for w in word_counts if 110 < w <= 150)
        long = sum(1 for w in word_counts if w > 150)
        print(f"\n  Word count stats:")
        print(f"    Min: {min(word_counts)}")
        print(f"    Max: {max(word_counts)}")
        print(f"    Avg: {sum(word_counts) / len(word_counts):.0f}")
        print(f"\n  Length distribution:")
        print(f"    Short  (<=110w): {short}")
        print(f"    Medium (111-150w): {medium}")
        print(f"    Long   (>150w): {long}")

    print(f"\n  {'PASS' if total_issues == 0 else 'FAIL'}")
    print()

    return 0 if total_issues == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
