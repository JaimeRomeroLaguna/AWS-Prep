#!/usr/bin/env python3
"""
Parse AWS exam questions from PDF text and solutions file,
combining them into a structured JSON file.
"""

import argparse
import json
import re
from pathlib import Path


def parse_questions_from_pdf(pdf_text_path: str) -> dict:
    """Parse questions and options from the PDF text file."""
    with open(pdf_text_path, 'r', encoding='utf-8') as f:
        content = f.read()

    questions = {}

    # Split by question pattern
    question_pattern = r'Question\s+#(\d+)\s+Topic\s+\d+'
    matches = list(re.finditer(question_pattern, content))

    for i, match in enumerate(matches):
        q_num = int(match.group(1))
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)

        block = content[start:end].strip()

        # Options start with letter followed by period
        option_pattern = r'\n\s{2,}([A-F])\.\s+'

        first_option = re.search(option_pattern, block)

        if first_option:
            question_text = block[:first_option.start()].strip()
            options_text = block[first_option.start():]

            options = {}
            option_matches = list(re.finditer(option_pattern, options_text))

            for j, opt_match in enumerate(option_matches):
                letter = opt_match.group(1)
                opt_start = opt_match.end()
                opt_end = option_matches[j + 1].start() if j + 1 < len(option_matches) else len(options_text)

                option_text = options_text[opt_start:opt_end].strip()
                option_text = ' '.join(option_text.split())
                options[letter] = option_text

            question_text = ' '.join(question_text.split())

            questions[q_num] = {
                'number': q_num,
                'question': question_text,
                'options': options,
                'correct_answer': None,
                'explanation': ''
            }

    return questions


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    # Remove punctuation, extra spaces, and lowercase
    text = re.sub(r'[^\w\s]', '', text.lower())
    text = ' '.join(text.split())
    return text[:100]  # First 100 chars for comparison


def find_matching_option(answer_text: str, options: dict):
    """Try to match answer text to one of the options."""
    if not answer_text or not options:
        return None

    answer_norm = normalize_text(answer_text)

    best_match = None
    best_score = 0

    for letter, option_text in options.items():
        option_norm = normalize_text(option_text)

        # Check if one contains the other
        if answer_norm in option_norm or option_norm in answer_norm:
            # Calculate overlap score
            score = len(set(answer_norm.split()) & set(option_norm.split()))
            if score > best_score:
                best_score = score
                best_match = letter

    # Require at least 3 matching words
    if best_score >= 3:
        return best_match

    return None


def is_multi_select(question_text: str) -> int:
    """Return the number of expected answers (2 for 'Choose two', else 1)."""
    if re.search(r'Choose two', question_text, re.IGNORECASE):
        return 2
    return 1


def extract_multi_answers(main_content: str, num_expected: int) -> str:
    """Extract multiple answer letters from a solutions block.

    Looks for lines starting with a letter followed by a period (e.g. 'A. ...')
    and returns the first `num_expected` unique letters found.
    """
    # Find all lines that start with an answer letter pattern
    letter_matches = re.findall(r'(?:^|\n)\s*([A-F])\.\s+', main_content)
    seen = []
    for letter in letter_matches:
        letter = letter.upper()
        if letter not in seen:
            seen.append(letter)
        if len(seen) == num_expected:
            break
    return ''.join(seen) if len(seen) == num_expected else None


