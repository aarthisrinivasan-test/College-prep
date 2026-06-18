"""
Ivy League College Prep App
Powered by Claude (via Docusign LLM Hub)
"""
import os
import json
import uuid
import base64
from pathlib import Path
from flask import Flask, request, jsonify, render_template, session
import anthropic

# ── Config ──────────────────────────────────────────────────────────────────
BASE_URL   = "https://llm-hub.docusignhq.com"
AUTH_TOKEN = os.environ.get("AUTH_TOKEN", "sk-cCSOahbAROLBKWb23Dtp2A")
MODEL      = "claude-sonnet-4-6"
UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
app.secret_key = "ivy-prep-secret-key-2026"

client = anthropic.Anthropic(
    api_key=AUTH_TOKEN,
    base_url=BASE_URL,
)

# ── Ivy League context ───────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are an elite college admissions consultant with a data-driven,
personalized approach. Your mission is to empower students to reach their ultimate
potential and gain admission to the world's most competitive universities.

You have deep expertise in:
- Ivy League admissions (Harvard, Yale, Princeton, Columbia, UPenn, Dartmouth, Brown, Cornell)
- Near-Ivy schools (MIT, Stanford, Duke, Northwestern, Georgetown, Johns Hopkins, Vanderbilt)
- Extracurricular strategy, capstone projects, competition pipelines
- Major selection aligned with student strengths and career goals
- Grade-by-grade roadmaps (9th through 12th)

You use the actual course catalogs and program offerings from Ivy League schools.
Be specific, actionable, and data-driven. Always reference real programs, courses,
and opportunities at specific schools.

When assessing admission probability, use realistic ranges based on GPA, test scores,
extracurriculars, and demonstrated interest. Be honest but encouraging.

Format your responses in clean HTML using Tailwind CSS classes for beautiful rendering."""

QUIZ_QUESTIONS = [
    {
        "id": "q1",
        "text": "When you encounter a challenging problem, your first instinct is to:",
        "options": [
            {"value": "analytical", "label": "Break it into parts and analyze systematically"},
            {"value": "creative",   "label": "Brainstorm unconventional solutions"},
            {"value": "social",     "label": "Discuss it with others to gather perspectives"},
            {"value": "practical",  "label": "Find what's worked before and adapt it"},
        ]
    },
    {
        "id": "q2",
        "text": "Which subject energizes you the most?",
        "options": [
            {"value": "stem",       "label": "Math, Science, or Computer Science"},
            {"value": "humanities", "label": "English, History, or Philosophy"},
            {"value": "business",   "label": "Economics, Business, or Finance"},
            {"value": "arts",       "label": "Art, Music, Theater, or Creative Writing"},
        ]
    },
    {
        "id": "q3",
        "text": "In a group project, you naturally gravitate toward:",
        "options": [
            {"value": "leader",     "label": "Taking charge and setting direction"},
            {"value": "researcher", "label": "Digging deep into research and facts"},
            {"value": "creator",    "label": "Designing, writing, or building"},
            {"value": "connector",  "label": "Coordinating people and communication"},
        ]
    },
    {
        "id": "q4",
        "text": "What kind of impact do you most want to make in the world?",
        "options": [
            {"value": "innovation",  "label": "Invent or build something transformative"},
            {"value": "equity",      "label": "Create social change and help underserved communities"},
            {"value": "knowledge",   "label": "Advance human understanding through research"},
            {"value": "enterprise",  "label": "Build organizations that create economic value"},
        ]
    },
    {
        "id": "q5",
        "text": "Outside of school, you spend most of your free time:",
        "options": [
            {"value": "competing",  "label": "Competing in sports, debate, or academic competitions"},
            {"value": "creating",   "label": "Creating — writing, coding, art, music"},
            {"value": "leading",    "label": "Leading clubs or community organizations"},
            {"value": "exploring",  "label": "Reading, exploring ideas, or independent projects"},
        ]
    },
    {
        "id": "q6",
        "text": "When you imagine your ideal career, it looks like:",
        "options": [
            {"value": "scientist",   "label": "Researcher, doctor, engineer, or scientist"},
            {"value": "entrepreneur","label": "Founder, executive, or business leader"},
            {"value": "advocate",    "label": "Lawyer, policymaker, or social advocate"},
            {"value": "creator_pro", "label": "Author, designer, filmmaker, or artist"},
        ]
    },
    {
        "id": "q7",
        "text": "Your best work happens when you are:",
        "options": [
            {"value": "independent", "label": "Working independently with full autonomy"},
            {"value": "mentored",    "label": "Guided by an expert mentor"},
            {"value": "team",        "label": "Collaborating as part of a team"},
            {"value": "competing2",  "label": "Competing against others to push your limits"},
        ]
    },
    {
        "id": "q8",
        "text": "What do friends and teachers most often say about you?",
        "options": [
            {"value": "smart",      "label": "You're incredibly smart and analytical"},
            {"value": "creative2",  "label": "You're creative and think outside the box"},
            {"value": "driven",     "label": "You're driven and extremely hard-working"},
            {"value": "empathetic", "label": "You're empathetic and great with people"},
        ]
    },
]


# ── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    session.clear()
    return render_template("index.html")


@app.route("/api/quiz", methods=["GET"])
def get_quiz():
    return jsonify({"questions": QUIZ_QUESTIONS})


@app.route("/api/assess", methods=["POST"])
def assess():
    """Receive quiz answers + metadata, store in session."""
    data = request.json
    session["path"]    = data.get("path", "ivy")       # "ivy" or "any"
    session["grade"]   = data.get("grade", "9")
    session["answers"] = data.get("answers", {})
    session["name"]    = data.get("name", "Student")
    return jsonify({"ok": True})


@app.route("/api/upload", methods=["POST"])
def upload():
    """Accept document uploads (transcript, awards, etc.)."""
    files = request.files.getlist("files")
    saved = []
    session_id = str(uuid.uuid4())[:8]
    for f in files:
        dest = UPLOAD_DIR / f"{session_id}_{f.filename}"
        f.save(dest)
        saved.append(str(dest))
    session["uploads"] = saved
    return jsonify({"ok": True, "count": len(saved)})


@app.route("/api/analyze", methods=["POST"])
def analyze():
    """Send everything to Claude and stream back the analysis."""
    path    = session.get("path", "ivy")
    grade   = session.get("grade", "9")
    answers = session.get("answers", {})
    name    = session.get("name", "Student")
    uploads = session.get("uploads", [])

    # Build quiz summary
    q_map = {q["id"]: q for q in QUIZ_QUESTIONS}
    quiz_summary = []
    for qid, val in answers.items():
        if qid in q_map:
            q = q_map[qid]
            opt_label = next((o["label"] for o in q["options"] if o["value"] == val), val)
            quiz_summary.append(f"- {q['text']}\n  → {opt_label}")
    quiz_text = "\n".join(quiz_summary)

    # Extract text from uploaded docs
    doc_text = ""
    for fpath in uploads:
        p = Path(fpath)
        if p.exists():
            if p.suffix.lower() == ".pdf":
                try:
                    import fitz
                    doc = fitz.open(str(p))
                    for page in doc:
                        doc_text += page.get_text() + "\n"
                except Exception:
                    doc_text += f"[Could not read {p.name}]\n"
            elif p.suffix.lower() in [".txt", ".csv"]:
                doc_text += p.read_text(errors="ignore") + "\n"
            elif p.suffix.lower() in [".png", ".jpg", ".jpeg"]:
                doc_text += f"[Image uploaded: {p.name}]\n"

    # Determine goal
    goal = "gain admission to top Ivy League universities" if path == "ivy" else \
           "master subjects deeply and gain admission to excellent universities"

    prompt = f"""
