packages := "web"
project_content := "web tests main.py"

venv:
    . .venv/bin/activate

init:
    python3 -m venv .venv
    venv
    pip install -r requirements.txt

# Linting
lint: venv
    python3 -m pylint {{project_content}} --fail-under 9
    mypy {{project_content}} --ignore-missing-imports
    flake8 {{project_content}}
    complexipy .

lint_file file: venv
    python3 -m pylint {{file}} --fail-under 9
    mypy {{file}} --ignore-missing-imports

# Tests
test: unit_tests functional_tests

unit_tests: venv
    find tests -type f -name "test_*.py" -not -name "test_functional.py" -not -path "*sample_project*" | xargs python3 -m unittest -v

functional_tests: venv
    python3 -m unittest discover -s tests -p "test_functional.py"

coverage: venv
    find tests -type f -name "test_*.py" -not -name "test_functional.py" | xargs coverage run --source={{packages}} -m unittest
    coverage lcov -o lcov.info
    coverage report -m --fail-under 85 --sort=cover

push: venv lint test
    git push

run: venv
    python3 src/pygrader.py

docs: venv
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
build_docker_web:
    docker build -f Dockerfile.web -t pygrader_web:latest .

run_docker_web:
    docker run --rm -d -p 8501:8501 --name pygrader_web pygrader_web:latest 
