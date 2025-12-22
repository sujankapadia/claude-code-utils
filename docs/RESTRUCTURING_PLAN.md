# Python Package Restructuring Plan

**Status:** 🟡 Planning Complete - Ready to Execute
**Date:** December 22, 2024
**Goal:** Convert script collection → installable Python package for Homebrew + manual installation

## Why We're Doing This

**Current State:**
- Collection of Python scripts (`scripts/*.py`)
- No proper package structure
- Can't be installed via pip or Homebrew
- Users must run scripts directly: `python scripts/import_conversations.py`

**Blocking Issue:**
```
ERROR: Directory is not installable. Neither 'setup.py' nor 'pyproject.toml' found.
```

**Target State:**
- Proper Python package with `pyproject.toml`
- Installable via pip and Homebrew
- Clean CLI commands: `claude-code-import`, `claude-code-analytics`
- Two installation methods: Homebrew (automated) and manual (./install.sh)

## Current Structure

```
claude-code-utils/
├── config.py                      # Configuration management
├── streamlit_app/                 # Dashboard application
│   ├── app.py
│   ├── pages/
│   └── ...
├── scripts/                       # CLI scripts
│   ├── import_conversations.py
│   ├── search_fts.py
│   ├── analyze_session.py
│   ├── create_database.py
│   └── create_fts_index.py
├── hooks/                         # Shell hooks for Claude Code
│   ├── export-conversation.sh
│   └── pretty-print-transcript.py
├── prompts/                       # AI prompt templates
├── .env.example                   # Config template
├── install.sh                     # Manual installation script
├── pyproject.toml                 # ✅ Created (needs testing)
├── README.md
└── LICENSE
```

## Target Structure

```
claude-code-utils/
├── claude_code_analytics/         # ← NEW: Main package directory
│   ├── __init__.py                # ← NEW: Package marker
│   ├── cli.py                     # ← NEW: CLI entry points
│   ├── config.py                  # MOVED from root
│   ├── streamlit_app/             # MOVED from root
│   │   ├── __init__.py            # ← NEW
│   │   ├── app.py
│   │   ├── pages/
│   │   └── ...
│   ├── scripts/                   # MOVED from root
│   │   ├── __init__.py            # ← NEW
│   │   ├── import_conversations.py
│   │   ├── search_fts.py
│   │   ├── analyze_session.py
│   │   ├── create_database.py
│   │   └── create_fts_index.py
│   ├── prompts/                   # MOVED from root
│   └── .env.example               # MOVED from root
├── hooks/                         # STAYS at root (not part of package)
│   ├── export-conversation.sh
│   └── pretty-print-transcript.py
├── install.sh                     # UPDATED to include pip install
├── pyproject.toml                 # ✅ Already created
├── README.md                      # UPDATED with new install instructions
└── LICENSE
```

## Implementation Steps

### Phase 1: Create Package Structure

#### Step 1.1: Create Package Directory
```bash
mkdir -p claude_code_analytics
```

#### Step 1.2: Create __init__.py Files
```python
# claude_code_analytics/__init__.py
"""Analytics platform for Claude Code conversations."""
__version__ = "1.0.0"
```

```python
# claude_code_analytics/streamlit_app/__init__.py
"""Streamlit dashboard application."""
```

```python
# claude_code_analytics/scripts/__init__.py
"""CLI utility scripts."""
```

#### Step 1.3: Move Files into Package
```bash
# Move core files
mv config.py claude_code_analytics/
mv .env.example claude_code_analytics/

# Move directories
mv streamlit_app claude_code_analytics/
mv scripts claude_code_analytics/
mv prompts claude_code_analytics/

# hooks/ stays at root - not part of Python package
```

### Phase 2: Create CLI Entry Points

#### Step 2.1: Create cli.py Module

Location: `claude_code_analytics/cli.py`

