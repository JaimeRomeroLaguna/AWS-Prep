#!/usr/bin/env python3
"""
AWS Certification Quiz Tool
A terminal-based multiple choice quiz for AWS certification exam prep.
"""

import json
import os
import random
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

_cert_name = ""  # set by main(); used by print_header()


def cert_name_from_path(path: Path) -> str:
    """'saa-c03_questions.json' → 'SAA-C03'"""
    return path.stem.replace("_questions", "").upper()


def progress_path_from_questions(questions_path: Path) -> Path:
    cert_id = cert_name_from_path(questions_path).lower()
    return questions_path.parent / f".{cert_id}_progress.json"


@dataclass
class Question:
    """Represents a single quiz question."""
    number: int
    text: str
    options: dict  # {'A': 'text', 'B': 'text', ...}
    correct_answer: str  # 'A', 'B', 'C', or 'D'
    explanation: str
    domain: str = ""


@dataclass
class Progress:
    """Tracks user progress across sessions."""
    total_questions: int = 0
    questions_answered: int = 0
    correct_answers: int = 0
    current_session_correct: int = 0
    current_session_total: int = 0
    last_question_index: int = 0
    question_stats: dict = field(default_factory=dict)
    last_session: str = ""


class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'


def colorize(text: str, color: str) -> str:
    return f"{color}{text}{Colors.RESET}"


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def extract_domain(question_text: str) -> str:
    """Try to extract/infer the AWS domain from question text."""
    domains = {
        'Compute': ['EC2', 'Lambda', 'ECS', 'EKS', 'Fargate', 'Auto Scaling', 'Elastic Beanstalk'],
        'Storage': ['S3', 'EBS', 'EFS', 'FSx', 'Storage Gateway', 'Snowball', 'Glacier'],
        'Database': ['RDS', 'DynamoDB', 'Aurora', 'ElastiCache', 'Redshift', 'DocumentDB'],
        'Networking': ['VPC', 'CloudFront', 'Route 53', 'Direct Connect', 'VPN', 'Transit Gateway',
                       'API Gateway', 'Load Balancer', 'ALB', 'NLB'],
        'Security': ['IAM', 'KMS', 'Secrets Manager', 'WAF', 'Shield', 'GuardDuty',
                     'Certificate Manager', 'ACM', 'Security Group'],
        'Analytics': ['Athena', 'Kinesis', 'EMR', 'Glue', 'QuickSight', 'OpenSearch'],
        'Integration': ['SQS', 'SNS', 'EventBridge', 'Step Functions'],
        'Management': ['CloudWatch', 'CloudTrail', 'Config', 'Systems Manager', 'Organizations'],
    }

    text_upper = question_text.upper()
    matched = []

    for domain, keywords in domains.items():
        for keyword in keywords:
            if keyword.upper() in text_upper:
                matched.append(domain)
                break

    return ', '.join(matched[:2]) if matched else 'General'


def load_questions(json_path: str) -> list:
    """Load questions from JSON file."""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    questions = []
    for q in data:
        questions.append(Question(
            number=q['number'],
            text=q['question'],
            options=q['options'],
            correct_answer=q['correct_answer'],
            explanation=q.get('explanation', ''),
            domain=extract_domain(q['question'])
        ))

    return questions


def load_progress(progress_file: str) -> Progress:
    if os.path.exists(progress_file):
        try:
            with open(progress_file, 'r') as f:
                data = json.load(f)
                return Progress(**data)
        except (json.JSONDecodeError, TypeError):
            pass
    return Progress()


def save_progress(progress: Progress, progress_file: str):
    progress.last_session = datetime.now().isoformat()
    with open(progress_file, 'w') as f:
        json.dump(asdict(progress), f, indent=2)


def print_header():
    print(colorize("╔════════════════════════════════════════════════════════════╗", Colors.CYAN))
    print(colorize("║           AWS Certification Quiz Tool                      ║", Colors.CYAN))
    if _cert_name:
        line = f"  {_cert_name}"
        print(colorize(f"║{line.ljust(60)}║", Colors.CYAN))
    print(colorize("╚════════════════════════════════════════════════════════════╝", Colors.CYAN))
    print()


