.PHONY: quiz parse test clean help

# Default target - show help
help:
	@echo "Available commands:"
	@echo "  make quiz    - Run the AWS quiz"
	@echo "  make parse   - Parse questions from raw text into JSON"
	@echo "  make test    - Run tests"
	@echo "  make clean   - Remove generated JSON file"
	@echo "  make help    - Show this help message"

# Run the quiz
quiz:
	python3 aws_quiz.py

# Run tests
test:
	python3 -m unittest test_quiz -v

# Parse raw questions into JSON
parse:
	python3 parse_questions.py

# Remove generated files
clean:
	rm -f aws_questions.json
