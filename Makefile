# Makefile for WSE Indices Weights Loader

.PHONY: help install test run clean format lint dev tag-release

help:
	@echo "WSE Indices Weights Loader - Available targets:"
	@echo "  help           Show this help message"
	@echo "  install        Install project dependencies"
	@echo "  test           Run all tests"
	@echo "  test-unit      Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  run            Run the main application"
	@echo "  clean          Clean up generated files"
	@echo "  format         Format code with black"
	@echo "  lint           Run linting checks"
	@echo "  dev            Set up development environment"
	@echo "  version        Show current version"
	@echo "  tag-release    Create git tag for current version"

install:
	@echo "Installing dependencies with uv..."
	uv sync

dev: install
	@echo "Development environment ready!"
	@echo "Run 'make test' to verify everything works"

test:
	@echo "Running all tests..."
	uv run python -m pytest tests/ -v

test-unit:
	@echo "Running unit tests..."
	uv run python -m pytest tests/test_pdf_parser.py tests/test_pdf_downloader.py -v

test-integration:
	@echo "Running integration tests..."
	uv run python -m pytest tests/test_integration.py tests/test_pdf_parser_fixes.py -v

run:
	@echo "Running WSE Indices Weights Loader..."
	uv run python src/__main__.py

format:
	@echo "Formatting code with black..."
	uv run black src/ tests/

lint:
	@echo "Running linting checks..."
	uv run python -m py_compile src/*.py
	uv run python -m py_compile tests/*.py

clean:
	@echo "Cleaning up generated files..."
	rm -rf __pycache__ src/__pycache__ tests/__pycache__
	rm -rf .pytest_cache
	rm -rf dist/ build/ *.egg-info/
	rm -f downloads/*.pdf
	rm -f output/*.csv output/*.xlsx output/*.json

# Development helpers
download-sample:
	@echo "Downloading sample data for testing..."
	uv run python -c "from src.pdf_downloader import PDFDownloader; PDFDownloader().download_for_date('2024_06_21')"

parse-sample:
	@echo "Parsing sample data..."
	uv run python -c "from src.pdf_parser import PDFParser; parser = PDFParser(); stocks = parser.parse_pdf('downloads/2024_06_21_WIG.pdf'); parser.export_to_csv(stocks, 'output/sample_output.csv'); print(f'Parsed {len(stocks)} stocks')"

# Version management
version:
	@echo "Current version: $$(grep '^version' pyproject.toml | cut -d'"' -f2)"

tag-release:
	@VERSION=$$(grep '^version' pyproject.toml | cut -d'"' -f2); \
	echo "Tagging release v$$VERSION..."; \
	git add .; \
	git commit -m "Release v$$VERSION" || echo "No changes to commit"; \
	git tag -a "v$$VERSION" -m "Release version $$VERSION"; \
	echo "Tagged as v$$VERSION"; \
	echo "To push the tag, run: git push origin v$$VERSION"
