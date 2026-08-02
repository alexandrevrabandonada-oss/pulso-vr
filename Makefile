PYTHON ?= python

.PHONY: validate test all

validate:
	$(PYTHON) scripts/run_cli.py validate

test:
	$(PYTHON) -m pytest -q

all:
	$(PYTHON) scripts/run_cli.py all
