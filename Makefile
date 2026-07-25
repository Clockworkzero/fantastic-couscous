.PHONY: setup run clean

setup:
	@chmod +x setup.sh
	@./setup.sh

run:
	@python3 app.py

clean:
	rm -rf output.mp4 __pycache__

