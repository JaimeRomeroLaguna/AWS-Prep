# AWS Certification Quiz Tool

A terminal and web-based multiple-choice quiz for AWS certification exam prep.
Supports any AWS certification — just drop in the right question file.

> **Note on question files:** This repo ships with a small sample question file
> for demo purposes. It does **not** include any real exam questions. You must
> supply your own `{cert_id}_questions.json` — do not add copyrighted exam dumps
> or braindump material to this repository.

---

## Getting started

```bash
# Create and activate the virtual environment
python3 -m venv venv
source venv/bin/activate
pip install flask

# Launch the web interface
make web
# Open http://localhost:5001
```

---

## Adding questions for a new cert

Questions live in files named `{cert_id}_questions.json` (e.g. `saa-c03_questions.json`).
Generate one from raw exam text with the parser:

```bash
# Raw input files expected in the project directory:
#   questions_raw.txt          — question text extracted from the PDF
#   AWS {CERT}-Solution.txt    — answers/explanations file

make parse CERT=saa-c03
# or with explicit paths:
python3 parse_questions.py --cert saa-c03 \
  --input questions_raw.txt \
  --solutions "AWS SAA-C03-Solution.txt" \
  --output saa-c03_questions.json
```

---

## The cert picker (web)

When you open `http://localhost:5001` you land on the cert picker.
It shows all 8 supported certs and highlights the ones that have a question file ready.

**If no question file is found** for a cert you click, you'll see an error page that:
- Shows the expected filename
- Offers a "Use Sample Questions" button if a `{cert_id}_questions.sample.json` file exists
- Shows the `make parse` command to generate a real file

---

## CLI usage

```bash
# Use the default (auto-discovers the only *_questions.json in the directory)
make quiz

# Specify a cert ID
make quiz CERT=saa-c03

# Or pass a file path directly
venv/bin/python3 aws_quiz.py path/to/custom_questions.json
```

---

## Progress tracking

Progress is stored per-cert in hidden files named `.{cert_id}_progress.json`
(e.g. `.saa-c03_progress.json`).

The CLI and web app share progress files, so switching between interfaces
preserves your history for each cert independently.

To wipe progress for the active cert use **Reset Progress** in the web menu,
or delete the corresponding `.{cert_id}_progress.json` file manually.
