
SHELL := /bin/bash

# Function name in AWS Lambda:
FUNCTION_NAME=haaska

BUILD_DIR=build
PYTHON ?= python3

# Always rebuild so removed configuration files cannot survive in the ZIP.
.PHONY: haaska.zip
haaska.zip: haaska.py requirements.txt config/*
	@test -f config/config.json || { echo 'Create config/config.json before building'; exit 1; }
	rm -rf $(BUILD_DIR)
	rm -f $@
	mkdir -p $(BUILD_DIR)
	cp haaska.py config/* $(BUILD_DIR)
	$(PYTHON) -m pip install --no-compile --only-binary=:all: --platform any --implementation py --abi none -t $(BUILD_DIR) -r requirements.txt
	chmod 755 $(BUILD_DIR)/haaska.py
	cd $(BUILD_DIR) && zip ../$@ -r *

.PHONY: deploy
deploy: haaska.zip
	aws lambda update-function-configuration \
		--function-name $(FUNCTION_NAME) \
		--handler haaska.event_handler
	aws lambda update-function-code \
		--function-name $(FUNCTION_NAME) \
		--zip-file fileb://$<

DISCOVERY_PAYLOAD:='                                \
{                                                         \
  "directive": {                                          \
    "header": {                                           \
      "namespace": "Alexa.Discovery",                     \
      "name": "Discover",                                 \
      "payloadVersion": "3",                              \
      "messageId": "1bd5d003-31b9-476f-ad03-71d471922820" \
    },                                                    \
    "payload": {                                          \
      "scope": {                                          \
        "type": "BearerToken",                            \
        "token": "access-token-from-skill"                \
      }                                                   \
    }                                                     \
  }                                                       \
}'

.PHONY: discover
discover:
	@aws lambda invoke \
		--function-name $(FUNCTION_NAME) \
		--payload ${DISCOVERY_PAYLOAD} \
		/dev/fd/3 3>&1 >/dev/null | jq '.'


.PHONY: clean
clean:
	rm -rf $(BUILD_DIR) haaska.zip

.PHONY: sample_config
sample_config:
	python -c 'from haaska import Configuration; print(Configuration().dump())' > config/config.json.sample

.PHONY: modernize_config
modernize_config: config/config.json
	@python -c 'from haaska import Configuration; print(Configuration("config/config.json").dump())' > config/config.json.modernized
	@echo Generated config/config.json.modernized from your existing config/config.json
	@echo Inspect that file and replace config/config.json with it to update your configuration
