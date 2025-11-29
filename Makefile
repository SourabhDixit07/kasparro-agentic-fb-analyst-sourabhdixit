.PHONY: setup run test clean lint

setup:
	python -m venv venv
	. venv/bin/activate && pip install -r requirements.txt
	@echo "✅ Setup complete! Activate with: source venv/bin/activate"

run:
	python run.py "Why did ROAS drop?"

test:
	python run.py "Test analysis with sample data"

clean:
	rm -rf reports/*.json reports/*.md logs/*.json
	find . -type d -name __pycache__ -exec rm -rf {} +
	@echo "✅ Cleaned outputs and cache"

lint:
	flake8 src/ --max-line-length=100
	black src/ --check

install:
	pip install -r requirements.txt

help:
	@echo "Available commands:"
	@echo "  make setup   - Create venv and install dependencies"
	@echo "  make run     - Run example analysis"
	@echo "  make test    - Run with sample data"
	@echo "  make clean   - Remove outputs and cache"
	@echo "  make lint    - Check code style"