def print_stats(progress: Progress, total: int):
    session_pct = (progress.current_session_correct / progress.current_session_total * 100
                   if progress.current_session_total > 0 else 0)
    overall_pct = (progress.correct_answers / progress.questions_answered * 100
                   if progress.questions_answered > 0 else 0)

    print(colorize("─" * 62, Colors.DIM))
    print(f"  Session: {colorize(f'{progress.current_session_correct}/{progress.current_session_total}', Colors.YELLOW)} "
          f"({session_pct:.0f}%)  │  "
          f"Overall: {colorize(f'{progress.correct_answers}/{progress.questions_answered}', Colors.BLUE)} "
          f"({overall_pct:.0f}%)  │  "
          f"Total: {total} questions")
    print(colorize("─" * 62, Colors.DIM))
    print()


def display_question(question: Question, index: int, total: int):
    print(colorize(f"Question {question.number} ", Colors.BOLD) +
          colorize(f"({index + 1}/{total})", Colors.DIM))
    if question.domain:
        print(colorize(f"[{question.domain}]", Colors.CYAN))
    print()
    print(question.text)
    print()

    # Display options
    for letter in sorted(question.options.keys()):
        print(f"  {colorize(letter, Colors.YELLOW)}. {question.options[letter]}")
    print()


def is_multi_select(question: Question) -> int:
    """Return the number of expected answers (2 for 'Choose two', else 1)."""
    if 'choose two' in question.text.lower():
        return 2
    return 1


def display_result(question: Question, user_answer: str, is_correct: bool):
    print()
    print(colorize("═" * 62, Colors.GREEN if is_correct else Colors.RED))

    multi = is_multi_select(question)

    if is_correct:
        print(colorize("✓ CORRECT!", Colors.GREEN + Colors.BOLD))
    else:
        print(colorize("✗ INCORRECT", Colors.RED + Colors.BOLD))
        if multi > 1:
            user_display = ', '.join(sorted(user_answer))
            correct_display = ', '.join(sorted(question.correct_answer))
            print(f"  Your answers: {colorize(user_display, Colors.RED)}")
            print(f"  Correct answers: {colorize(correct_display, Colors.GREEN)}")
        else:
            print(f"  Your answer: {colorize(user_answer, Colors.RED)}")
            print(f"  Correct answer: {colorize(question.correct_answer, Colors.GREEN)}")

    print()
    if multi > 1:
        print(colorize("CORRECT ANSWERS:", Colors.GREEN + Colors.BOLD))
        for letter in sorted(question.correct_answer):
            print(f"  {letter}. {question.options[letter]}")
    else:
        print(colorize("CORRECT ANSWER:", Colors.GREEN + Colors.BOLD))
        print(f"  {question.correct_answer}. {question.options[question.correct_answer]}")

    if question.explanation:
        print()
        print(colorize("EXPLANATION:", Colors.BLUE + Colors.BOLD))
        # Word wrap the explanation
        words = question.explanation.split()
        line = "  "
        for word in words:
            if len(line) + len(word) > 70:
                print(colorize(line, Colors.DIM))
                line = "  "
            line += word + " "
        if line.strip():
            print(colorize(line, Colors.DIM))

    print(colorize("═" * 62, Colors.GREEN if is_correct else Colors.RED))
    print()


def get_domains(questions: list) -> list:
    domains = set()
    for q in questions:
        if q.domain:
            for d in q.domain.split(', '):
                domains.add(d)
    return sorted(domains)


def filter_by_domain(questions: list, domain: str) -> list:
    if domain.lower() == 'all':
        return questions
    return [q for q in questions if domain.lower() in q.domain.lower()]


def get_weak_spots(questions: list, progress: Progress) -> list:
    """Return questions the user has gotten wrong, sorted by worst accuracy."""
    weak = []
    for q in questions:
        stats = progress.question_stats.get(str(q.number))
        if stats and stats['seen'] > stats['correct']:
            weak.append(q)
    # Sort by accuracy ascending (worst first)
    weak.sort(key=lambda q: progress.question_stats[str(q.number)]['correct']
              / progress.question_stats[str(q.number)]['seen'])
    return weak


def show_menu(questions: list, progress: Progress) -> str:
    clear_screen()
    print_header()
    print_stats(progress, len(questions))

    weak_count = len(get_weak_spots(questions, progress))

    print(colorize("MENU:", Colors.BOLD))
    print("  1. Start quiz (random order)")
    print("  2. Start quiz (sequential)")
    print("  3. Resume from last position")
    print("  4. Filter by domain/topic")
    print(f"  5. Weak spots ({weak_count} questions)" if weak_count else
          "  5. Weak spots (none yet)")
    print("  6. View statistics")
    print("  7. Reset progress")
    print("  q. Quit")
    print()

    return input(colorize("Choose option: ", Colors.YELLOW)).strip()


