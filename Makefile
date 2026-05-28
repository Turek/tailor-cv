COMPOSE := docker compose
RUN := $(COMPOSE) run --rm app

# Optional `--provider` override. Default comes from TAILORCV_PROVIDER in .env
# (or `anthropic` if unset). Example: `make generate FILE=offer.txt PROVIDER=google`.
PROVIDER_ARG := $(if $(PROVIDER),--provider $(PROVIDER))

# Pick exactly one input source. URL wins, then FILE, then TEXT.
ifdef URL
INPUT_ARG := --url "$(URL)"
else ifdef FILE
INPUT_ARG := --text-file "$(FILE)"
else ifdef TEXT
INPUT_ARG := --text "$(TEXT)"
endif

.PHONY: build generate cv-only letter-only tokens shell test

build:
	$(COMPOSE) build

# Usage:
#   make generate URL="https://example.com/job"
#   make generate FILE=offer.txt
#   make generate TEXT="paste the job ad here"
# Append PROVIDER=google to route to Gemini for any of the above.
generate:
	$(RUN) python -m tailorcv generate $(INPUT_ARG) $(PROVIDER_ARG)

cv-only:
	$(RUN) python -m tailorcv generate $(INPUT_ARG) $(PROVIDER_ARG) --cv-only

letter-only:
	$(RUN) python -m tailorcv generate $(INPUT_ARG) $(PROVIDER_ARG) --letter-only

tokens:
	$(RUN) python -m tailorcv kb-tokens

shell:
	$(RUN) bash

test:
	$(RUN) pytest -q