```python
"""CLI entry points for claude-code-analytics."""
import sys


def dashboard():
    """Launch the Streamlit dashboard."""
    import subprocess
    from pathlib import Path
    from claude_code_analytics import streamlit_app

    # Find the app.py file within the package
    app_path = Path(streamlit_app.__file__).parent / "app.py"

    # Run streamlit with all command-line args passed through
    result = subprocess.run(
        ["streamlit", "run", str(app_path)] + sys.argv[1:],
        check=False
    )
    return result.returncode


def import_conversations():
    """Import conversations from Claude Code."""
    from claude_code_analytics.scripts.import_conversations import main
    return main() or 0


def search():
    """Search conversations."""
    from claude_code_analytics.scripts.search_fts import main
    return main() or 0


def analyze():
    """Analyze session metrics."""
    from claude_code_analytics.scripts.analyze_session import main
    return main() or 0
```

**How it works:**
- Each function is a thin wrapper around existing script logic
- `pyproject.toml` maps commands to these functions
- pip creates executable scripts automatically

#### Step 2.2: Update Existing Scripts

Scripts need to:
1. Keep their `if __name__ == "__main__"` blocks (for direct running)
2. Extract main logic into a `main()` function
3. Update imports to use package-qualified paths

**Example: `scripts/import_conversations.py`**

Before:
```python
from config import get_config  # Top-level import

# ... script logic ...

if __name__ == "__main__":
    # ... inline code ...
```

After:
```python
from claude_code_analytics.config import get_config  # Package-qualified import


def main():
    """Main import logic."""
    # ... all the script logic ...
    return 0  # Exit code


if __name__ == "__main__":
    import sys
    sys.exit(main())
```

### Phase 3: Update Imports

All files that import from other modules need updating:

#### Files to Update:
- `claude_code_analytics/streamlit_app/app.py`
- `claude_code_analytics/streamlit_app/pages/*.py`
- `claude_code_analytics/scripts/*.py`

#### Import Changes:

