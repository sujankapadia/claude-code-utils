"""Analysis runner page."""

import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from streamlit_app.services import DatabaseService, AnalysisService, OpenRouterProvider
from streamlit_app.models import AnalysisType

# Initialize services
if "db_service" not in st.session_state:
    st.session_state.db_service = DatabaseService()

if "analysis_service" not in st.session_state:
    st.session_state.analysis_service = AnalysisService()

db_service = st.session_state.db_service
analysis_service = st.session_state.analysis_service

st.title("🔬 Run Analysis")

st.markdown("""
Perform AI-powered analysis on your conversation sessions using state-of-the-art LLMs.
""")

# Check for API key
api_key_configured = analysis_service.api_key is not None

if not api_key_configured:
    st.error("⚠️ LLM API key not configured!")
    st.markdown("""
    To use the analysis feature, you need to set an API key:

    **Option 1: OpenRouter (Recommended)** - Access 300+ models
    1. Get an API key from [OpenRouter](https://openrouter.ai/keys)
    2. Set the `OPENROUTER_API_KEY` environment variable
    3. Restart the Streamlit app

    ```bash
    export OPENROUTER_API_KEY="sk-or-your-key-here"
    streamlit run streamlit_app/app.py
    ```

    **Option 2: Google Gemini (Direct)**
    1. Get an API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
    2. Set the `GOOGLE_API_KEY` environment variable
    3. Restart the Streamlit app

    ```bash
    export GOOGLE_API_KEY="your-api-key-here"
    streamlit run streamlit_app/app.py
    ```
    """)
    st.stop()

# Session selector
st.subheader("Select Session")

