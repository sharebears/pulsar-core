lint:
	isort -rc .
	black -S -t py37 -l 79 .

tests:
	flake8
	# mypy --no-strict-optional core/  # fuck mypy...
	pytest --cov-report term-missing --cov-branch --cov=core tests/

.PHONY: lint tests