def parse_answers_from_solutions(solutions_path: str, questions: dict) -> dict:
    """Parse correct answers and explanations from the solutions file."""
    with open(solutions_path, 'r', encoding='utf-8') as f:
        content = f.read()

    answers = {}

    question_pattern = r'(?:^|\n)(\d+)\s*\]'
    matches = list(re.finditer(question_pattern, content))

    for i, match in enumerate(matches):
        q_num = int(match.group(1))
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)

        block = content[start:end].strip()
        parts = re.split(r'-{10,}', block)
        if not parts:
            continue

        main_content = parts[0].strip()

        # Check if this is a multi-select question
        q_text = questions[q_num]['question'] if q_num in questions else ""
        num_answers = is_multi_select(q_text)

        answer_letter = None
        answer_text = ""
        explanation = ""

        # For multi-select questions, try to extract all answer letters at once
        if num_answers > 1:
            multi = extract_multi_answers(main_content, num_answers)
            if multi:
                answer_letter = multi

        # Method 1: Look for "Correct answer X:" pattern
        if not answer_letter:
            correct_match = re.search(r'Correct\s+answer\s+([A-F]):', main_content, re.IGNORECASE)
            if correct_match:
                answer_letter = correct_match.group(1).upper()

        # Method 2: Look for "ans-" pattern
        if not answer_letter:
            ans_match = re.search(r'\n\s*ans[-–—]?\s*[-–—]?\s*', main_content, re.IGNORECASE)
            if ans_match:
                rest = main_content[ans_match.end():].strip()

                # Check if starts with letter
                letter_match = re.match(r'^([A-F])[\.\s:\-]', rest, re.IGNORECASE)
                if letter_match:
                    answer_letter = letter_match.group(1).upper()
                    rest = rest[letter_match.end():].strip()

                # Get answer text (first line or until double newline)
                lines = rest.split('\n')
                answer_text = lines[0].strip() if lines else ""

                # Get explanation
                exp_parts = re.split(r'\n\n+', rest, maxsplit=1)
                if len(exp_parts) > 1:
                    explanation = exp_parts[1].strip()

        # Method 3: Look for standalone letter pattern "A." or "B."
        if not answer_letter:
            letter_match = re.search(r'\n\s*([A-F])\.\s+', main_content)
            if letter_match:
                answer_letter = letter_match.group(1).upper()
                rest = main_content[letter_match.end():].strip()
                answer_text = rest.split('\n')[0].strip()
                exp_parts = re.split(r'\n\n+', rest, maxsplit=1)
                if len(exp_parts) > 1:
                    explanation = exp_parts[1].strip()

        # Method 4: If no letter found, try to match answer text to options
        if not answer_letter and answer_text and q_num in questions:
            answer_letter = find_matching_option(answer_text, questions[q_num]['options'])

        # Method 5: If still no letter, extract answer text after "ans-" and match
        if not answer_letter and q_num in questions:
            ans_match = re.search(r'ans[-–—]?\s*[-–—]?\s*(.+?)(?:\n\n|\n[A-Z][a-z])', main_content, re.IGNORECASE | re.DOTALL)
            if ans_match:
                answer_text = ans_match.group(1).strip()
                answer_letter = find_matching_option(answer_text, questions[q_num]['options'])

        if answer_letter:
            # Get explanation if we don't have it yet
            if not explanation:
                # Everything after the answer line
                ans_pos = main_content.find('ans')
                if ans_pos == -1:
                    ans_pos = main_content.find(answer_letter[0] + '.')
                if ans_pos != -1:
                    rest = main_content[ans_pos:]
                    exp_parts = re.split(r'\n\n+', rest, maxsplit=1)
                    if len(exp_parts) > 1:
                        explanation = exp_parts[1].strip()

            answers[q_num] = {
                'answer': answer_letter,
                'explanation': explanation[:1500] if explanation else ""
            }

    return answers


def combine_questions_and_answers(questions: dict, answers: dict) -> list:
    """Combine questions with their correct answers."""
    combined = []

    for q_num, q_data in sorted(questions.items()):
        if q_num in answers:
            q_data['correct_answer'] = answers[q_num]['answer']
            q_data['explanation'] = answers[q_num]['explanation']

        # Only include questions that have options and a valid correct answer
        if q_data['options'] and q_data['correct_answer']:
            # Validate all letters in correct_answer exist in options
            answer = q_data['correct_answer']
            if all(letter in q_data['options'] for letter in answer):
                combined.append(q_data)

    return combined


def main():
    script_dir = Path(__file__).parent

    parser = argparse.ArgumentParser(description="Parse AWS exam questions into JSON")
    parser.add_argument("--cert", default="saa-c03",
                        help="Cert ID (e.g. saa-c03). Sets default --solutions and --output.")
    parser.add_argument("--input", default=None,
                        help="Raw questions text file (default: questions_raw.txt)")
    parser.add_argument("--solutions", default=None,
                        help="Solutions text file (default: AWS {CERT}-Solution.txt)")
    parser.add_argument("--output", default=None,
                        help="Output JSON file (default: {cert}_questions.json)")
    args = parser.parse_args()

    cert = args.cert.lower()
    cert_upper = cert.upper()

    pdf_text_path = Path(args.input) if args.input else script_dir / "questions_raw.txt"
    solutions_path = (Path(args.solutions) if args.solutions
                      else script_dir / f"AWS {cert_upper}-Solution.txt")
    output_path = Path(args.output) if args.output else script_dir / f"{cert}_questions.json"

    print(f"Parsing questions for {cert_upper}...")
    questions = parse_questions_from_pdf(str(pdf_text_path))
    print(f"Found {len(questions)} questions in PDF")

    print("Parsing answers from solutions file...")
    answers = parse_answers_from_solutions(str(solutions_path), questions)
    print(f"Found {len(answers)} answers in solutions file")

    print("Combining questions and answers...")
    combined = combine_questions_and_answers(questions, answers)
    print(f"Combined {len(combined)} complete questions")

    # Save to JSON
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)

    print(f"Saved to {output_path}")

    # Stats
    missing = set(questions.keys()) - set(answers.keys())
    if missing:
        print(f"\nQuestions without parsed answers: {len(missing)}")


if __name__ == "__main__":
    main()
