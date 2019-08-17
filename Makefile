lint:
	isort -rc .

tests:
	flake8
	# mypy --no-strict-optional core/  # fuck mypy...
	pytest --cov-report term-missing --cov-branch --cov=core tests/

.PHONY: lint tests
