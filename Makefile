CERT ?= saa-c03

.PHONY: quiz web parse test clean help

# Default target - show help
help:
	@echo "Available commands:"
	@echo "  make quiz [CERT=saa-c03]  - Run the AWS quiz (CLI)"
	@echo "  make web                  - Run the AWS quiz (web, http://localhost:5001)"
	@echo "  make parse [CERT=saa-c03] - Parse questions from raw text into JSON"
	@echo "  make test                 - Run tests"
	@echo "  make clean                - Remove all *_questions.json files"
	@echo "  make help                 - Show this help message"

# Run the quiz (CLI)
quiz:
	venv/bin/python3 aws_quiz.py $(CERT)

# Run the quiz (web) - port 5001 (macOS reserves 5000 for AirPlay)
web:
	venv/bin/python3 web_quiz.py 5001

# Run tests
test:
	venv/bin/python3 -m unittest test_quiz -v

# Parse raw questions into JSON
parse:
	venv/bin/python3 parse_questions.py --cert $(CERT)

# Remove generated files
clean:
	rm -f *_questions.json
