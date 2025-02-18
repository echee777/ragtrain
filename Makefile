# Get absolute path to src directory
REPO_ROOT := $(shell pwd)
SRC_PATH := $(REPO_ROOT)/src
PYTEST_INI := $(REPO_ROOT)/pytest.ini

# Import docker server makefile
-include docker/server/Makefile

.PHONY: setup test testbench docker-build clean datadir

datadir:
	mkdir -p data/training_data/documents
	mkdir -p data/training_data/embeddings

setup: datadir
	pixi install
	pixi run post-install

shell:
	pixi shell

test:
	cd test/unit && PYTHONPATH=$(SRC_PATH) pytest --rootdir=$(REPO_ROOT) -c $(PYTEST_INI) && cd $(REPO_ROOT)

testbench:
	cd test/manual && PYTHONPATH=$(SRC_PATH) python testbench.py && cd $(REPO_ROOT)

google:
	cd test/spike && PYTHONPATH=$(SRC_PATH) python google.py && cd $(REPO_ROOT)

docker-build:
	cd docker/server && make docker-build && cd $(REPO_ROOT)

# Optional clean target
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
