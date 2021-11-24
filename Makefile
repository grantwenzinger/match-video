.PHONY: install install-test install-local shell clean update \
	lint test test-verbose \
	build-package publish-package \

MODULE_NAME := match_video

# Installation

install:
	LDFLAGS="$(pg_config --ldflags)" SYSTEM_VERSION_COMPAT="1" poetry install

install-test:
	LDFLAGS="$(pg_config --ldflags)" SYSTEM_VERSION_COMPAT="1" poetry install --extras "test"

install-local:
	LDFLAGS="$(pg_config --ldflags)" SYSTEM_VERSION_COMPAT="1" poetry install --extras "lint test examples"
	poetry run pre-commit install

shell:
	poetry shell

clean:
	rm -R dist

update:
	git pull
	poetry lock
	LDFLAGS="$(pg_config --ldflags)" SYSTEM_VERSION_COMPAT="1" poetry install


# Testing, documentation

lint:
	poetry run pre-commit run --all-files

test:
	poetry run pytest --cov $(MODULE_NAME) --cov-report html

test-verbose:
	poetry run pytest --cov $(MODULE_NAME)


# Gitlab package

build-package:
	poetry build

publish-package:
	poetry publish
