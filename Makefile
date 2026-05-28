# `--progress quiet` suppresses compose's "Container ... Creating / Created"
# status lines; recipe lines are prefixed with `@` so make doesn't echo the
# command itself either. Result: only the app's own output reaches the terminal.
COMPOSE := docker compose --progress quiet
RUN := $(COMPOSE) run --rm app

# Optional `--provider` override. Default comes from TAILORCV_PROVIDER in .env
# (or `anthropic` if unset). Example: `make generate FILE=offer.txt PROVIDER=google`.
PROVIDER_ARG := $(if $(PROVIDER),--provider $(PROVIDER))

# Pick exactly one input source. URL wins, then FILE, then TEXT.
# FILE is read from the host: we mount it into the container at a fixed path
# because docker-compose.yml only bind-mounts a curated set of subdirs, not the
# whole repo root.
ifdef URL
INPUT_ARG := --url "$(URL)"
INPUT_RUN := $(RUN)
else ifdef FILE
INPUT_ARG := --text-file /app/inputs/job-ad.txt
INPUT_RUN := $(COMPOSE) run --rm -v "$(abspath $(FILE))":/app/inputs/job-ad.txt:ro app
else ifdef TEXT
INPUT_ARG := --text "$(TEXT)"
INPUT_RUN := $(RUN)
endif

.PHONY: build generate cv-only letter-only tokens shell test

build:
	@$(COMPOSE) build

# Usage:
#   make generate URL="https://example.com/job"
#   make generate FILE=offer.txt
#   make generate TEXT="paste the job ad here"
# Append PROVIDER=google to route to Gemini for any of the above.
generate:
	@$(INPUT_RUN) python -m tailorcv generate $(INPUT_ARG) $(PROVIDER_ARG)

cv-only:
	@$(INPUT_RUN) python -m tailorcv generate $(INPUT_ARG) $(PROVIDER_ARG) --cv-only

letter-only:
	@$(INPUT_RUN) python -m tailorcv generate $(INPUT_ARG) $(PROVIDER_ARG) --letter-only

tokens:
	@$(RUN) python -m tailorcv kb-tokens

shell:
	$(RUN) bash

test:
	@$(RUN) pytest -q
