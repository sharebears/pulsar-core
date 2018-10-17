lint:
	isort -rc .
_tests:
	flake8
	# mypy --no-strict-optional core/  # fuck mypy...
	pytest --cov-report term-missing --cov-branch --cov=core tests/
tests: _tests
