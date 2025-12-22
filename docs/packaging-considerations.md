# Packaging Considerations & Lessons Learned

## Key Insights from Homebrew Documentation Research

### 1. What We're Doing RIGHT ✅

**Our tool is well-suited for Homebrew:**
- ✅ Open source with MIT license
- ✅ Has a stable GitHub repository
- ✅ Command-line tool (not a GUI app)
- ✅ Doesn't self-update (good for Homebrew integration)
- ✅ Uses versioned, checksummed sources
- ✅ Builds from source (Python + dependencies)

**Our code already follows best practices:**
- ✅ HTTPS homepage (GitHub)
- ✅ All Python dependencies will be declared as `resource` blocks
- ✅ Using virtualenv (as required for Python formulas)
- ✅ Cross-platform Python code

### 2. Critical Pitfalls to Avoid ⚠️

**Formula Creation:**
- ❌ **Don't** use `--version` or `--help` as the only test
- ❌ **Don't** forget SHA256 checksums for resources
- ❌ **Don't** modify user shell profiles (no .bashrc edits)
- ❌ **Don't** bundle/vendor dependencies manually
- ❌ **Don't** use unversioned Git branches as sources

**Version Management:**
- ❌ **Don't** manually edit formula for updates - use `brew bump-formula-pr`
- ❌ **Don't** forget to increment `revision` for security patches
- ❌ **Don't** use unstable/development versions

**Testing:**
- ❌ **Don't** submit without running `brew audit --strict --online`
- ❌ **Don't** skip testing actual functionality
- ❌ **Don't** test only on your machine (use clean Docker container)

### 3. Things We Need to Add

#### Versioning Strategy

**Current state:** No version tags yet

**What we need:**
```bash
# Semantic versioning: MAJOR.MINOR.PATCH
v1.0.0  # First Homebrew release
v1.0.1  # Bug fixes
v1.1.0  # New features (backward compatible)
v2.0.0  # Breaking changes
```

**Process for updates:**
1. Tag release: `git tag -a v1.0.0 -m "Release 1.0.0"`
2. Update formula URL to new tag
3. Generate new SHA256 checksum
4. Use `brew bump-formula-pr` to submit update

#### Meaningful Tests

**Current test in plan:**
```ruby
test do
  system bin/"claude-code-import", "--help"  # ❌ TOO SUPERFICIAL
end
```

**Better test:**
```ruby
test do
  # Create a minimal test conversation
  (testpath/"test-project").mkpath
  (testpath/"test-project/session.jsonl").write <<~EOS
    {"type":"conversation_metadata","session_id":"test-123"}
    {"type":"message","message":{"role":"user","content":"test message"}}
  EOS

  # Set config to use test directory
  ENV["CLAUDE_CONVERSATIONS_DIR"] = testpath.to_s
  ENV["CLAUDE_CODE_PROJECTS_DIR"] = testpath.to_s

  # Test import functionality
  system bin/"claude-code-import"

  # Verify database was created
  assert_predicate testpath/"conversations.db", :exist?

  # Verify data was imported
  output = shell_output("sqlite3 #{testpath}/conversations.db 'SELECT COUNT(*) FROM messages'")
  assert_match "1", output
end
```

#### CLI Entry Points

**Current state:** Wrapper bash scripts

**For proper Python packaging (future pip install):**

We'll need a `pyproject.toml`:
```toml
[project]
name = "claude-code-analytics"
version = "1.0.0"
description = "Analytics platform for Claude Code conversations"
readme = "README.md"
license = {text = "MIT"}
authors = [{name = "Your Name", email = "your@email.com"}]

dependencies = [
    "streamlit>=1.28.0",
    "pandas>=2.0.0",
    "altair>=5.0.0",
    "google-generativeai>=0.3.0",
    "openai>=1.0.0",
    "jinja2>=3.0.0",
    "pyyaml>=6.0.0",
    "python-dotenv>=1.0.0",
]

[project.scripts]
claude-code-analytics = "claude_code_analytics.cli:dashboard"
claude-code-import = "claude_code_analytics.cli:import_cmd"
claude-code-search = "claude_code_analytics.cli:search_cmd"
claude-code-analyze = "claude_code_analytics.cli:analyze_cmd"

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"
```

