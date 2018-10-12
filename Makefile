lint:
	isort -rc .
_tests:
	flake8
	mypy --no-strict-optional core/
	pytest --cov-report term-missing --cov-branch --cov=pulsar tests/
tests: _tests
