#!/usr/bin/env python3
"""Tests for AWS quiz application."""

import json
import re
import unittest
from pathlib import Path
from unittest.mock import patch

from aws_quiz import Question, is_multi_select, display_result
from parse_questions import (
    is_multi_select as parser_is_multi_select,
    extract_multi_answers,
)

QUESTIONS_FILE = Path(__file__).parent / "aws_questions.json"


def make_question(text="Sample question?", correct_answer="A", options=None):
    """Helper to build a Question with sensible defaults."""
    if options is None:
        options = {"A": "Option A", "B": "Option B", "C": "Option C", "D": "Option D"}
    return Question(
        number=1, text=text, options=options,
        correct_answer=correct_answer, explanation="Explanation."
    )


# ---------------------------------------------------------------------------
# Parser: is_multi_select
# ---------------------------------------------------------------------------
class TestParserIsMultiSelect(unittest.TestCase):
    def test_choose_two(self):
        self.assertEqual(parser_is_multi_select("Which two? (Choose two.)"), 2)

    def test_choose_two_case_insensitive(self):
        self.assertEqual(parser_is_multi_select("pick options (choose two.)"), 2)

    def test_single_select(self):
        self.assertEqual(parser_is_multi_select("Which is correct?"), 1)


# ---------------------------------------------------------------------------
# Parser: extract_multi_answers
# ---------------------------------------------------------------------------
class TestExtractMultiAnswers(unittest.TestCase):
    def test_two_answers(self):
        block = (
            "Some question text\n"
            "A. First correct answer\n"
            "B. Second correct answer\n"
            "\nExplanation text..."
        )
        self.assertEqual(extract_multi_answers(block, 2), "AB")

    def test_non_consecutive_letters(self):
        block = (
            "Question...\n"
            "B. Answer B\n"
            "E. Answer E\n"
            "\nExplanation..."
        )
        self.assertEqual(extract_multi_answers(block, 2), "BE")

    def test_deduplicates_letters(self):
        block = (
            "A. Answer A\n"
            "\n"
            "A. Repeated explanation for A\n"
            "C. Answer C\n"
        )
        self.assertEqual(extract_multi_answers(block, 2), "AC")

    def test_returns_none_when_not_enough(self):
        block = "A. Only one answer\n"
        self.assertIsNone(extract_multi_answers(block, 2))

    def test_returns_none_for_empty(self):
        self.assertIsNone(extract_multi_answers("", 2))


# ---------------------------------------------------------------------------
# Quiz: is_multi_select
# ---------------------------------------------------------------------------
class TestQuizIsMultiSelect(unittest.TestCase):
    def test_choose_two_question(self):
        q = make_question(text="Which meet requirements? (Choose two.)")
        self.assertEqual(is_multi_select(q), 2)

    def test_regular_question(self):
        q = make_question(text="Which is the best solution?")
        self.assertEqual(is_multi_select(q), 1)


# ---------------------------------------------------------------------------
# Quiz: answer validation logic (mirrors run_quiz checks)
# ---------------------------------------------------------------------------
class TestAnswerValidation(unittest.TestCase):
    """Test the answer-checking logic extracted from run_quiz."""

    @staticmethod
    def check_answer(user_input, correct_answer, multi):
        """Replicate the validation logic from run_quiz."""
        cleaned = re.sub(r'[\s,/]+', '', user_input.strip().upper())
        if multi > 1:
            letters = list(dict.fromkeys(cleaned))
            if len(letters) != multi:
                return None  # invalid input
            return set(letters) == set(correct_answer)
        else:
            return cleaned == correct_answer

    # Single-select
    def test_single_correct(self):
        self.assertTrue(self.check_answer("A", "A", 1))

    def test_single_incorrect(self):
        self.assertFalse(self.check_answer("B", "A", 1))

    def test_single_lowercase(self):
        self.assertTrue(self.check_answer("a", "A", 1))

    # Multi-select
    def test_multi_correct_same_order(self):
        self.assertTrue(self.check_answer("AB", "AB", 2))

    def test_multi_correct_reverse_order(self):
        self.assertTrue(self.check_answer("BA", "AB", 2))

    def test_multi_incorrect(self):
        self.assertFalse(self.check_answer("AC", "AB", 2))

    def test_multi_with_comma_separator(self):
        self.assertTrue(self.check_answer("A,B", "AB", 2))

    def test_multi_with_space_separator(self):
        self.assertTrue(self.check_answer("A B", "AB", 2))

    def test_multi_lowercase(self):
        self.assertTrue(self.check_answer("ab", "AB", 2))

    def test_multi_too_few_letters(self):
        self.assertIsNone(self.check_answer("A", "AB", 2))

    def test_multi_too_many_letters(self):
        self.assertIsNone(self.check_answer("ABC", "AB", 2))

    def test_multi_duplicate_letter_rejected(self):
        self.assertIsNone(self.check_answer("AA", "AB", 2))


# ---------------------------------------------------------------------------
# Quiz: display_result (smoke test — just verify no crash)
# ---------------------------------------------------------------------------
class TestDisplayResult(unittest.TestCase):
    @patch("builtins.print")
    def test_single_correct(self, _mock_print):
        q = make_question(correct_answer="A")
        display_result(q, "A", True)

    @patch("builtins.print")
    def test_single_incorrect(self, _mock_print):
        q = make_question(correct_answer="A")
        display_result(q, "B", False)

    @patch("builtins.print")
    def test_multi_correct(self, _mock_print):
        q = make_question(
            text="Pick two (Choose two.)", correct_answer="AB",
            options={"A": "A", "B": "B", "C": "C", "D": "D", "E": "E"},
        )
        display_result(q, "AB", True)

    @patch("builtins.print")
    def test_multi_incorrect(self, _mock_print):
        q = make_question(
            text="Pick two (Choose two.)", correct_answer="AB",
            options={"A": "A", "B": "B", "C": "C", "D": "D", "E": "E"},
        )
        display_result(q, "AC", False)


# ---------------------------------------------------------------------------
# Integration: validate aws_questions.json
# ---------------------------------------------------------------------------
@unittest.skipUnless(QUESTIONS_FILE.exists(), "aws_questions.json not found")
class TestQuestionsJson(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(QUESTIONS_FILE) as f:
            cls.data = json.load(f)

    def test_has_questions(self):
        self.assertGreater(len(self.data), 400)

    def test_all_correct_answers_reference_valid_options(self):
        for q in self.data:
            for letter in q["correct_answer"]:
                self.assertIn(
                    letter, q["options"],
                    f"Q{q['number']}: answer '{letter}' not in options"
                )

    def test_choose_two_have_two_answers(self):
        choose_two = [q for q in self.data if "Choose two" in q["question"]]
        self.assertGreater(len(choose_two), 0, "No 'Choose two' questions found")
        for q in choose_two:
            self.assertEqual(
                len(q["correct_answer"]), 2,
                f"Q{q['number']}: expected 2-letter answer, got '{q['correct_answer']}'"
            )

    def test_single_select_have_one_answer(self):
        single = [q for q in self.data
                   if "Choose two" not in q["question"]
                   and "Choose three" not in q["question"]]
        for q in single:
            self.assertEqual(
                len(q["correct_answer"]), 1,
                f"Q{q['number']}: expected 1-letter answer, got '{q['correct_answer']}'"
            )


if __name__ == "__main__":
    unittest.main()
