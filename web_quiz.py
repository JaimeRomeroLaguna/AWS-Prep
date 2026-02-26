#!/usr/bin/env python3
"""
AWS Certification Quiz - Web Interface
Run with: python3 web_quiz.py [port]
Then open http://localhost:5001 in your browser.
"""

import json
import os
import random
import sys
from pathlib import Path
from flask import Flask, session, redirect, url_for, request, render_template_string

# Reuse core logic from aws_quiz.py
sys.path.insert(0, str(Path(__file__).parent))
from aws_quiz import (
    load_questions, load_progress, save_progress,
    is_multi_select, get_domains, filter_by_domain,
    get_weak_spots, Progress
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-in-production")

SCRIPT_DIR = Path(__file__).parent

CERT_LIST = [
    {"id": "saa-c03", "name": "Solutions Architect Associate"},
    {"id": "sap-c02", "name": "Solutions Architect Professional"},
    {"id": "dva-c02", "name": "Developer Associate"},
    {"id": "soa-c02", "name": "SysOps Administrator Associate"},
    {"id": "dop-c02", "name": "DevOps Engineer Professional"},
    {"id": "scs-c02", "name": "Security Specialty"},
    {"id": "mls-c01", "name": "Machine Learning Specialty"},
    {"id": "ans-c01", "name": "Advanced Networking Specialty"},
]

# ---------------------------------------------------------------------------
# HTML templates (single-file, dark theme)
# ---------------------------------------------------------------------------

BASE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AWS Quiz</title>
<style>
  :root {
    --bg: #0f1117;
    --surface: #1a1d27;
    --surface2: #242736;
    --border: #2e3245;
    --text: #e2e8f0;
    --muted: #8892a4;
    --aws: #ff9900;
    --aws-dim: #c47800;
    --green: #4ade80;
    --green-dim: #166534;
    --red: #f87171;
    --red-dim: #7f1d1d;
    --blue: #60a5fa;
    --yellow: #fbbf24;
  }
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
    font-size: 17px;
    line-height: 1.6;
    min-height: 100vh;
  }
  a { color: var(--aws); text-decoration: none; }
  a:hover { text-decoration: underline; }

  .container { max-width: 820px; margin: 0 auto; padding: 24px 20px; }

  /* Header */
  .header {
    display: flex; align-items: center; gap: 12px;
    padding: 16px 20px;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    position: sticky; top: 0; z-index: 10;
  }
  .header-logo { font-size: 22px; font-weight: 700; color: var(--aws); }
  .header-sub { color: var(--muted); font-size: 14px; }
  .header-right { margin-left: auto; display: flex; gap: 12px; align-items: center; }
  .header-stat { font-size: 13px; color: var(--muted); }
  .header-stat span { color: var(--text); font-weight: 600; }

  /* Cards */
  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 20px;
  }
  .card-title {
    font-size: 13px; font-weight: 600; letter-spacing: .08em;
    text-transform: uppercase; color: var(--muted); margin-bottom: 16px;
  }

  /* Buttons */
  .btn {
    display: inline-flex; align-items: center; gap: 8px;
    padding: 10px 20px; border-radius: 8px; border: 1px solid transparent;
    font-size: 15px; font-weight: 500; cursor: pointer;
    transition: opacity .15s, transform .1s;
    text-decoration: none;
  }
  .btn:hover { opacity: .85; transform: translateY(-1px); text-decoration: none; }
  .btn:active { transform: translateY(0); }
  .btn-primary { background: var(--aws); color: #000; }
  .btn-secondary { background: var(--surface2); color: var(--text); border-color: var(--border); }
  .btn-danger { background: var(--red-dim); color: var(--red); border-color: var(--red-dim); }
  .btn-sm { padding: 6px 14px; font-size: 13px; }

  /* Menu grid */
  .menu-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  @media (max-width: 540px) { .menu-grid { grid-template-columns: 1fr; } }
  .menu-btn {
    background: var(--surface2); border: 1px solid var(--border);
    border-radius: 10px; padding: 16px 20px; cursor: pointer;
    text-align: left; color: var(--text); font-size: 15px;
    transition: border-color .15s, background .15s;
    text-decoration: none; display: block;
  }
  .menu-btn:hover { border-color: var(--aws); background: #1e2030; text-decoration: none; }
  .menu-btn-icon { font-size: 22px; margin-bottom: 6px; }
  .menu-btn-title { font-weight: 600; margin-bottom: 2px; }
  .menu-btn-desc { font-size: 13px; color: var(--muted); }

  /* Stats row */
  .stats-row {
    display: flex; gap: 16px; flex-wrap: wrap;
    padding: 16px 20px;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
  }
  .stat-box { text-align: center; }
  .stat-value { font-size: 22px; font-weight: 700; color: var(--aws); }
  .stat-label { font-size: 12px; color: var(--muted); }

  /* Progress bar */
  .progress-bar-wrap {
    background: var(--surface2); border-radius: 99px; height: 6px;
    overflow: hidden; margin-bottom: 20px;
  }
  .progress-bar-fill {
    height: 100%; background: var(--aws); border-radius: 99px;
    transition: width .4s ease;
  }

  /* Question */
  .question-meta { display: flex; gap: 10px; align-items: center; margin-bottom: 12px; flex-wrap: wrap; }
  .badge {
    font-size: 12px; font-weight: 600; padding: 3px 10px;
    border-radius: 99px; background: var(--surface2);
    border: 1px solid var(--border); color: var(--muted);
  }
  .badge-aws { color: var(--aws); border-color: var(--aws-dim); }
  .question-text { font-size: 18px; line-height: 1.7; margin-bottom: 24px; }

  /* Options */
  .options { display: flex; flex-direction: column; gap: 10px; margin-bottom: 24px; }
  .option-label {
    display: flex; align-items: flex-start; gap: 14px;
    padding: 14px 18px; border-radius: 10px;
    border: 2px solid var(--border); background: var(--surface2);
    cursor: pointer; transition: border-color .15s, background .15s;
    font-size: 16px; line-height: 1.5;
  }
  .option-label:hover { border-color: var(--aws); background: #1e2030; }
  .option-label input[type=radio],
  .option-label input[type=checkbox] { display: none; }
  .option-label.selected { border-color: var(--aws); background: #1e1a0e; }
  .option-key {
    min-width: 28px; height: 28px; border-radius: 6px;
    background: var(--surface); border: 1px solid var(--border);
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 14px; color: var(--aws); flex-shrink: 0;
    margin-top: 1px;
  }
  .option-label.selected .option-key { background: var(--aws); color: #000; border-color: var(--aws); }

  /* Result styles */
  .result-banner {
    border-radius: 10px; padding: 16px 20px; margin-bottom: 20px;
    display: flex; align-items: center; gap: 12px; font-size: 18px; font-weight: 700;
  }
  .result-correct { background: var(--green-dim); color: var(--green); border: 1px solid #166534; }
  .result-incorrect { background: var(--red-dim); color: var(--red); border: 1px solid #7f1d1d; }

  .answer-list { display: flex; flex-direction: column; gap: 8px; margin: 12px 0; }
  .answer-item {
    display: flex; align-items: flex-start; gap: 12px;
    padding: 12px 16px; border-radius: 8px;
    font-size: 15px; line-height: 1.5;
  }
  .answer-correct { background: #052e16; border: 1px solid #166534; color: #bbf7d0; }
  .answer-wrong   { background: #3b0000; border: 1px solid #7f1d1d; color: #fecaca; }
  .answer-neutral { background: var(--surface2); border: 1px solid var(--border); }

  .explanation-box {
    background: #0d1b2e; border: 1px solid #1e3a5f;
    border-radius: 10px; padding: 16px 20px; margin-top: 16px;
  }
  .explanation-title { font-size: 12px; font-weight: 700; letter-spacing: .08em;
    text-transform: uppercase; color: var(--blue); margin-bottom: 8px; }
  .explanation-text { color: #93c5fd; line-height: 1.7; font-size: 15px; }

  /* Domain list */
  .domain-list { display: flex; flex-direction: column; gap: 8px; }
  .domain-item {
    display: flex; align-items: center; justify-content: space-between;
    padding: 12px 16px; background: var(--surface2);
    border: 1px solid var(--border); border-radius: 8px;
    cursor: pointer; text-decoration: none; color: var(--text);
    transition: border-color .15s;
  }
  .domain-item:hover { border-color: var(--aws); text-decoration: none; }
  .domain-count { font-size: 13px; color: var(--muted); }

  /* Stats table */
  .stats-table { width: 100%; border-collapse: collapse; }
  .stats-table th, .stats-table td {
    padding: 10px 14px; text-align: left;
    border-bottom: 1px solid var(--border); font-size: 14px;
  }
  .stats-table th { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .07em; }
  .mini-bar-wrap { background: var(--surface2); border-radius: 99px; height: 4px; width: 80px; display: inline-block; vertical-align: middle; margin-left: 8px; }
  .mini-bar-fill { height: 100%; background: var(--aws); border-radius: 99px; }

  /* Flash messages */
  .flash { padding: 12px 16px; border-radius: 8px; margin-bottom: 16px; font-size: 14px; }
  .flash-info { background: #0d1b2e; border: 1px solid #1e3a5f; color: var(--blue); }

  /* Cert picker */
  .cert-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
  @media (max-width: 540px) { .cert-grid { grid-template-columns: 1fr; } }
  .cert-card {
    width: 100%; background: var(--surface);
    border: 2px solid var(--border); border-radius: 12px;
    padding: 20px 24px; cursor: pointer; text-align: left;
    transition: border-color .15s, background .15s; color: var(--text);
  }
  .cert-card:hover { border-color: var(--aws); background: #1e2030; }
  .cert-card.cert-available { border-color: var(--green-dim); }
  .cert-card.cert-available:hover { border-color: var(--green); }
  .cert-card-id { font-size: 18px; font-weight: 700; color: var(--aws); margin-bottom: 4px; }
  .cert-card-name { font-size: 14px; color: var(--muted); margin-bottom: 8px; }
  .cert-card-status { font-size: 12px; }
  .cert-card.cert-available .cert-card-status { color: var(--green); }
  .cert-card:not(.cert-available) .cert-card-status { color: var(--muted); }

  /* Responsive */
  @media (max-width: 540px) {
    .header { flex-wrap: wrap; }
    .question-text { font-size: 16px; }
    .option-label { font-size: 15px; padding: 12px 14px; }
  }
</style>
</head>
<body>
<div class="header">
  <div>
    <div class="header-logo">&#9729; AWS Quiz</div>
    {% if cert_name is defined and cert_name %}
    <div class="header-sub">{{ cert_name }} Exam Prep</div>
    {% endif %}
  </div>
  <div class="header-right">
    {% if session_pct is defined %}
    <div class="header-stat">Session <span>{{ session_correct }}/{{ session_total }}</span> ({{ session_pct }}%)</div>
    {% endif %}
    {% if overall_pct is defined %}
    <div class="header-stat">Overall <span>{{ overall_correct }}/{{ overall_total }}</span> ({{ overall_pct }}%)</div>
    {% endif %}
    {% if not hide_menu_btn %}
    <a href="/menu" class="btn btn-secondary btn-sm">Menu</a>
    {% endif %}
  </div>
</div>
{% block body %}{% endblock %}
</body>
</html>
"""

CERT_PICKER_TEMPLATE = BASE_TEMPLATE.replace("{% block body %}{% endblock %}", """
{% block body %}
<div class="container" style="margin-top:40px">
  <h1 style="color:var(--aws);margin-bottom:8px">AWS Certification Quiz</h1>
  <p style="color:var(--muted);margin-bottom:32px">Select a certification to get started.</p>

  <div class="cert-grid">
    {% for cert in certs %}
    <form method="post" action="/cert/select" style="display:contents">
      <input type="hidden" name="cert_id" value="{{ cert.id }}">
      <button type="submit" class="cert-card{% if cert.available %} cert-available{% endif %}">
        <div class="cert-card-id">{{ cert.id | upper }}</div>
        <div class="cert-card-name">{{ cert.name }}</div>
        <div class="cert-card-status">
          {% if cert.available %}Questions available{% else %}No questions yet{% endif %}
        </div>
      </button>
    </form>
    {% endfor %}
  </div>
</div>
{% endblock %}""")

CERT_NOT_FOUND_TEMPLATE = BASE_TEMPLATE.replace("{% block body %}{% endblock %}", """
{% block body %}
<div class="container" style="margin-top:40px;max-width:600px">
  <div style="font-size:48px;margin-bottom:16px">&#128269;</div>
  <h1 style="color:var(--red);margin-bottom:8px">Questions Not Found</h1>
  <p style="color:var(--muted);margin-bottom:24px">
    No question file found for <strong style="color:var(--text)">{{ cert_name }}</strong>.<br>
    Expected: <code style="color:var(--yellow)">{{ cert_id }}_questions.json</code>
  </p>

  {% if has_sample %}
  <div class="card" style="margin-bottom:20px">
    <div class="card-title">Sample Questions Available</div>
    <p style="color:var(--muted);margin-bottom:16px">
      A sample question file is available for {{ cert_name }}.
      Use it to explore the quiz interface.
    </p>
    <form method="post" action="/cert/use-sample">
      <input type="hidden" name="cert_id" value="{{ cert_id }}">
      <button type="submit" class="btn btn-primary">Use Sample Questions</button>
    </form>
  </div>
  {% endif %}

  <div class="card">
    <div class="card-title">Add Questions</div>
    <p style="color:var(--muted);margin-bottom:12px">Run the parser to generate a question file:</p>
    <code style="display:block;background:var(--surface2);padding:12px;border-radius:8px;color:var(--yellow);font-size:14px">make parse CERT={{ cert_id }}</code>
  </div>

  <a href="/" class="btn btn-secondary">&#8592; Back to Cert Picker</a>
</div>
{% endblock %}""")

MENU_TEMPLATE = BASE_TEMPLATE.replace("{% block body %}{% endblock %}", """
{% block body %}
<div class="container">
  {% if flash_msg %}
  <div class="flash flash-info">{{ flash_msg }}</div>
  {% endif %}

  <div class="card" style="margin-top:24px">
    <div class="card-title">Your Progress</div>
    <div style="display:flex;gap:32px;flex-wrap:wrap">
      <div class="stat-box"><div class="stat-value">{{ total_q }}</div><div class="stat-label">Questions</div></div>
      <div class="stat-box"><div class="stat-value">{{ answered }}</div><div class="stat-label">Attempted</div></div>
      <div class="stat-box"><div class="stat-value">{{ correct }}</div><div class="stat-label">Correct</div></div>
      <div class="stat-box"><div class="stat-value">{{ pct }}%</div><div class="stat-label">Accuracy</div></div>
      <div class="stat-box"><div class="stat-value" style="color:var(--red)">{{ weak }}</div><div class="stat-label">Weak Spots</div></div>
    </div>
  </div>

  <div class="menu-grid">
    <form method="post" action="/quiz/start">
      <input type="hidden" name="mode" value="random">
      <button type="submit" class="menu-btn">
        <div class="menu-btn-icon">&#x1F3B2;</div>
        <div class="menu-btn-title">Random Quiz</div>
        <div class="menu-btn-desc">Questions in random order</div>
      </button>
    </form>
    <form method="post" action="/quiz/start">
      <input type="hidden" name="mode" value="sequential">
      <button type="submit" class="menu-btn">
        <div class="menu-btn-icon">&#x1F4CB;</div>
        <div class="menu-btn-title">Sequential</div>
        <div class="menu-btn-desc">Questions in original order</div>
      </button>
    </form>
    <form method="post" action="/quiz/start">
      <input type="hidden" name="mode" value="resume">
      <button type="submit" class="menu-btn">
        <div class="menu-btn-icon">&#x23ED;&#xFE0F;</div>
        <div class="menu-btn-title">Resume</div>
        <div class="menu-btn-desc">Continue from last position (#{{ last_idx + 1 }})</div>
      </button>
    </form>
    <a href="/domain" class="menu-btn">
      <div class="menu-btn-icon">&#x1F4C2;</div>
      <div class="menu-btn-title">Filter by Domain</div>
      <div class="menu-btn-desc">Focus on a specific topic</div>
    </a>
    {% if weak > 0 %}
    <form method="post" action="/quiz/start">
      <input type="hidden" name="mode" value="weak">
      <button type="submit" class="menu-btn" style="border-color:var(--red-dim)">
        <div class="menu-btn-icon">&#x26A0;&#xFE0F;</div>
        <div class="menu-btn-title">Weak Spots</div>
        <div class="menu-btn-desc">{{ weak }} questions you've missed</div>
      </button>
    </form>
    {% endif %}
    <a href="/stats" class="menu-btn">
      <div class="menu-btn-icon">&#x1F4CA;</div>
      <div class="menu-btn-title">Statistics</div>
      <div class="menu-btn-desc">Detailed breakdown by domain</div>
    </a>
  </div>

  <div style="margin-top:8px;display:flex;justify-content:space-between;align-items:center">
    <a href="/" class="btn btn-secondary btn-sm">&#8592; Change Cert</a>
    <form method="post" action="/reset" onsubmit="return confirm('Reset ALL progress? This cannot be undone.')">
      <button type="submit" class="btn btn-danger btn-sm">Reset Progress</button>
    </form>
  </div>
</div>
{% endblock %}""")

DOMAIN_TEMPLATE = BASE_TEMPLATE.replace("{% block body %}{% endblock %}", """
{% block body %}
<div class="container" style="margin-top:24px">
  <h2 style="margin-bottom:16px">Filter by Domain</h2>
  <div class="domain-list">
    <form method="post" action="/quiz/start" style="display:contents">
      <input type="hidden" name="mode" value="domain">
      <input type="hidden" name="domain" value="all">
      <button type="submit" class="domain-item">
        <span>All Domains</span>
        <span class="domain-count">{{ total_q }} questions</span>
      </button>
    </form>
    {% for domain, count in domains %}
    <form method="post" action="/quiz/start" style="display:contents">
      <input type="hidden" name="mode" value="domain">
      <input type="hidden" name="domain" value="{{ domain }}">
      <button type="submit" class="domain-item">
        <span>{{ domain }}</span>
        <span class="domain-count">{{ count }} questions</span>
      </button>
    </form>
    {% endfor %}
  </div>
  <div style="margin-top:16px"><a href="/menu" class="btn btn-secondary">&#8592; Back</a></div>
</div>
{% endblock %}""")

QUESTION_TEMPLATE = BASE_TEMPLATE.replace("{% block body %}{% endblock %}", """
{% block body %}
<div class="progress-bar-wrap" style="border-radius:0;margin-bottom:0;height:4px">
  <div class="progress-bar-fill" style="width:{{ progress_pct }}%"></div>
</div>
<div class="container" style="margin-top:20px">
  <div class="question-meta">
    <span class="badge badge-aws">Q{{ q_number }}</span>
    <span class="badge">{{ idx + 1 }} / {{ total }}</span>
    {% if domain %}<span class="badge">{{ domain }}</span>{% endif %}
    {% if multi > 1 %}<span class="badge" style="color:var(--yellow);border-color:var(--yellow)">Select {{ multi }}</span>{% endif %}
  </div>

  <div class="question-text">{{ question_text }}</div>

  <form method="post" action="/quiz/answer" id="quiz-form">
    <input type="hidden" name="q_number" value="{{ q_number }}">
    <div class="options">
      {% for letter, text in options %}
      <label class="option-label" id="opt-{{ letter }}">
        {% if multi > 1 %}
        <input type="checkbox" name="answer" value="{{ letter }}" onchange="updateSelected(this)">
        {% else %}
        <input type="radio" name="answer" value="{{ letter }}" onchange="autoSubmit()">
        {% endif %}
        <span class="option-key">{{ letter }}</span>
        <span>{{ text }}</span>
      </label>
      {% endfor %}
    </div>
    {% if multi > 1 %}
    <button type="submit" class="btn btn-primary" id="submit-btn" disabled>Submit {{ multi }} Answers</button>
    {% endif %}
  </form>

  <div style="margin-top:20px;display:flex;gap:10px">
    <a href="/quiz/skip" class="btn btn-secondary btn-sm">Skip</a>
    <a href="/menu" class="btn btn-secondary btn-sm">&#x1F3E0; Menu</a>
  </div>
</div>

<script>
{% if multi > 1 %}
function updateSelected(el) {
  var checked = document.querySelectorAll('input[type=checkbox]:checked');
  document.querySelectorAll('.option-label').forEach(function(l) {
    var cb = l.querySelector('input[type=checkbox]');
    l.classList.toggle('selected', cb && cb.checked);
  });
  var btn = document.getElementById('submit-btn');
  btn.disabled = (checked.length !== {{ multi }});
  btn.textContent = checked.length < {{ multi }}
    ? 'Select ' + ({{ multi }} - checked.length) + ' more'
    : 'Submit {{ multi }} Answers';
}
{% else %}
function autoSubmit() {
  document.querySelectorAll('.option-label').forEach(function(l) {
    var r = l.querySelector('input[type=radio]');
    l.classList.toggle('selected', r && r.checked);
  });
  setTimeout(function(){ document.getElementById('quiz-form').submit(); }, 180);
}
{% endif %}
</script>
{% endblock %}""")

RESULT_TEMPLATE = BASE_TEMPLATE.replace("{% block body %}{% endblock %}", """
{% block body %}
<div class="progress-bar-wrap" style="border-radius:0;margin-bottom:0;height:4px">
  <div class="progress-bar-fill" style="width:{{ progress_pct }}%"></div>
</div>
<div class="container" style="margin-top:20px">
  <div class="result-banner {{ 'result-correct' if is_correct else 'result-incorrect' }}">
    {{ '✓ Correct!' if is_correct else '✗ Incorrect' }}
  </div>

  <div class="card">
    <div class="card-title">Question {{ q_number }}</div>
    <div style="font-size:16px;line-height:1.7;color:var(--muted);margin-bottom:16px">{{ question_text }}</div>

    <div class="answer-list">
      {% for letter, text in options %}
      <div class="answer-item
        {% if letter in correct_set %}answer-correct
        {% elif letter in user_set and letter not in correct_set %}answer-wrong
        {% else %}answer-neutral{% endif %}">
        <span style="font-weight:700;min-width:20px">{{ letter }}.</span>
        <span>{{ text }}</span>
        {% if letter in correct_set %}<span style="margin-left:auto;font-size:13px">&#10003; correct</span>{% endif %}
        {% if letter in user_set and letter not in correct_set %}<span style="margin-left:auto;font-size:13px">&#10007; your pick</span>{% endif %}
      </div>
      {% endfor %}
    </div>

    {% if explanation %}
    <div class="explanation-box">
      <div class="explanation-title">Explanation</div>
      <div class="explanation-text">{{ explanation }}</div>
    </div>
    {% endif %}
  </div>

  <div style="display:flex;gap:10px">
    <a href="/quiz/next" class="btn btn-primary">Next Question &#8594;</a>
    <a href="/menu" class="btn btn-secondary">&#x1F3E0; Menu</a>
  </div>
</div>
{% endblock %}""")

COMPLETE_TEMPLATE = BASE_TEMPLATE.replace("{% block body %}{% endblock %}", """
{% block body %}
<div class="container" style="margin-top:40px;text-align:center">
  <div style="font-size:48px;margin-bottom:16px">&#127881;</div>
  <h1 style="color:var(--aws);margin-bottom:8px">Quiz Complete!</h1>
  <p style="color:var(--muted);margin-bottom:32px">You finished all questions in this set.</p>
  <div style="display:flex;gap:32px;justify-content:center;margin-bottom:32px;flex-wrap:wrap">
    <div class="stat-box"><div class="stat-value">{{ session_correct }}</div><div class="stat-label">Correct (session)</div></div>
    <div class="stat-box"><div class="stat-value">{{ session_total }}</div><div class="stat-label">Answered</div></div>
    <div class="stat-box"><div class="stat-value">{{ pct }}%</div><div class="stat-label">Accuracy</div></div>
  </div>
  <a href="/menu" class="btn btn-primary">Back to Menu</a>
</div>
{% endblock %}""")

STATS_TEMPLATE = BASE_TEMPLATE.replace("{% block body %}{% endblock %}", """
{% block body %}
<div class="container" style="margin-top:24px">
  <h2 style="margin-bottom:20px">Statistics</h2>

  <div class="card">
    <div class="card-title">Overall</div>
    <div style="display:flex;gap:32px;flex-wrap:wrap">
      <div class="stat-box"><div class="stat-value">{{ total_q }}</div><div class="stat-label">Total Questions</div></div>
      <div class="stat-box"><div class="stat-value">{{ answered }}</div><div class="stat-label">Attempted</div></div>
      <div class="stat-box"><div class="stat-value">{{ correct }}</div><div class="stat-label">Correct</div></div>
      <div class="stat-box"><div class="stat-value">{{ pct }}%</div><div class="stat-label">Accuracy</div></div>
    </div>
  </div>

  <div class="card">
    <div class="card-title">By Domain</div>
    <table class="stats-table">
      <thead><tr><th>Domain</th><th>Attempted</th><th>Correct</th><th>Accuracy</th></tr></thead>
      <tbody>
        {% for row in domain_stats %}
        <tr>
          <td>{{ row.domain }}</td>
          <td>{{ row.attempted }}/{{ row.total }}</td>
          <td>{{ row.correct }}</td>
          <td>
            {{ row.pct }}%
            <span class="mini-bar-wrap"><span class="mini-bar-fill" style="width:{{ row.pct }}%"></span></span>
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

  {% if last_session %}
  <p style="color:var(--muted);font-size:13px">Last session: {{ last_session }}</p>
  {% endif %}

  <div style="margin-top:16px"><a href="/menu" class="btn btn-secondary">&#8592; Back</a></div>
</div>
{% endblock %}""")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def files_for_cert(cert_id: str):
    """Return (questions_path, progress_path) for a given cert ID."""
    questions_path = SCRIPT_DIR / f"{cert_id}_questions.json"
    progress_path = SCRIPT_DIR / f".{cert_id}_progress.json"
    return questions_path, progress_path


def get_progress_ctx(progress: Progress, questions: list) -> dict:
    """Build common template context vars for header stats."""
    s_pct = round(progress.current_session_correct / progress.current_session_total * 100
                  if progress.current_session_total > 0 else 0)
    o_pct = round(progress.correct_answers / progress.questions_answered * 100
                  if progress.questions_answered > 0 else 0)
    cert_id = session.get("cert_id", "")
    return dict(
        cert_name=cert_id.upper(),
        session_correct=progress.current_session_correct,
        session_total=progress.current_session_total,
        session_pct=s_pct,
        overall_correct=progress.correct_answers,
        overall_total=progress.questions_answered,
        overall_pct=o_pct,
    )


def load_all():
    """Load questions and progress for the cert in the current session."""
    cert_id = session.get("cert_id", "")
    if not cert_id:
        return None, None
    questions_path, progress_path = files_for_cert(cert_id)
    # Allow sample file override stored in session
    questions_override = session.get("questions_file")
    if questions_override:
        questions_path = Path(questions_override)
    try:
        questions = load_questions(str(questions_path))
    except Exception:
        return None, None
    progress = load_progress(str(progress_path))
    return questions, progress


def _require_cert():
    """Return cert_id from session, or None to signal a redirect is needed."""
    return session.get("cert_id")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def cert_picker():
    certs = []
    for c in CERT_LIST:
        questions_path, _ = files_for_cert(c["id"])
        certs.append({**c, "available": questions_path.exists()})
    return render_template_string(CERT_PICKER_TEMPLATE, certs=certs, hide_menu_btn=True)


@app.route("/cert/select", methods=["POST"])
def cert_select():
    cert_id = request.form.get("cert_id", "").strip().lower()
    if not cert_id:
        return redirect(url_for("cert_picker"))
    questions_path, _ = files_for_cert(cert_id)
    if questions_path.exists():
        session["cert_id"] = cert_id
        session.pop("questions_file", None)
        return redirect(url_for("menu"))
    sample_path = SCRIPT_DIR / f"{cert_id}_questions.sample.json"
    return render_template_string(
        CERT_NOT_FOUND_TEMPLATE,
        cert_id=cert_id,
        cert_name=cert_id.upper(),
        has_sample=sample_path.exists(),
        hide_menu_btn=True,
    )


@app.route("/cert/use-sample", methods=["POST"])
def cert_use_sample():
    cert_id = request.form.get("cert_id", "").strip().lower()
    sample_path = SCRIPT_DIR / f"{cert_id}_questions.sample.json"
    if not sample_path.exists():
        return redirect(url_for("cert_picker"))
    session["cert_id"] = cert_id
    session["questions_file"] = str(sample_path)
    return redirect(url_for("menu"))


@app.route("/menu")
def menu():
    if not _require_cert():
        return redirect(url_for("cert_picker"))
    questions, progress = load_all()
    if questions is None:
        return redirect(url_for("cert_picker"))
    weak = len(get_weak_spots(questions, progress))
    pct = round(progress.correct_answers / progress.questions_answered * 100
                if progress.questions_answered > 0 else 0)
    ctx = get_progress_ctx(progress, questions)
    ctx.update(
        total_q=len(questions),
        answered=progress.questions_answered,
        correct=progress.correct_answers,
        pct=pct,
        weak=weak,
        last_idx=progress.last_question_index,
        flash_msg=session.pop("flash_msg", None),
    )
    return render_template_string(MENU_TEMPLATE, **ctx)


@app.route("/domain")
def domain_page():
    if not _require_cert():
        return redirect(url_for("cert_picker"))
    questions, progress = load_all()
    if questions is None:
        return redirect(url_for("cert_picker"))
    domains = get_domains(questions)
    domain_list = [(d, len([q for q in questions if d in q.domain])) for d in domains]
    ctx = get_progress_ctx(progress, questions)
    ctx.update(domains=domain_list, total_q=len(questions))
    return render_template_string(DOMAIN_TEMPLATE, **ctx)


@app.route("/quiz/start", methods=["POST"])
def quiz_start():
    if not _require_cert():
        return redirect(url_for("cert_picker"))
    questions, progress = load_all()
    if questions is None:
        return redirect(url_for("cert_picker"))
    mode = request.form.get("mode", "random")
    domain = request.form.get("domain", "all")

    _, progress_path = files_for_cert(session["cert_id"])

    # Reset session quiz state
    progress.current_session_correct = 0
    progress.current_session_total = 0
    save_progress(progress, str(progress_path))

    if mode == "random":
        q_list = questions.copy()
        random.shuffle(q_list)
    elif mode == "sequential":
        q_list = questions.copy()
    elif mode == "resume":
        idx = progress.last_question_index
        q_list = questions[idx:]
    elif mode == "weak":
        q_list = get_weak_spots(questions, progress)
    elif mode == "domain":
        q_list = filter_by_domain(questions, domain)
        if not q_list:
            session["flash_msg"] = f"No questions found for domain: {domain}"
            return redirect(url_for("menu"))
        random.shuffle(q_list)
    else:
        q_list = questions.copy()

    if not q_list:
        session["flash_msg"] = "No questions available for that selection."
        return redirect(url_for("menu"))

    session["quiz_indices"] = [q.number for q in q_list]
    session["quiz_pos"] = 0
    session["last_result"] = None
    return redirect(url_for("quiz_question"))


@app.route("/quiz")
def quiz_question():
    if not _require_cert() or "quiz_indices" not in session:
        return redirect(url_for("cert_picker"))

    questions, progress = load_all()
    if questions is None:
        return redirect(url_for("cert_picker"))
    q_map = {q.number: q for q in questions}

    indices = session["quiz_indices"]
    pos = session.get("quiz_pos", 0)

    if pos >= len(indices):
        return redirect(url_for("quiz_complete"))

    q = q_map.get(indices[pos])
    if not q:
        return redirect(url_for("menu"))

    multi = is_multi_select(q)
    progress_pct = round(pos / len(indices) * 100)
    ctx = get_progress_ctx(progress, questions)
    ctx.update(
        q_number=q.number,
        question_text=q.text,
        options=sorted(q.options.items()),
        domain=q.domain,
        multi=multi,
        idx=pos,
        total=len(indices),
        progress_pct=progress_pct,
    )
    return render_template_string(QUESTION_TEMPLATE, **ctx)


@app.route("/quiz/answer", methods=["POST"])
def quiz_answer():
    if not _require_cert() or "quiz_indices" not in session:
        return redirect(url_for("cert_picker"))

    questions, progress = load_all()
    if questions is None:
        return redirect(url_for("cert_picker"))
    q_map = {q.number: q for q in questions}

    q_number = int(request.form.get("q_number", 0))
    q = q_map.get(q_number)
    if not q:
        return redirect(url_for("menu"))

    raw_answers = request.form.getlist("answer")
    multi = is_multi_select(q)

    if multi > 1:
        user_answer_set = set(raw_answers)
        is_correct = user_answer_set == set(q.correct_answer)
    else:
        user_answer_set = set(raw_answers[:1])
        is_correct = raw_answers[0] == q.correct_answer if raw_answers else False

    # Update progress
    q_key = str(q.number)
    if q_key not in progress.question_stats:
        progress.question_stats[q_key] = {"seen": 0, "correct": 0}
    progress.question_stats[q_key]["seen"] += 1
    progress.current_session_total += 1
    progress.questions_answered += 1
    progress.last_question_index = session.get("quiz_pos", 0)

    if is_correct:
        progress.question_stats[q_key]["correct"] += 1
        progress.current_session_correct += 1
        progress.correct_answers += 1

    _, progress_path = files_for_cert(session["cert_id"])
    save_progress(progress, str(progress_path))

    # Determine correct set
    if multi > 1:
        correct_set = set(q.correct_answer)
    else:
        correct_set = {q.correct_answer}

    pos = session.get("quiz_pos", 0)
    indices = session["quiz_indices"]
    progress_pct = round(pos / len(indices) * 100)

    ctx = get_progress_ctx(progress, questions)
    ctx.update(
        q_number=q.number,
        question_text=q.text,
        options=sorted(q.options.items()),
        is_correct=is_correct,
        user_set=user_answer_set,
        correct_set=correct_set,
        explanation=q.explanation,
        idx=pos,
        total=len(indices),
        progress_pct=progress_pct,
    )
    return render_template_string(RESULT_TEMPLATE, **ctx)


@app.route("/quiz/next")
def quiz_next():
    if "quiz_indices" not in session:
        return redirect(url_for("menu"))
    session["quiz_pos"] = session.get("quiz_pos", 0) + 1
    return redirect(url_for("quiz_question"))


@app.route("/quiz/skip")
def quiz_skip():
    if "quiz_indices" not in session:
        return redirect(url_for("menu"))
    session["quiz_pos"] = session.get("quiz_pos", 0) + 1
    return redirect(url_for("quiz_question"))


@app.route("/quiz/complete")
def quiz_complete():
    if not _require_cert():
        return redirect(url_for("cert_picker"))
    questions, progress = load_all()
    if questions is None:
        return redirect(url_for("cert_picker"))
    pct = round(progress.current_session_correct / progress.current_session_total * 100
                if progress.current_session_total > 0 else 0)
    ctx = get_progress_ctx(progress, questions)
    ctx.update(
        session_correct=progress.current_session_correct,
        session_total=progress.current_session_total,
        pct=pct,
    )
    return render_template_string(COMPLETE_TEMPLATE, **ctx)


@app.route("/stats")
def stats():
    if not _require_cert():
        return redirect(url_for("cert_picker"))
    questions, progress = load_all()
    if questions is None:
        return redirect(url_for("cert_picker"))
    domains = get_domains(questions)
    domain_stats = []
    for domain in domains:
        dqs = [q for q in questions if domain in q.domain]
        attempted = sum(1 for q in dqs if str(q.number) in progress.question_stats)
        correct = sum(progress.question_stats.get(str(q.number), {}).get("correct", 0) for q in dqs)
        pct = round(correct / attempted * 100 if attempted > 0 else 0)
        domain_stats.append(dict(domain=domain, total=len(dqs),
                                 attempted=attempted, correct=correct, pct=pct))

    overall_pct = round(progress.correct_answers / progress.questions_answered * 100
                        if progress.questions_answered > 0 else 0)
    ctx = get_progress_ctx(progress, questions)
    ctx.update(
        total_q=len(questions),
        answered=progress.questions_answered,
        correct=progress.correct_answers,
        pct=overall_pct,
        domain_stats=domain_stats,
        last_session=progress.last_session,
    )
    return render_template_string(STATS_TEMPLATE, **ctx)


@app.route("/reset", methods=["POST"])
def reset():
    cert_id = session.get("cert_id", "")
    _, progress_path = files_for_cert(cert_id)
    progress = Progress()
    save_progress(progress, str(progress_path))
    session.clear()
    session["cert_id"] = cert_id
    session["flash_msg"] = "Progress has been reset."
    return redirect(url_for("menu"))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    print(f"Starting AWS Quiz web server at http://localhost:{port}")
    print("Press Ctrl+C to stop.")
    app.run(debug=False, port=port)