**This would enable:**
```bash
pip install claude-code-analytics
# or
pipx install claude-code-analytics
```

### 4. Homebrew Bottles (Pre-compiled Binaries)

**What are they?**
- Pre-built binaries (gzipped tarballs) that avoid compilation
- Speed up installation significantly
- Generated automatically for homebrew/core formulas

**Do we need them?**
- ❌ Not required for personal taps
- ✅ Nice to have (faster user installs)
- 🔄 Auto-generated if we submit to homebrew/core

**For our tap:**
- Start without bottles (users build from source)
- Add later if installation is slow
- Use GitHub Actions to auto-build bottles per-release (advanced)

### 5. Maintenance & Updates

**Version Update Process:**
```bash
# 1. Make changes and tag new version
git tag -a v1.0.1 -m "Bug fixes"
git push origin v1.0.1

# 2. Generate new checksum
curl -L https://github.com/USER/REPO/archive/refs/tags/v1.0.1.tar.gz | shasum -a 256

# 3. Update formula (automated)
brew bump-formula-pr --url=<NEW_URL> --sha256=<NEW_SHA> claude-code-analytics

# 4. Users update with
brew upgrade claude-code-analytics
```

**Security Patches (no version change):**
```bash
# Increment revision in formula
revision 1

# Update dependencies if needed
brew bump-revision claude-code-analytics
```

### 6. Unacceptable in Homebrew (We're Safe)

**Things Homebrew rejects:**
- ❌ GUI apps (should be casks) - **We're CLI ✅**
- ❌ Self-updating software - **We don't self-update ✅**
- ❌ Binary-only proprietary software - **We're open source ✅**
- ❌ Unversioned sources - **We'll use tagged releases ✅**
- ❌ Bundled/vendored dependencies - **Using `resource` blocks ✅**

### 7. Dependencies on User Data

