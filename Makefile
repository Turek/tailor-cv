COMPOSE := docker compose
RUN := $(COMPOSE) run --rm app

.PHONY: build generate cv-only letter-only tokens shell test

build:
	$(COMPOSE) build

# Usage: make generate URL="https://..."   OR   make generate TEXT="paste here"
generate:
ifdef URL
	$(RUN) python -m tailorcv generate --url "$(URL)"
else
	$(RUN) python -m tailorcv generate --text "$(TEXT)"
endif

cv-only:
	$(RUN) python -m tailorcv generate --url "$(URL)" --cv-only

letter-only:
	$(RUN) python -m tailorcv generate --url "$(URL)" --letter-only

tokens:
	$(RUN) python -m tailorcv kb-tokens

shell:
	$(RUN) bash

test:
	$(RUN) pytest -q
