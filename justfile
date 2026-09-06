packages := "web"
project_content := "web tests main.py"

init:
    python3 -m venv .venv
    venv
    pip install -r requirements.txt

# Linting
lint:
    uv run ruff check {{project_content}} --fix
    uv run ruff format {{project_content}}
    uv run mypy {{project_content}} --ignore-missing-imports
    uv run complexipy .

# Tests
test: unit_tests functional_tests

unit_tests:
    find tests -type f -name "test_*.py" -not -name "test_functional.py" -not -path "*sample_project*" | xargs uv run -m unittest -v

functional_tests:
    uv run -m unittest discover -s tests -p "test_functional.py"

coverage:
    find tests -type f -name "test_*.py" -not -name "test_functional.py" | xargs uv run coverage run --source={{packages}} -m unittest
    uv run coverage lcov -o lcov.info
    uv run coverage report -m --fail-under 85 --sort=cover

docs:
    sphinx-apidoc -o docs/source grader
    sphinx-build -b html docs/source docs/build

# Cleaning
clean: clean_logs
    rm -rf .coverage
    rm -rf .pytest_cache
    rm -rf .mypy_cache
    rm -rf docs/build
    rm -f lcov.info
    rm -rf "pygrader-sample-project"

clean_logs:
    rm -rf *.log.*
    rm -rf *.log

clean_venv:
    rm -rf .venv

# Sample project
setup_sample_project: clean_sample_project
    git clone https://github.com/fmipython/pygrader-sample-project

clean_sample_project:
    if [ -d "pygrader-sample-project" ]; then rm -rf "pygrader-sample-project"; fi


build_diagrams:
    java -jar ~/plantuml-1.2025.4.jar ./docs/diagrams/*.puml -o out

# Web via Docker
build_docker:
    docker build -f Dockerfile -t pygrader_web:latest .

run_docker:
    docker run --rm -d -p 8501:8501 --name pygrader_web pygrader_web:latest 