try:
    # Get recent sessions
    sessions = db_service.get_session_summaries(limit=50)

    if not sessions:
        st.warning("No sessions found. Import conversations first.")
        st.stop()

    # Create session options
    session_options = {
        f"{s.project_name} | {s.session_id[:8]}... | {s.start_time}": s.session_id
        for s in sessions
    }

    # Pre-select if coming from browser
    default_index = 0
    if "selected_session_id" in st.session_state:
        selected_id = st.session_state.selected_session_id
        matching_keys = [k for k, v in session_options.items() if v == selected_id]
        if matching_keys:
            default_index = list(session_options.keys()).index(matching_keys[0])

    selected_session_display = st.selectbox(
        "Choose a session:",
        options=list(session_options.keys()),
        index=default_index,
    )

    selected_session_id = session_options[selected_session_display]

    # Display session info
    session = next(s for s in sessions if s.session_id == selected_session_id)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Messages", session.message_count)
    col2.metric("Tool Uses", session.tool_use_count)
    col3.metric("User Msgs", session.user_message_count)
    col4.metric("Assistant Msgs", session.assistant_message_count)

    st.divider()

    # Analysis type selector
    st.subheader("Select Analysis Type")

    available_types = analysis_service.get_available_analysis_types()

    # Create radio buttons for analysis types
    analysis_type_options = {
        f"**{meta.name}**: {meta.description}": key
        for key, meta in available_types.items()
    }

    selected_display = st.radio(
        "Choose analysis type:",
        options=list(analysis_type_options.keys()),
        index=0,
    )

    selected_analysis_type = AnalysisType(analysis_type_options[selected_display])

    # Show custom prompt text area if CUSTOM is selected
    custom_prompt = None
    if selected_analysis_type == AnalysisType.CUSTOM:
        st.markdown("### Enter Your Analysis Prompt")
        st.markdown("_The conversation transcript will be automatically appended to your prompt._")
        custom_prompt = st.text_area(
            "Prompt:",
            height=200,
            placeholder="Example: Analyze this conversation and identify the main topics discussed, key insights shared, and any action items mentioned.",
            help="Enter your analysis instructions. The transcript will be automatically added after your prompt."
        )

    st.divider()

    # Model selector (only show if using OpenRouter)
    selected_model = None
    if isinstance(analysis_service.provider, OpenRouterProvider):
        st.subheader("Model Selection")

        # Quick select models
        model_options = {label: model_id for label, model_id in OpenRouterProvider.QUICK_SELECT_MODELS}

        selected_model_label = st.selectbox(
            "Choose model:",
            options=list(model_options.keys()),
            index=4,  # Default to DeepSeek V3.2
            help="Quick select from curated list of newest premium models. Default uses env var OPENROUTER_MODEL or DeepSeek V3.2."
        )

        selected_model = model_options[selected_model_label]

        # Advanced: All models expander
        with st.expander("🔍 Advanced: Browse All Models"):
            st.markdown("Load the full catalog of 300+ models from OpenRouter:")

            if st.button("Load All Models", help="Fetches the complete list from OpenRouter API"):
                with st.spinner("Fetching models from OpenRouter..."):
                    try:
                        all_models = OpenRouterProvider.fetch_all_models()

                        # Filter for text generation models
                        text_models = [
                            m for m in all_models
                            if 'text' in m['architecture']['output_modalities']
                            and m['pricing']['prompt'] != '0'
                        ]

                        # Sort by newest first
                        text_models.sort(key=lambda m: m['created'], reverse=True)

                        st.success(f"✅ Loaded {len(text_models)} models!")

                        # Create searchable dataframe
                        import pandas as pd

                        df_data = []
                        for m in text_models[:100]:  # Limit to 100 for performance
                            prompt_price = float(m['pricing']['prompt']) * 1_000_000
                            completion_price = float(m['pricing']['completion']) * 1_000_000
                            df_data.append({
                                'Model ID': m['id'],
                                'Name': m['name'],
                                'Input $/1M': f"${prompt_price:.2f}",
                                'Output $/1M': f"${completion_price:.2f}",
                                'Context': f"{m['context_length']:,}",
                            })

                        df = pd.DataFrame(df_data)

                        st.markdown("**Top 100 newest models:**")
                        st.dataframe(df, use_container_width=True, height=400)

                        st.info("💡 To use a model from this list, copy the Model ID and set it as OPENROUTER_MODEL environment variable, or select from quick list above.")

                    except Exception as e:
                        st.error(f"Failed to fetch models: {e}")

        st.divider()

    # Run analysis
    st.subheader("Run Analysis")

    col1, col2 = st.columns([1, 3])

    with col1:
        run_button = st.button("🚀 Run Analysis", type="primary", use_container_width=True)

    with col2:
        save_to_file = st.checkbox("Save result to file", value=False)

    if run_button:
        # Validate custom prompt if CUSTOM type is selected
        if selected_analysis_type == AnalysisType.CUSTOM:
            if not custom_prompt or not custom_prompt.strip():
                st.error("❌ Please enter a custom prompt for analysis.")
                st.stop()

        with st.spinner("Analyzing conversation... This may take a minute."):
            try:
                # Run analysis
                result = analysis_service.analyze_session(
                    selected_session_id,
                    selected_analysis_type,
                    custom_prompt=custom_prompt,
                    model=selected_model,
                )

                st.success("✅ Analysis complete!")

                # Display token usage
                if result.input_tokens or result.output_tokens:
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Input Tokens", f"{result.input_tokens or 0:,}")
                    col2.metric("Output Tokens", f"{result.output_tokens or 0:,}")
                    col3.metric("Model", result.model_name or "N/A")

                st.divider()

                # Display result
                st.markdown("### Analysis Result")
                st.markdown(result.result_text)

                # Save to file if requested
                if save_to_file:
                    output_dir = Path.home() / "claude-conversations" / "analyses"
                    output_dir.mkdir(exist_ok=True)

                    filename = f"{selected_session_id}_{selected_analysis_type.value}.md"
                    output_path = output_dir / filename

                    with open(output_path, "w") as f:
                        f.write(f"# {available_types[selected_analysis_type.value].name}\n\n")
                        f.write(f"**Session:** {selected_session_id}\n")
                        f.write(f"**Date:** {result.created_at}\n\n")
                        f.write("---\n\n")
                        f.write(result.result_text)

                    st.success(f"💾 Saved to: `{output_path}`")

                # Download button
                st.download_button(
                    label="📥 Download as Markdown",
                    data=result.result_text,
                    file_name=f"{selected_session_id}_{selected_analysis_type.value}.md",
                    mime="text/markdown",
                )

            except Exception as e:
                st.error(f"❌ Error running analysis: {e}")
                import traceback
                with st.expander("Error details"):
                    st.code(traceback.format_exc())

except Exception as e:
    st.error(f"Error loading sessions: {e}")
    import traceback
    with st.expander("Error details"):
        st.code(traceback.format_exc())
