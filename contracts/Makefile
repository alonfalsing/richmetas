OUTPUT_DIR ?= build

SOURCES	= \
	AccessControl.cairo \
	FacadeAdmin.cairo \
	Login.cairo \
	LoginFacade.cairo \
	LoginFacadeAdmin.cairo \
	Ledger.cairo \
	LedgerFacade.cairo \
	LedgerLoader.cairo \
	Exchange.cairo \
	ExchangeFacade.cairo \
	ExchangeLoader.cairo \
	Staking.cairo \
	StakingFacade.cairo \
	StakingFacadeAdmin.cairo \
	Proxy.cairo \
	ProxyAdmin.cairo \
	Richmetas.sol \
	RichmetasForwarder.sol \
	ERC721PresetMinter.sol
OUTPUTS	= $(patsubst %.sol,$(OUTPUT_DIR)/%.bin, \
	$(patsubst %.cairo,$(OUTPUT_DIR)/%_compiled.json,$(SOURCES)))
ABIS 	= $(patsubst %.sol,$(OUTPUT_DIR)/%.abi, \
	$(patsubst %.cairo,$(OUTPUT_DIR)/%_abi.json,$(SOURCES)))

build/%.abi build/%.bin: %.sol
	solc --abi --bin -o build $< --base-path . --include-path node_modules --overwrite

build/%_compiled.json build/%_abi.json: %.cairo
	starknet-compile $< \
	--abi build/$(basename $<)_abi.json \
	--output build/$(basename $<)_compiled.json \
	--cairo_path .

build/%.d: %.cairo
	ddd $< --cairo_path . | \
	sed "s/^/$(subst /,\/,$@): /" | \
	sed "s/^/$(patsubst %.cairo,$(OUTPUT_DIR)\/%_abi.json,$<) /" | \
	sed "s/^/$(patsubst %.cairo,$(OUTPUT_DIR)\/%_compiled.json,$<) /" > $@

all: $(OUTPUTS) $(ABIS)

test:
	pytest -x

clean:
	@rm -fv $(OUTPUT_DIR)/*

.PHONY: all test clean

include $(patsubst %.cairo,$(OUTPUT_DIR)/%.d,$(filter %.cairo,$(SOURCES)))
