SHELL := /bin/sh
BUILD := build

$(BUILD)/catalog.md: catalog.md.jinja .jsmn-tools.py specs/sensor.yaml
	jsmn render --plugin . --env project_name=sensor-kit --template $< $@

.PHONY: run clean
run: $(BUILD)/catalog.md
	cat $<

clean:
	rm -rf $(BUILD)
