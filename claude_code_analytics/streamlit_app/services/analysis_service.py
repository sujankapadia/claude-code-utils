"""Analysis service layer for running LLM-powered analysis."""

import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional
import yaml
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from claude_code_analytics.streamlit_app.models import AnalysisType, AnalysisResult, AnalysisTypeMetadata
from claude_code_analytics.streamlit_app.services.llm_providers import LLMProvider, create_provider


class AnalysisService:
    """Service for running conversation analysis."""

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        db_path: Optional[str] = None,
        default_model: Optional[str] = None,
    ):
        """
        Initialize analysis service.

        Args:
            provider: LLM provider instance. If None, creates provider from environment.
            db_path: Path to database. Defaults to ~/claude-conversations/conversations.db
            default_model: Default model to use for analysis
        """
        # Initialize provider
        if provider is None:
            self.provider = create_provider(default_model=default_model)
        else:
            self.provider = provider

        # Set database path
        if db_path is None:
            db_path = str(Path.home() / "claude-conversations" / "conversations.db")
        self.db_path = db_path

        # Load prompt metadata
        self.metadata, self.jinja_env = self._load_prompts()

    @property
    def api_key(self) -> Optional[str]:
        """Legacy property for backwards compatibility."""
        # Check if provider has API key
        return getattr(self.provider, 'api_key', None)

    def _load_prompts(self) -> tuple[Dict[str, AnalysisTypeMetadata], Environment]:
        """
        Load analysis prompts from Jinja2 template files.

        Returns:
            Tuple of (metadata dict, jinja2 environment)
        """
        # Get prompts directory (relative to project root)
        project_root = Path(__file__).parent.parent.parent
        prompts_dir = project_root / "prompts"

        # Load metadata
        metadata_file = prompts_dir / "metadata.yaml"
        with open(metadata_file, "r") as f:
            raw_metadata = yaml.safe_load(f)

        # Convert to Pydantic models
        metadata = {
            key: AnalysisTypeMetadata(**value) for key, value in raw_metadata.items()
        }

        # Create Jinja2 environment
        env = Environment(loader=FileSystemLoader(str(prompts_dir)))

        return metadata, env

    def get_available_analysis_types(self) -> Dict[str, AnalysisTypeMetadata]:
        """Get all available analysis types and their metadata."""
        return self.metadata

    def get_transcript_path(self, session_id: str) -> Optional[str]:
        """
        Get the transcript path for a session, generating it if needed.

        Args:
            session_id: Session UUID

        Returns:
            Path to transcript file, or None if not found
        """
        import sqlite3

        conversations_dir = Path.home() / "claude-conversations"

        # Get project info from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT p.project_id, p.project_name
            FROM sessions s
            JOIN projects p ON s.project_id = p.project_id
            WHERE s.session_id = ?
        """,
            (session_id,),
        )

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
            return None

        # Create output directory
        project_dir.mkdir(parents=True, exist_ok=True)
        output_file = project_dir / f"{session_id}.txt"

        # Run pretty-print script
        pretty_print_script = (
            Path(__file__).parent.parent.parent
            / "scripts"
            / "pretty-print-transcript.py"
        )

        try:
            with open(output_file, "w") as f:
                subprocess.run(
                    [sys.executable, str(pretty_print_script), str(jsonl_file)],
                    stdout=f,
                    check=True,
                    stderr=subprocess.PIPE,
                )
            return str(output_file)
        except subprocess.CalledProcessError:
            return None

    def analyze_session(
        self,
        session_id: str,
        analysis_type: AnalysisType,
        custom_prompt: Optional[str] = None,
        model: Optional[str] = None,
    ) -> AnalysisResult:
        """
        Analyze a session with the specified analysis type.

        Args:
            session_id: Session UUID
            analysis_type: Type of analysis to perform
            custom_prompt: Custom prompt text (required if analysis_type is CUSTOM)
            model: Model to use (provider-specific). If None, uses provider's default.

        Returns:
            AnalysisResult with the analysis output

        Raises:
            ValueError: If analysis type not found or custom_prompt missing
            FileNotFoundError: If transcript not found
        """
        # Get transcript
        transcript_path = self.get_transcript_path(session_id)
        if not transcript_path:
            raise FileNotFoundError(
                f"Could not find or generate transcript for session {session_id}"
            )

        # Read transcript
        with open(transcript_path, "r", encoding="utf-8") as f:
            transcript = f.read()

        # Build prompt based on analysis type
        if analysis_type == AnalysisType.CUSTOM:
            if not custom_prompt:
                raise ValueError("custom_prompt is required for CUSTOM analysis type")
            # Automatically append the transcript
            prompt = f"{custom_prompt}\n\n---\n\nCONVERSATION TRANSCRIPT:\n\n{transcript}"
        else:
            # Get metadata for this analysis type
            metadata = self.metadata.get(analysis_type.value)
            if not metadata:
                raise ValueError(f"Unknown analysis type: {analysis_type}")

            # Load and render Jinja2 template
            try:
                template = self.jinja_env.get_template(metadata.file)
                prompt = template.render(transcript=transcript)
            except TemplateNotFound:
                raise ValueError(f"Template file not found: {metadata.file}")

        # Generate analysis using provider
        llm_response = self.provider.generate(prompt, model=model)

        return AnalysisResult(
            session_id=session_id,
            analysis_type=analysis_type,
            result_text=llm_response.text,
            input_tokens=llm_response.input_tokens,
            output_tokens=llm_response.output_tokens,
            model_name=llm_response.model_name,
        )
