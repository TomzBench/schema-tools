SHELL   := /bin/sh
BUILD   := build
CFLAGS  := -Os -DJT_HAS_FLOAT -Wall

$(BUILD)/main: $(BUILD)/main.c
	$(CC) $(CFLAGS) -o $@ $<

$(BUILD)/main.c: main.c.jinja sensor.yaml
	jsmn render sensor.yaml --template $< $@

.PHONY: run clean
run: $(BUILD)/main
	./$<

clean:
	rm -rf $(BUILD)