def show_domain_menu(questions: list):
    domains = get_domains(questions)

    clear_screen()
    print_header()
    print(colorize("SELECT DOMAIN/TOPIC:", Colors.BOLD))
    print()
    print("  0. All domains")
    for i, domain in enumerate(domains, 1):
        count = len([q for q in questions if domain in q.domain])
        print(f"  {i}. {domain} ({count} questions)")
    print()
    print("  b. Back to menu")
    print()

    choice = input(colorize("Choose domain: ", Colors.YELLOW)).strip()

    if choice == 'b':
        return None

    try:
        idx = int(choice)
        if idx == 0:
            return 'all'
        if 1 <= idx <= len(domains):
            return domains[idx - 1]
    except ValueError:
        pass

    return None


def show_statistics(questions: list, progress: Progress):
    clear_screen()
    print_header()
    print(colorize("STATISTICS", Colors.BOLD))
    print(colorize("─" * 62, Colors.DIM))
    print()

    print(f"Total questions available: {len(questions)}")
    print(f"Questions attempted: {progress.questions_answered}")
    print(f"Correct answers: {progress.correct_answers}")

    if progress.questions_answered > 0:
        pct = progress.correct_answers / progress.questions_answered * 100
        print(f"Success rate: {pct:.1f}%")

    print()
    print(colorize("BY DOMAIN:", Colors.BOLD))
    domains = get_domains(questions)
    for domain in domains:
        domain_qs = [q for q in questions if domain in q.domain]
        attempted = sum(1 for q in domain_qs if str(q.number) in progress.question_stats)
        correct = sum(progress.question_stats.get(str(q.number), {}).get('correct', 0)
                     for q in domain_qs)
        print(f"  {domain}: {attempted}/{len(domain_qs)} attempted, {correct} correct")

    print()
    print(colorize("Last session: ", Colors.DIM) + (progress.last_session or "Never"))
    print()
    input(colorize("Press Enter to continue...", Colors.DIM))


def run_quiz(questions: list, progress: Progress, progress_file: str,
             randomize: bool = True, start_index: int = 0):
    if not questions:
        print(colorize("No questions available!", Colors.RED))
        input("Press Enter to continue...")
        return

    quiz_questions = questions.copy()
    if randomize:
        random.shuffle(quiz_questions)
    else:
        quiz_questions = quiz_questions[start_index:]

    progress.current_session_correct = 0
    progress.current_session_total = 0

    for i, question in enumerate(quiz_questions):
        clear_screen()
        print_header()
        print_stats(progress, len(questions))

        display_question(question, i, len(quiz_questions))

        # Get valid options
        valid_options = set(question.options.keys())
        valid_options_str = '/'.join(sorted(valid_options))
        multi = is_multi_select(question)

        if multi > 1:
            print(colorize(f"Select {multi} answers (e.g. AB), 'q' to quit, 's' to skip:", Colors.DIM))
        else:
            print(colorize(f"Enter your answer ({valid_options_str}), 'q' to quit, 's' to skip:", Colors.DIM))
        print()

        while True:
            user_input = input(colorize("Your answer: ", Colors.YELLOW)).strip().upper()

            if user_input == 'Q':
                save_progress(progress, progress_file)
                return

            if user_input == 'S':
                break

            # Normalize input: remove separators like commas, spaces
            cleaned = re.sub(r'[\s,/]+', '', user_input)

            if multi > 1:
                # Multi-select: need exactly `multi` unique valid letters
                letters = list(dict.fromkeys(cleaned))  # unique, preserve order
                if len(letters) == multi and all(l in valid_options for l in letters):
                    user_answer = ''.join(letters)
                    is_correct = set(user_answer) == set(question.correct_answer)

                    progress.current_session_total += 1
                    progress.questions_answered += 1
                    progress.last_question_index = i

                    q_key = str(question.number)
                    if q_key not in progress.question_stats:
                        progress.question_stats[q_key] = {'seen': 0, 'correct': 0}
                    progress.question_stats[q_key]['seen'] += 1

                    if is_correct:
                        progress.current_session_correct += 1
                        progress.correct_answers += 1
                        progress.question_stats[q_key]['correct'] += 1

                    display_result(question, user_answer, is_correct)

                    save_progress(progress, progress_file)
                    input(colorize("Press Enter for next question...", Colors.DIM))
                    break
                else:
                    print(colorize(f"Please enter exactly {multi} valid options (e.g. AB)", Colors.RED))
            else:
                if cleaned in valid_options:
                    is_correct = cleaned == question.correct_answer

                    progress.current_session_total += 1
                    progress.questions_answered += 1
                    progress.last_question_index = i

                    q_key = str(question.number)
                    if q_key not in progress.question_stats:
                        progress.question_stats[q_key] = {'seen': 0, 'correct': 0}
                    progress.question_stats[q_key]['seen'] += 1

                    if is_correct:
                        progress.current_session_correct += 1
                        progress.correct_answers += 1
                        progress.question_stats[q_key]['correct'] += 1

                    display_result(question, cleaned, is_correct)

                    save_progress(progress, progress_file)
                    input(colorize("Press Enter for next question...", Colors.DIM))
                    break
                else:
                    print(colorize(f"Invalid option. Please enter {valid_options_str}", Colors.RED))

    # Quiz complete
    clear_screen()
    print_header()
    print(colorize("QUIZ COMPLETE!", Colors.GREEN + Colors.BOLD))
    print()
    print_stats(progress, len(questions))
    print()
    input(colorize("Press Enter to continue...", Colors.DIM))


