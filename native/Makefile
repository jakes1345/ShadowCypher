CC = gcc
CFLAGS = -Wall -Wextra -O2 $(shell pkg-config --cflags gtk+-3.0 webkit2gtk-4.1)
LDFLAGS = $(shell pkg-config --libs gtk+-3.0 webkit2gtk-4.1)
TARGET = shadowcypher

all: $(TARGET)

$(TARGET): shadowcypher.c
	$(CC) $(CFLAGS) -o $@ $< $(LDFLAGS)

clean:
	rm -f $(TARGET)

install: $(TARGET)
	cp $(TARGET) /usr/local/bin/shadowcypher
	cp shadowcypher.desktop /usr/share/applications/
	@echo "Installed. Run 'shadowcypher' from anywhere or find it in your app menu."

.PHONY: all clean install
