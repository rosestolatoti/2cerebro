# Project Rules

## Lint
- flake8 app.py database.py ocr_engine.py file_manager.py config.py --max-line-length=120

## Syntax Check
- python -m py_compile app.py database.py ocr_engine.py file_manager.py

## Tests
- pytest -q