**Our situation:**
- Tool requires Claude Code conversation exports
- Data lives in `~/.claude/projects/` (user's home directory)
- Config in `~/.config/claude-code-analytics/`

**Homebrew compatibility:**
- ✅ Accessing user home directory is fine
- ✅ Reading from `~/.claude/` is acceptable
- ✅ Writing to `~/.config/` follows XDG standard
- ✅ Caveats section explains data requirements

**What we document in caveats:**
- Where conversation data should be located
- How to configure custom paths
- Requirement for Claude Code (optional runtime dependency)

## Higher-Level Packaging Considerations

### Distribution Matrix

| Method | Platform | Status | Priority |
|--------|----------|--------|----------|
| **Homebrew Formula** | macOS, Linux | Ready to implement | 🔴 High |
| **Git Clone + install.sh** | macOS, Linux, WSL | ✅ Works today | ✅ Done |
| **PyPI (pip)** | All platforms | Needs restructuring | 🟡 Medium |
| **pipx** | All platforms | After PyPI | 🟡 Medium |
| **apt (deb)** | Debian/Ubuntu | Future | 🔵 Low |
| **rpm** | Fedora/RHEL | Future | 🔵 Low |
| **Arch AUR** | Arch Linux | Community-driven | 🔵 Low |
| **Windows installer** | Windows | Needs PowerShell hooks | 🟡 Medium |

### PyPI vs Homebrew: Key Differences

**Homebrew:**
- ✅ Handles system dependencies (jq, Python itself)
- ✅ Integrates with macOS/Linux package ecosystem
- ✅ Easy updates (`brew upgrade`)
- ✅ Sets up hooks automatically
- ❌ Platform-limited (macOS/Linux only)
- ❌ Requires formula maintenance

**PyPI (pip/pipx):**
- ✅ Cross-platform (including Windows)
- ✅ Standard Python distribution
- ✅ Easy to publish (`twine upload`)
- ❌ Doesn't handle system dependencies (jq)
- ❌ Doesn't set up hooks automatically
- ❌ Requires restructuring as proper Python package

### Recommended Distribution Strategy

**Phase 1: Homebrew (Now)**
- Target macOS developers (largest audience)
- Handles all dependencies and setup
- Provides CLI commands
- Sets up hooks automatically

**Phase 2: Documentation (Soon)**
- Document Linux installation (git clone)
- Document Windows installation (manual)
- Improve README with platform-specific instructions

**Phase 3: PyPI (Later)**
- Restructure as proper Python package
- Add `pyproject.toml`
- Create CLI entry points
- Publish to PyPI
- Document hook setup as separate step

**Phase 4: Platform Packages (Optional)**
- Create .deb for Ubuntu/Debian
- Create .rpm for Fedora/RHEL
- Submit to Arch AUR
- Create Windows installer

## Security Considerations

**What Homebrew checks:**
- ✅ HTTPS for homepage and downloads
- ✅ SHA256 checksums for all sources
- ✅ License compatibility (MIT is fine)
- ✅ No obvious security vulnerabilities in code

**What we should do:**
- [ ] Add SECURITY.md with vulnerability reporting process
- [ ] Pin Python dependency versions (avoid `>=`, use `~=`)
- [ ] Regular dependency updates for security patches
- [ ] Document what data is collected (none currently)
- [ ] Document where data is stored locally

**Example dependency pinning:**
```ruby
resource "streamlit" do
  url "https://..."
  sha256 "..."
  # Homebrew handles version constraints via sha256
  # Each resource is a specific version
end
```

## File Organization for Packaging

**Current structure (good for git clone):**
```
claude-code-utils/
├── hooks/
├── scripts/
├── streamlit_app/
├── config.py
├── install.sh
└── README.md
```

**For PyPI (would need restructuring):**
```
claude-code-analytics/
├── src/
│   └── claude_code_analytics/
│       ├── __init__.py
│       ├── cli.py           # Entry points
│       ├── config.py
│       ├── streamlit_app/
│       └── scripts/
├── hooks/                   # Separate install
├── pyproject.toml
├── README.md
└── LICENSE
```

**For Homebrew (current structure is fine):**
- Formula downloads tarball
- Installs to `libexec/` (virtualenv)
- Creates symlinks from `bin/` to wrapper scripts
- No restructuring needed!

## Action Items Before Homebrew Release

### Must Have (Blocking)
- [ ] Create v1.0.0 tag
- [ ] Write meaningful tests for formula
- [ ] Test formula locally with `brew install --build-from-source`
- [ ] Run `brew audit --strict --online`
- [ ] Test in clean Docker environment
- [ ] Create homebrew tap repository

### Should Have (Important)
- [ ] Add CHANGELOG.md
- [ ] Document update process for maintainers
- [ ] Create release checklist
- [ ] Set up GitHub Actions for automated testing (optional)

### Nice to Have (Future)
- [ ] Automatic bottle building via CI
- [ ] Livecheck configuration for auto-update detection
- [ ] Migration guide from git clone to Homebrew install

## Questions to Answer

1. **Versioning**: What's in v1.0.0 vs what's future?
2. **Maintenance**: Who maintains the formula after release?
3. **Support**: How do users report issues (GitHub issues)?
4. **Updates**: How often do we release updates?
5. **Breaking changes**: How do we handle them?

## Key Takeaways

✅ **We're in good shape for Homebrew:**
- Code is ready
- Structure works
- License is compatible
- No major blockers

⚠️ **Things to add before release:**
- Meaningful tests
- Version tags
- Better documentation

🔮 **Future packaging paths:**
- PyPI (requires restructuring)
- Platform-specific packages (nice to have)
- Windows support (separate effort)

**Bottom line:** Focus on Homebrew first, it's the right fit for our tool and audience.
