# Contributing to QuakeScope

Thank you for your interest in contributing to **QuakeScope — Global Earthquake Intelligence**!

---

## 1. Local Development Setup

### Prerequisites
* Python 3.10 or newer (tested on Python 3.11, 3.12, 3.13)
* Git

### Windows PowerShell Setup
```powershell
# Clone the repository
git clone https://github.com/KhaleelxRahman/earthquake-github-dashboard.git
cd earthquake-github-dashboard

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### macOS / Linux Setup
```bash
# Clone the repository
git clone https://github.com/KhaleelxRahman/earthquake-github-dashboard.git
cd earthquake-github-dashboard

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## 2. Running Tests & Quality Checks

Run the automated test suite before submitting any changes:

```bash
# Run unit and integration tests with standard unittest
python -m unittest discover -s tests -v

# Or with pytest if installed
pytest -v
```

All 21 automated tests must pass.

---

## 3. Building the Dashboard Locally

```bash
# Standard build (fetches live data, falls back to cache if offline)
python data_pipeline.py

# Force offline build using verified baseline
python data_pipeline.py --offline

# Validate output integrity without regenerating
python data_pipeline.py --validate-only
```

Open `index.html` in your web browser to review your changes locally.

---

## 4. Coding Standards

* Follow **PEP 8** style guidelines for Python code.
* Use explicit type annotations where practical.
* Never commit secrets, API tokens, or personal access tokens.
* Preserve atomic write guarantees and schema validations in `data_pipeline.py`.
* Ensure that the frontend remains fully accessible, responsive, and resilient to offline usage.