**Before (won't work):**
```python
from config import get_config
from scripts.create_database import create_database
```

**After (package-qualified):**
```python
from claude_code_analytics.config import get_config
from claude_code_analytics.scripts.create_database import create_database
```

### Phase 4: Update install.sh

Location: `install.sh` (at root)

Add after line 62 (after config setup):

```bash
# Install Python package
echo "📦 Installing Python package..."
if command -v pip3 &> /dev/null; then
    pip3 install -e "$SCRIPT_DIR"
    echo -e "${GREEN}✓ Installed claude-code-analytics package${NC}"
    echo -e "${GREEN}✓ All dependencies installed automatically${NC}"
else
    echo -e "${RED}Error: pip3 is required but not installed.${NC}"
    exit 1
fi
```

Update "Next steps" section (lines 145-163):

```bash
echo "Next steps:"
echo ""
echo "Quick start:"
echo "  1. Import conversations: claude-code-import"
echo "  2. Launch dashboard: claude-code-analytics"
echo ""
echo "CLI Commands available:"
echo "  claude-code-analytics    # Launch dashboard"
echo "  claude-code-import       # Import conversations"
echo "  claude-code-search       # Search conversations"
echo "  claude-code-analyze      # Analyze sessions"
echo ""
echo "For AI analysis features:"
echo "  Edit $CONFIG_FILE"
echo "  Set OPENROUTER_API_KEY or GOOGLE_API_KEY"
echo "  (Get keys from https://openrouter.ai/keys or https://aistudio.google.com/app/apikey)"
echo ""
echo "To test the export hook:"
echo "  Start a new Claude Code session and exit it."
echo "  Check $CONVERSATIONS_DIR for exported conversation."
```

### Phase 5: Update Homebrew Formula

Location: `Formula/claude-code-analytics.rb`

#### Step 5.1: Generate Python Resources

After package structure is complete and tested:

```bash
brew update-python-resources Formula/claude-code-analytics.rb
```

This auto-generates resource blocks for all dependencies:
```ruby
resource "streamlit" do
  url "https://files.pythonhosted.org/packages/.../streamlit-1.29.0.tar.gz"
  sha256 "abc123..."
end

resource "pandas" do
  url "https://files.pythonhosted.org/packages/.../pandas-2.1.0.tar.gz"
  sha256 "def456..."
end

# ... etc for all dependencies
```

#### Step 5.2: Update Install Method

Change from manual wrapper scripts to proper virtualenv:

**Before:**
```ruby
def install
  libexec.install Dir["*"]

  # Manual wrapper scripts
  (bin/"claude-code-analytics").write <<~EOS
    #!/bin/bash
    cd "#{libexec}" && python3 -m streamlit run streamlit_app/app.py "$@"
  EOS
  # ... more manual wrappers ...
end
```

**After:**
```ruby
def install
  virtualenv_install_with_resources

  # CLI commands are created automatically from pyproject.toml [project.scripts]
  # No manual wrappers needed!
end
```

#### Step 5.3: Update for Release

Before v1.0.0 tag:
- Change URL from branch to tag: `v1.0.0.tar.gz`
- Generate new SHA256 for tag (not branch)
- Remove "dev" version suffix
- Keep post_install for hook setup (unchanged)

### Phase 6: Testing

#### Test 1: Local Package Installation
```bash
# From repo root
pip install -e .

# Verify installation
which claude-code-analytics
which claude-code-import

# Test commands
claude-code-analytics --help
claude-code-import --help
claude-code-search --help
claude-code-analyze --help
```

#### Test 2: Manual install.sh
```bash
# Uninstall first
pip uninstall claude-code-analytics

# Run install script
./install.sh

# Verify CLI commands work
claude-code-import
claude-code-analytics
```

#### Test 3: Homebrew Formula
```bash
# Generate resources
brew update-python-resources Formula/claude-code-analytics.rb

# Copy to tap
cp Formula/claude-code-analytics.rb /opt/homebrew/Library/Taps/sujankapadia/homebrew-claude-code-analytics/Formula/

# Install
export HOMEBREW_NO_INSTALL_FROM_API=1
brew install --build-from-source claude-code-analytics

# Verify
brew test claude-code-analytics
brew audit --strict claude-code-analytics
```

#### Test 4: Full Workflow
```bash
# 1. Import conversations
claude-code-import

# 2. Search
claude-code-search "test query"

# 3. Launch dashboard
claude-code-analytics

# 4. Verify SessionEnd hook works
# Start and exit a Claude Code session
# Check ~/claude-conversations/ for new file
```

### Phase 7: Documentation Updates

#### Update README.md

Replace installation section with:

```markdown
## Installation

### Option 1: Homebrew (Recommended for macOS)

```bash
brew tap sujankapadia/claude-code-analytics
brew install claude-code-analytics
```

Everything is configured automatically!

### Option 2: Manual Installation

```bash
git clone https://github.com/sujankapadia/claude-code-utils.git
cd claude-code-utils
./install.sh
```

This will:
- Install the Python package and all dependencies
- Set up Claude Code hooks
- Create configuration files

### Option 3: Development Installation

```bash
git clone https://github.com/sujankapadia/claude-code-utils.git
cd claude-code-utils
pip install -e ".[dev]"
./install.sh  # For hook setup
```

## Usage

### CLI Commands

```bash
claude-code-analytics    # Launch dashboard
claude-code-import       # Import conversations
claude-code-search       # Search conversations
claude-code-analyze      # Analyze sessions
```

### Configuration

Edit `~/.config/claude-code-analytics/.env` to customize settings.
```

## Files Checklist

### Files to Create
- [ ] `claude_code_analytics/__init__.py`
- [ ] `claude_code_analytics/cli.py`
- [ ] `claude_code_analytics/streamlit_app/__init__.py`
- [ ] `claude_code_analytics/scripts/__init__.py`

### Files to Move
- [ ] `config.py` → `claude_code_analytics/config.py`
- [ ] `streamlit_app/` → `claude_code_analytics/streamlit_app/`
- [ ] `scripts/` → `claude_code_analytics/scripts/`
- [ ] `prompts/` → `claude_code_analytics/prompts/`
- [ ] `.env.example` → `claude_code_analytics/.env.example`

### Files to Update
- [ ] `claude_code_analytics/scripts/import_conversations.py` (imports + main())
- [ ] `claude_code_analytics/scripts/search_fts.py` (imports + main())
- [ ] `claude_code_analytics/scripts/analyze_session.py` (imports + main())
- [ ] `claude_code_analytics/scripts/create_database.py` (imports + main())
- [ ] `claude_code_analytics/scripts/create_fts_index.py` (imports + main())
- [ ] `claude_code_analytics/streamlit_app/app.py` (imports)
- [ ] `claude_code_analytics/streamlit_app/pages/*.py` (imports)
- [ ] `install.sh` (add pip install, update instructions)
- [ ] `README.md` (installation instructions)
- [ ] `Formula/claude-code-analytics.rb` (after testing)

### Files to Keep Unchanged
- [x] `hooks/export-conversation.sh` (stays at root)
- [x] `hooks/pretty-print-transcript.py` (stays at root)
- [x] `pyproject.toml` (already created, ready to use)
- [x] `LICENSE`
- [x] All documentation in `docs/`

## Risk Assessment

### Low Risk (Safe Changes)
- Creating new files (`__init__.py`, `cli.py`)
- Moving files (can revert easily)
- `pyproject.toml` already tested structurally

### Medium Risk (Need Careful Testing)
- Import statement updates (many files affected)
- Script main() extraction (logic changes)
- install.sh updates (affects user experience)

### High Risk (Test Thoroughly)
- Homebrew formula changes (must work for clean install)
- Full integration testing (all components together)

### Mitigation
- Work in feature branch (already on `feature/homebrew-packaging`)
- Test each phase before proceeding to next
- Keep install.sh backup
- Document any issues encountered

## Success Criteria

### Phase Complete When:
- [x] Phase 1: Package structure created, files moved
- [ ] Phase 2: cli.py created and tested
- [ ] Phase 3: All imports updated, no import errors
- [ ] Phase 4: install.sh updated and tested
- [ ] Phase 5: Homebrew formula working
- [ ] Phase 6: All tests pass
- [ ] Phase 7: Documentation updated

### Ready for v1.0.0 When:
- [ ] `pip install -e .` works
- [ ] `./install.sh` completes successfully
- [ ] All CLI commands work
- [ ] `brew install` completes successfully
- [ ] All 6 Homebrew tests pass
- [ ] `brew audit --strict` passes
- [ ] SessionEnd hook exports conversations
- [ ] Import → Search → Dashboard workflow works
- [ ] Documentation is complete and accurate

## Rollback Plan

If issues arise:

```bash
# Revert to previous commit
git checkout HEAD~1

# Or revert specific files
git checkout HEAD -- config.py
git checkout HEAD -- scripts/
git checkout HEAD -- streamlit_app/

# Or start over from main
git checkout main
git branch -D feature/homebrew-packaging
git checkout -b feature/homebrew-packaging
```

## Time Estimates

| Phase | Description | Estimated Time |
|-------|-------------|----------------|
| Phase 1 | Create package structure | 30 minutes |
| Phase 2 | Create CLI entry points | 1 hour |
| Phase 3 | Update imports | 1-2 hours |
| Phase 4 | Update install.sh | 30 minutes |
| Phase 5 | Update Homebrew formula | 1 hour |
| Phase 6 | Testing all components | 2-3 hours |
| Phase 7 | Documentation updates | 1 hour |
| **Total** | | **7-10 hours** |

## Questions to Resolve

- [x] Where does pip install to? (Answer: Active Python - pyenv in this case)
- [x] Do we keep hooks/ separate? (Answer: Yes, not part of package)
- [x] Does install.sh install dependencies? (Answer: Yes, via pip install -e .)
- [x] How do CLI commands work? (Answer: pyproject.toml [project.scripts])
- [ ] Any other scripts that need updating we haven't identified?

## Next Actions

1. Review this plan with user
2. Get approval to proceed
3. Execute Phase 1
4. Test and validate before moving to Phase 2
5. Proceed systematically through all phases

## Notes

- Working in `feature/homebrew-packaging` branch
- Current git status: Clean (all previous work committed)
- pyproject.toml already created and ready
- Homebrew formula already created (needs resource generation)
- Documentation already comprehensive
- This is the final major task before v1.0.0 release
