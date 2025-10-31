#!/usr/bin/env python3
"""
Analyze Claude Code conversation sessions for technical decision points using Gemini 2.5 Flash.

This script extracts technical decisions from conversation transcripts, identifying:
- What was decided
- Alternatives discussed
- Reasoning given
- Whether decisions were revised

Usage:
    python3 analyze_session_decisions.py <session_id>
    python3 analyze_session_decisions.py --project <project_name>
"""

import argparse
import sqlite3
import os
import sys
from pathlib import Path
from typing import Optional
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


ANALYSIS_PROMPT = """Review this Claude Code conversation transcript and identify moments where a technical decision was made.

For each decision, extract:
- What was decided
- What alternatives were discussed (if any)
- The reasoning given
- Whether it was later changed/revisited

Format your response as a structured report with:

1. **Executive Summary** (2-3 sentences about the project)

2. **Key Technical Decisions** (numbered list, each with):
   - What was decided
   - Alternatives discussed
   - Reasoning given
   - Changes/revisions (if any)

3. **Revised Decisions** (if any decisions were changed later):
   - Original decision
   - Revised to
   - Reason for change

Focus on architectural, technical, and implementation decisions. Skip minor formatting or style choices.

---

CONVERSATION TRANSCRIPT:

{transcript}
"""


def get_session_transcript(session_id: str, db_path: str) -> Optional[str]:
    """
    Get the pretty-printed transcript for a session.

    Args:
        session_id: Session UUID
        db_path: Path to SQLite database

    Returns:
        Transcript file path or None if not found
    """
    # Check if transcript already exists in ~/claude-conversations/
    conversations_dir = Path.home() / "claude-conversations"

    # Get project info from database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.project_id, p.project_name
        FROM sessions s
        JOIN projects p ON s.project_id = p.project_id
        WHERE s.session_id = ?
    """, (session_id,))

    result = cursor.fetchone()
    conn.close()

    if not result:
        return None

    project_id, project_name = result

    # Look for existing transcript
    project_dir = conversations_dir / project_id
    if project_dir.exists():
        transcript_file = project_dir / f"{session_id}.txt"
        if transcript_file.exists():
            return str(transcript_file)

    # If not found, generate it
    claude_projects = Path.home() / ".claude" / "projects"
    jsonl_file = claude_projects / project_id / f"{session_id}.jsonl"

    if not jsonl_file.exists():
        print(f"❌ JSONL file not found: {jsonl_file}", file=sys.stderr)
        return None

    # Create output directory
    project_dir.mkdir(parents=True, exist_ok=True)
    output_file = project_dir / f"{session_id}.txt"

    # Run pretty-print script
    print(f"📄 Generating transcript from {jsonl_file}...")
    pretty_print_script = Path.home() / ".claude" / "scripts" / "pretty-print-transcript.py"

    import subprocess
    try:
        with open(output_file, 'w') as f:
            subprocess.run([str(pretty_print_script), str(jsonl_file)], stdout=f, check=True)
        print(f"✅ Transcript saved to {output_file}")
        return str(output_file)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error generating transcript: {e}", file=sys.stderr)
        return None


def analyze_with_gemini(transcript_path: str, api_key: str) -> str:
    """
    Analyze transcript using Gemini 2.5 Flash.

    Args:
        transcript_path: Path to conversation transcript
        api_key: Google AI API key

    Returns:
        Analysis text
    """
    # Read transcript
    with open(transcript_path, 'r', encoding='utf-8') as f:
        transcript = f.read()

    # Configure Gemini
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash-exp')

    # Create prompt
    prompt = ANALYSIS_PROMPT.format(transcript=transcript)

    print(f"🤖 Analyzing with Gemini 2.5 Flash...")
    print(f"📊 Transcript size: {len(transcript):,} characters")

    # Generate analysis
    response = model.generate_content(prompt)

    return response.text


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Analyze Claude Code conversation for technical decision points'
    )
    parser.add_argument('session_id', nargs='?', help='Session UUID to analyze')
    parser.add_argument('--project', help='Analyze all sessions for a project')
    parser.add_argument(
        '--db',
        default=str(Path.home() / 'claude-conversations' / 'conversations.db'),
        help='Path to database (default: ~/claude-conversations/conversations.db)'
    )
    parser.add_argument('--output', help='Output file path (default: stdout)')

    args = parser.parse_args()

    # Get API key from environment
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        print("❌ Error: GOOGLE_API_KEY environment variable not set", file=sys.stderr)
        print("Get your API key from: https://aistudio.google.com/app/apikey", file=sys.stderr)
        sys.exit(1)

    # Validate arguments
    if not args.session_id and not args.project:
        parser.print_help()
        sys.exit(1)

    if args.project:
        print("❌ Error: Project-level analysis not yet implemented", file=sys.stderr)
        print("Please specify a single session_id for now.", file=sys.stderr)
        sys.exit(1)

    # Get transcript
    print(f"🔍 Looking up session {args.session_id}...")
    transcript_path = get_session_transcript(args.session_id, args.db)

    if not transcript_path:
        print(f"❌ Could not find or generate transcript for session {args.session_id}", file=sys.stderr)
        sys.exit(1)

    # Analyze
    try:
        analysis = analyze_with_gemini(transcript_path, api_key)

        # Output
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(analysis)
            print(f"\n✅ Analysis saved to {output_path}")
        else:
            print("\n" + "="*100)
            print("TECHNICAL DECISION ANALYSIS")
            print("="*100 + "\n")
            print(analysis)

    except Exception as e:
        print(f"❌ Error during analysis: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