def reset_progress(progress: Progress, progress_file: str) -> Progress:
    confirm = input(colorize("Are you sure you want to reset all progress? (yes/no): ", Colors.RED))
    if confirm.lower() == 'yes':
        progress = Progress()
        save_progress(progress, progress_file)
        print(colorize("Progress reset!", Colors.GREEN))
    else:
        print(colorize("Reset cancelled.", Colors.DIM))
    input("Press Enter to continue...")
    return progress


def main():
    global _cert_name
    script_dir = Path(__file__).parent

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        arg_path = Path(arg)
        if arg_path.suffix == ".json" or arg_path.exists():
            questions_file = arg_path
        else:
            questions_file = script_dir / f"{arg}_questions.json"
    else:
        candidates = sorted(script_dir.glob("*_questions.json"))
        if len(candidates) == 1:
            questions_file = candidates[0]
        elif len(candidates) > 1:
            print(colorize("Multiple question files found. Please choose:", Colors.YELLOW))
            for i, p in enumerate(candidates, 1):
                print(f"  {i}. {p.name}")
            choice = input(colorize("Enter number: ", Colors.YELLOW)).strip()
            try:
                questions_file = candidates[int(choice) - 1]
            except (ValueError, IndexError):
                print(colorize("Invalid choice.", Colors.RED))
                sys.exit(1)
        else:
            print(colorize("Error: No *_questions.json file found in script directory.", Colors.RED))
            print("Run parse_questions.py first or pass a cert ID as argument.")
            sys.exit(1)

    questions_file = Path(questions_file)
    progress_file = progress_path_from_questions(questions_file)
    _cert_name = cert_name_from_path(questions_file)

    if not questions_file.exists():
        print(colorize(f"Error: Questions file not found: {questions_file}", Colors.RED))
        print("Run parse_questions.py first to generate the questions file.")
        sys.exit(1)

    print("Loading questions...")
    questions = load_questions(str(questions_file))
    progress = load_progress(str(progress_file))
    progress.total_questions = len(questions)

    print(f"Loaded {len(questions)} questions.")

    current_questions = questions

    while True:
        choice = show_menu(current_questions, progress)

        if choice == '1':
            run_quiz(current_questions, progress, str(progress_file), randomize=True)
        elif choice == '2':
            run_quiz(current_questions, progress, str(progress_file), randomize=False)
        elif choice == '3':
            run_quiz(current_questions, progress, str(progress_file),
                    randomize=False, start_index=progress.last_question_index)
        elif choice == '4':
            domain = show_domain_menu(questions)
            if domain:
                current_questions = filter_by_domain(questions, domain)
                if not current_questions:
                    print(colorize("No questions found for that domain.", Colors.RED))
                    current_questions = questions
                    input("Press Enter to continue...")
        elif choice == '5':
            show_statistics(questions, progress)
        elif choice == '6':
            progress = reset_progress(progress, str(progress_file))
        elif choice.lower() == 'q':
            save_progress(progress, str(progress_file))
            clear_screen()
            print(colorize("Thanks for studying! Good luck on your exam!", Colors.GREEN))
            break


if __name__ == "__main__":
    main()
