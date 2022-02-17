OUTPUT_DIR ?= build

SOURCES = \
	AccessControl.cairo \
	FacadeAdmin.cairo \
	Ledger.cairo \
	LedgerFacade.cairo \
	Proxy.cairo \
	ProxyAdmin.cairo
OUTPUTS = $(patsubst %.cairo,$(OUTPUT_DIR)/%_compiled.json,$(SOURCES))
ABIS = $(patsubst %.cairo,$(OUTPUT_DIR)/%_abi.json,$(SOURCES))

build/%_compiled.json build/%_abi.json: %.cairo
	starknet-compile $< --abi build/$(basename $<)_abi.json --output build/$(basename $<)_compiled.json --cairo_path .

all: $(OUTPUTS) $(ABIS)

test:
	pytest

clean:
	@rm -fv $(OUTPUT_DIR)/*

.PHONY: all test clean