You are assessing a student named {name}, currently in Grade {grade},
whose goal is to {goal}.

## Behavioral Assessment (Quiz Responses)
{quiz_text}

## Uploaded Documents
{doc_text[:4000] if doc_text else "No documents uploaded."}

Please provide a comprehensive college prep report with the following sections,
formatted beautifully in HTML with Tailwind CSS classes:

1. **Student Strengths Profile** — Based on the quiz, identify their top 3 strengths
   and 2 areas for development. Use concrete language.

2. **Predicted Career & Major Fit** — Suggest 3 most aligned majors at Ivy League
   schools. For EACH major, you MUST name the specific program at EXACTLY 2 different
   Ivy League schools (e.g., Option 1: Harvard's Computer Science AB; Option 2: Yale's
   Computer Science BS). Include 2 real course examples per school.
   Also evaluate Dartmouth's Quantitative Social Science (QSS) program as a specific
   option if the student shows any combination of analytical, social science, or
   data-driven interests. For QSS: Dartmouth requires strong math through at least
   Precalculus; Calculus is strongly preferred. Based on the uploaded transcript, assess
   whether her math grades meet this bar and note any gap or strength explicitly.

3. **Ivy League Admission Probability** — For each of the 8 Ivies + MIT/Stanford,
   give a current estimated probability range (e.g., "Harvard: 8–12% if profile
   continues trajectory") with what would most move the needle.

4. **Grade {grade} → 12th Grade Roadmap** — A year-by-year action plan covering:
   - Academic priorities and target courses
   - Extracurricular strategy (competitions, leadership, capstone)
   - Summer programs to target (name real programs: RSI, PRIMES, Wharton Pre-Biz, etc.)
   - Test prep timeline (SAT/ACT/SAT Subject, AP exams)

5. **Top 3 Immediate Action Items** — The 3 most impactful things to do THIS month.

Use this HTML structure for sections:
<div class="section-card bg-white rounded-2xl shadow-md p-6 mb-6">
  <h2 class="text-xl font-bold text-indigo-700 mb-3">Section Title</h2>
  ... content ...
</div>

Make the response highly specific, actionable, and inspiring.
Reference real Ivy League programs, courses, and opportunities.
"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    import re
    html_content = response.content[0].text.strip()
    # Strip markdown code fences Claude sometimes wraps around HTML
    html_content = re.sub(r'^```html?\s*', '', html_content)
    html_content = re.sub(r'```\s*$', '', html_content).strip()
    return jsonify({"html": html_content})


if __name__ == "__main__":
    print("\n Ivy Prep App running at http://localhost:5050\n")
    app.run(debug=True, port=5050)
