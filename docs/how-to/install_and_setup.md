---
title: "How to Install and Set Up ed-resolver"
tags: ["how-to", "installation", "setup", "quickstart"]
created_at: "2026-11-08"
last_updated_at: "2026-11-08"
---

# How to Install and Set Up ed-resolver

This guide explains how to install `ed-resolver` into your Python environment and verify that the package is ready for use.

---

## Prerequisites

- **Python:** Version `3.13` or higher.
- A virtual environment tool such as `uv`, `poetry`, or standard `venv`.

---

## 1. Install via pip

To install `ed-resolver` directly from your Git repository using `pip`:

```bash
pip install git+https://github.com/mnaatjes/ed-resolver.git
```

If you are using local development wheels or local path installation:

```bash
pip install /path/to/ed-resolver
```

---

## 2. Install via uv

If you use `uv` for modern, fast Python package management:

```bash
# Add as a project dependency
uv add git+https://github.com/mnaatjes/ed-resolver.git
```

For local development in an existing workspace:

```bash
uv pip install -e .
```

---

## 3. Install Thin CLI Tool via pipx

If you only need the command-line utility in an isolated global environment:

```bash
pipx install git+https://github.com/mnaatjes/ed-resolver.git
```

Verify that the CLI command works:

```bash
ed-resolver --help
```

---

## 4. Local Editable Installation (Development)

To contribute to or inspect `ed-resolver` locally:

1. Clone the repository:

   ```bash
   git clone https://github.com/mnaatjes/ed-resolver.git
   cd ed-resolver
   ```

2. Create and activate a virtual environment:

   ```bash
   uv venv
   source .venv/bin/activate
   ```

3. Install in editable mode with development dependencies:

   ```bash
   uv pip install -e ".[dev]"
   ```

---

## 5. Verification

Verify that the composition root and facade library import cleanly:

```bash
python -c "from ed_resolver.bootstrap import create_resolver; facade = create_resolver(); print('ed-resolver initialized successfully!')"
```

Expected output:

```text
ed-resolver initialized successfully!
```
