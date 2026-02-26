.PHONY: quiz web parse test clean help

# Default target - show help
help:
	@echo "Available commands:"
	@echo "  make quiz    - Run the AWS quiz (CLI)"
	@echo "  make web     - Run the AWS quiz (web, opens at http://localhost:5000)"
	@echo "  make parse   - Parse questions from raw text into JSON"
	@echo "  make test    - Run tests"
	@echo "  make clean   - Remove generated JSON file"
	@echo "  make help    - Show this help message"

# Run the quiz (CLI)
quiz:
	python3 aws_quiz.py

# Run the quiz (web) - port 5001 (macOS reserves 5000 for AirPlay)
web:
	venv/bin/python3 web_quiz.py 5001

# Run tests
test:
	python3 -m unittest test_quiz -v

# Parse raw questions into JSON
parse:
	python3 parse_questions.py

# Remove generated files
clean:
	rm -f aws_questions.json
