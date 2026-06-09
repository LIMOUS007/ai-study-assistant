import re
from fpdf import FPDF
from core.generator import NoteDocument, QuizDocument, FlashcardDeck, PracticePaper, LatexNotesDocument


def _clean(text: str) -> str:
    text = re.sub(r"```[\s\S]*?```", "[see in-app for code]", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", text)
    text = re.sub(r"#{1,6}\s?", "", text)
    return text.strip()


def _safe(text: str) -> str:
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _cell(pdf: FPDF, h: float, text: str):
    pdf.multi_cell(0, h, _safe(text), new_x="LMARGIN", new_y="NEXT", wrapmode="CHAR")


def _new_pdf() -> FPDF:
    pdf = FPDF()
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    return pdf


def export_notes_pdf(document: NoteDocument) -> bytes:
    pdf = _new_pdf()
    pdf.set_font("Helvetica", "B", 16)
    _cell(pdf, 10, _clean(document.title))
    pdf.ln(4)
    for section in document.sections:
        pdf.set_font("Helvetica", "B", 13)
        _cell(pdf, 8, _clean(section.heading))
        pdf.ln(1)
        pdf.set_font("Helvetica", "", 11)
        _cell(pdf, 6, _clean(section.content))
        pdf.ln(5)
    return bytes(pdf.output())


def export_quiz_pdf(document: QuizDocument) -> bytes:
    pdf = _new_pdf()
    pdf.set_font("Helvetica", "B", 16)
    _cell(pdf, 10, _clean(document.title))
    pdf.ln(4)
    for i, q in enumerate(document.questions, 1):
        pdf.set_font("Helvetica", "B", 12)
        _cell(pdf, 7, f"Q{i}. {_clean(q.question)}")
        pdf.ln(1)
        pdf.set_font("Helvetica", "", 11)
        for j, opt in enumerate(q.options):
            _cell(pdf, 6, f"  {chr(65 + j)}. {_clean(opt)}")
        pdf.ln(2)
        pdf.set_font("Helvetica", "I", 11)
        _cell(pdf, 6, f"Answer: {_clean(q.correct)}")
        _cell(pdf, 6, f"Explanation: {_clean(q.explanation)}")
        pdf.ln(5)
    return bytes(pdf.output())


def export_flashcards_pdf(deck: FlashcardDeck) -> bytes:
    pdf = _new_pdf()
    pdf.set_font("Helvetica", "B", 16)
    _cell(pdf, 10, _clean(deck.title))
    pdf.ln(4)
    for i, card in enumerate(deck.cards, 1):
        pdf.set_font("Helvetica", "B", 12)
        _cell(pdf, 7, f"{i}. {_clean(card.front)}")
        pdf.set_font("Helvetica", "", 11)
        _cell(pdf, 6, f"   {_clean(card.back)}")
        pdf.ln(3)
    return bytes(pdf.output())


def export_practice_paper_pdf(paper: PracticePaper) -> bytes:
    pdf = _new_pdf()
    pdf.set_font("Helvetica", "B", 18)
    _cell(pdf, 10, _clean(paper.course_name))
    pdf.ln(2)
    pdf.set_font("Helvetica", "I", 12)
    _cell(pdf, 7, "Practice Examination Paper")
    pdf.ln(6)

    q_num = 1
    for section in paper.sections:
        pdf.set_font("Helvetica", "B", 14)
        _cell(pdf, 9, _clean(section.section_name))
        pdf.ln(1)
        pdf.set_font("Helvetica", "I", 11)
        _cell(pdf, 6, _clean(section.instructions))
        pdf.ln(3)

        for q in section.questions:
            marks_label = f"[{q.marks} mark{'s' if q.marks != 1 else ''}]"
            pdf.set_font("Helvetica", "B", 12)
            _cell(pdf, 7, f"Q{q_num}. {_clean(q.question)}  {marks_label}")
            pdf.ln(1)
            pdf.set_font("Helvetica", "I", 11)
            _cell(pdf, 6, f"Model Answer: {_clean(q.model_answer)}")
            pdf.ln(4)
            q_num += 1

        pdf.ln(3)

    return bytes(pdf.output())


# ─── LATEX EXPORT ─────────────────────────────────────────────────────────────

_LATEX_PREAMBLE = r"""\documentclass[10pt,a4paper]{article}
\usepackage[margin=1.5cm,top=2.2cm,bottom=2cm]{geometry}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage[dvipsnames]{xcolor}
\usepackage{listings}
\usepackage{tcolorbox}
\tcbuselibrary{skins}
\usepackage{titlesec}
\usepackage{fancyhdr}
\usepackage[colorlinks=true,linkcolor=NavyBlue,urlcolor=NavyBlue]{hyperref}
\usepackage{booktabs}
\usepackage{amsmath,amssymb}
\usepackage{enumitem}
\usepackage{microtype}
\usepackage{multicol}

% Code listing style
\lstdefinestyle{examstyle}{
  basicstyle=\ttfamily\scriptsize,
  keywordstyle=\color{BrickRed}\bfseries,
  commentstyle=\color{OliveGreen}\itshape,
  stringstyle=\color{ForestGreen},
  numberstyle=\tiny\color{gray},
  numbers=left,
  numbersep=5pt,
  frame=single,
  backgroundcolor=\color{gray!8},
  rulecolor=\color{gray!35},
  breaklines=true,
  breakatwhitespace=false,
  columns=flexible,
  tabsize=4,
  showstringspaces=false,
  captionpos=b,
  xleftmargin=10pt,
  xrightmargin=2pt,
}
\lstset{style=examstyle}

% Callout boxes
\tcbset{
  exambox/.style={
    enhanced,colback=NavyBlue!6,colframe=NavyBlue,
    leftrule=3pt,toprule=0.4pt,bottomrule=0.4pt,rightrule=0.4pt,
    fonttitle=\bfseries\footnotesize,title={Exam move},
    left=4pt,right=4pt,top=3pt,bottom=3pt,
    before skip=4pt,after skip=4pt,
  },
  pitfallbox/.style={
    enhanced,colback=BrickRed!6,colframe=BrickRed,
    leftrule=3pt,toprule=0.4pt,bottomrule=0.4pt,rightrule=0.4pt,
    fonttitle=\bfseries\footnotesize,title={Pitfall},
    left=4pt,right=4pt,top=3pt,bottom=3pt,
    before skip=4pt,after skip=4pt,
  },
  tracebox/.style={
    enhanced,colback=gray!7,colframe=gray!55,
    leftrule=3pt,toprule=0.4pt,bottomrule=0.4pt,rightrule=0.4pt,
    fonttitle=\bfseries\footnotesize,
    left=4pt,right=4pt,top=3pt,bottom=3pt,
    before skip=4pt,after skip=4pt,
  },
  patternbox/.style={
    enhanced,colback=OliveGreen!6,colframe=OliveGreen,
    leftrule=3pt,toprule=0.4pt,bottomrule=0.4pt,rightrule=0.4pt,
    fonttitle=\bfseries\footnotesize,title={Pattern Recognition},
    left=4pt,right=4pt,top=3pt,bottom=3pt,
    before skip=4pt,after skip=4pt,
  },
  cmptable/.style={
    enhanced,colback=NavyBlue!4,colframe=NavyBlue!60,
    leftrule=0.4pt,toprule=2pt,bottomrule=0.4pt,rightrule=0.4pt,
    left=4pt,right=4pt,top=4pt,bottom=4pt,
    before skip=6pt,after skip=6pt,
  },
  masterbox/.style={
    enhanced,colback=Periwinkle!8,colframe=Periwinkle!70,
    leftrule=3pt,toprule=0.4pt,bottomrule=0.4pt,rightrule=0.4pt,
    fonttitle=\bfseries\footnotesize,title={Master Example},
    left=4pt,right=4pt,top=3pt,bottom=3pt,
    before skip=4pt,after skip=6pt,
  },
}

% Section headings
\titleformat{\section}
  {\large\bfseries\color{NavyBlue}}{\thesection}{0.5em}{}
  [\vspace{-3pt}\rule{\columnwidth}{0.4pt}]
\titleformat{\subsection}
  {\normalsize\bfseries\color{NavyBlue}}{\thesubsection}{0.5em}{}
\titleformat{\subsubsection}
  {\small\bfseries}{}{}{}
\titlespacing*{\section}{0pt}{10pt}{4pt}
\titlespacing*{\subsection}{0pt}{6pt}{2pt}
\titlespacing*{\subsubsection}{0pt}{4pt}{2pt}

% Layout
\setlength{\columnsep}{18pt}
\setlength{\columnseprule}{0.3pt}
\setlength{\parindent}{0pt}
\setlength{\parskip}{3pt}
\setlist{topsep=2pt,itemsep=1pt,parsep=0pt}
"""

_LANG_MAP = {
    "c++": "C++", "cpp": "C++", "c": "C",
    "python": "Python", "py": "Python",
    "java": "Java",
    "javascript": "JavaScript", "js": "JavaScript",
    "typescript": "JavaScript", "ts": "JavaScript",
    "bash": "bash", "sh": "bash",
    "sql": "SQL",
    "text": "", "plain": "", "plaintext": "",
}


def _listing_lang(lang: str) -> str:
    return _LANG_MAP.get(lang.lower().strip(), lang)


def _sanitize_code(code: str) -> str:
    """Strip/replace characters that break pdflatex inside lstlisting verbatim blocks."""
    code = (code
        .replace(' ', ' ').replace(' ', ' ').replace(' ', ' ')
        .replace('​', '').replace('⁠', '').replace('﻿', '')
        .replace('‘', "'").replace('’', "'")
        .replace('“', '"').replace('”', '"')
        .replace('–', '-').replace('—', '--').replace('…', '...')
        .replace('→', '->').replace('←', '<-').replace('⇒', '=>')
    )
    return ''.join(c if (c.isprintable() or c in '\t\n') else ' ' for c in code)


def _to_tex(text: str) -> str:
    """Escape LaTeX special chars in plain text, preserving $...$ math regions."""
    if not text:
        return ""
    # Normalize Unicode chars that T1/pdflatex cannot handle
    text = (text
        .replace(' ', ' ').replace(' ', ' ').replace(' ', ' ')
        .replace(' ', ' ').replace('​', '').replace('⁠', '').replace('﻿', '')
        .replace('‘', "'").replace('’', "'")
        .replace('“', '"').replace('”', '"')
        .replace('–', '--').replace('—', '---').replace('…', '...')
    )
    parts = re.split(r'(\$[^$\n]*?\$)', text)
    out = []
    for i, part in enumerate(parts):
        if i % 2 == 1:  # math region — keep as-is
            out.append(part)
        else:
            part = part.replace('\\', r'\textbackslash{}')
            part = part.replace('{', r'\{')
            part = part.replace('}', r'\}')
            part = part.replace('&', r'\&')
            part = part.replace('%', r'\%')
            part = part.replace('$', r'\$')
            part = part.replace('#', r'\#')
            part = part.replace('_', r'\_')
            part = part.replace('^', r'\^{}')
            part = part.replace('~', r'\textasciitilde{}')
            part = part.replace('→', r'$\rightarrow$')
            part = part.replace('⇒', r'$\Rightarrow$')
            part = part.replace('↔', r'$\leftrightarrow$')
            part = part.replace('≤', r'$\leq$')
            part = part.replace('≥', r'$\geq$')
            part = part.replace('≠', r'$\neq$')
            out.append(part)
    return ''.join(out)


def export_latex_source(doc: LatexNotesDocument) -> str:
    """Build a complete .tex source string from a LatexNotesDocument."""
    from datetime import date
    today = date.today().strftime("%B %d, %Y")

    L = [_LATEX_PREAMBLE, r"\begin{document}", ""]

    # Header/footer (set after \begin{document} so we can inject course_code)
    L += [
        r"\pagestyle{fancy}",
        r"\fancyhf{}",
        r"\fancyhead[L]{\small\textcolor{NavyBlue}{\textbf{" + _to_tex(doc.course_code) + r" --- Final Notes}}}",
        r"\fancyhead[R]{\small\thepage}",
        r"\renewcommand{\headrulewidth}{0.4pt}",
        "",
    ]

    # Cover page (single column, no header)
    L += [
        r"\thispagestyle{empty}",
        r"\begin{center}",
        r"\vspace*{3.5cm}",
        r"{\Huge\bfseries\color{NavyBlue} " + _to_tex(doc.course_name) + r"\par}",
        r"\vspace{0.6cm}",
        r"{\Large Final Exam Open-Book Notes\par}",
        r"\vspace{0.5cm}",
        r"\rule{0.6\textwidth}{0.5pt}",
        r"\vspace{0.5cm}",
        r"{\large " + _to_tex(doc.topic) + r"\par}",
        r"\vspace{3cm}",
        r"{\small\textit{Generated from course materials}\par}",
        r"\vspace{0.3cm}",
        r"{\small " + today + r"\par}",
        r"\end{center}",
        r"\newpage",
        "",
    ]

    # Table of contents (single column, roman page numbers)
    L += [
        r"\pagenumbering{roman}",
        r"\setcounter{tocdepth}{2}",
        r"\tableofcontents",
        r"\newpage",
        r"\pagenumbering{arabic}",
        "",
    ]

    # Switch to two-column for main content
    L += [r"\twocolumn", ""]

    example_n = 0
    for sec in doc.sections:
        L.append(r"\section{" + _to_tex(sec.title) + "}")
        if sec.master_example:
            L.append(r"\begin{tcolorbox}[masterbox]")
            L.append(_to_tex(sec.master_example))
            L.append(r"\end{tcolorbox}")
            L.append("")
        for sub in sec.subsections:
            L.append(r"\subsection{" + _to_tex(sub.title) + "}")

            if sub.body:
                L.append(_to_tex(sub.body))
                L.append("")

            # MCQ quick-reference facts
            if sub.mcq_facts:
                L.append(r"\begin{tabular}{@{}ll@{}}")
                for f in sub.mcq_facts:
                    L.append(r"\textbf{" + _to_tex(f.label) + r":} & " + _to_tex(f.value) + r" \\")
                L.append(r"\end{tabular}")
                L.append("")

            if sub.bullets:
                L.append(r"\begin{itemize}[leftmargin=*]")
                for b in sub.bullets:
                    L.append(r"\item " + _to_tex(b))
                L.append(r"\end{itemize}")
                L.append("")

            if sub.patterns:
                L.append(r"\begin{tcolorbox}[patternbox]")
                L.append(r"\begin{itemize}[leftmargin=*,topsep=0pt,itemsep=2pt]")
                for pt in sub.patterns:
                    L.append(
                        r"\item \textit{" + _to_tex(pt.keywords) + r"} $\Rightarrow$ "
                        + r"\textbf{" + _to_tex(pt.think) + r"}"
                    )
                L.append(r"\end{itemize}")
                L.append(r"\end{tcolorbox}")
                L.append("")

            for we in sub.worked_examples:
                example_n += 1
                L.append(
                    r"\subsubsection*{\small Example "
                    + str(example_n) + ": " + _to_tex(we.title) + "}"
                )
                if we.problem_statement:
                    L.append(r"\textit{Problem:} " + _to_tex(we.problem_statement))
                    L.append("")
                if we.answer_idea:
                    L.append(r"\textbf{Idea:} " + _to_tex(we.answer_idea))
                    L.append("")
                if we.code:
                    raw_lang = we.code.language or ""
                    if not raw_lang or raw_lang.lower() in ("text", "plain", "plaintext"):
                        code_text = we.code.code or ""
                        if any(x in code_text for x in ('#include', 'cout', 'cin', 'nullptr', 'std::')):
                            raw_lang = "C++"
                        elif 'def ' in code_text and ('print(' in code_text or 'import ' in code_text):
                            raw_lang = "Python"
                    lang = _listing_lang(raw_lang or "text")
                    opts = f"language={lang}" if lang else ""
                    if we.code.caption:
                        sep = "," if opts else ""
                        opts += f"{sep}caption={{{_to_tex(we.code.caption)}}}"
                    open_tag = r"\begin{lstlisting}" + (f"[{opts}]" if opts else "")
                    L.append(open_tag)
                    L.append(_sanitize_code(we.code.code))
                    L.append(r"\end{lstlisting}")
                if we.trace:
                    L.append(r"\textit{Trace:} " + _to_tex(we.trace))
                    L.append("")

            # Exam-style trace questions
            if sub.exam_traces:
                for et in sub.exam_traces:
                    L.append(r"\begin{tcolorbox}[tracebox]")
                    L.append(r"\textbf{Exam Q:} " + _to_tex(et.question))
                    if et.steps:
                        L.append("")
                        for step in et.steps:
                            L.append(r"\quad " + _to_tex(step) + r"\\")
                    L.append("")
                    L.append(r"\textbf{Ans:} " + _to_tex(et.answer))
                    L.append(r"\end{tcolorbox}")
                    L.append("")

            if sub.exam_moves:
                L.append(r"\begin{tcolorbox}[exambox]")
                if len(sub.exam_moves) == 1:
                    L.append(_to_tex(sub.exam_moves[0]))
                else:
                    L.append(r"\begin{itemize}[leftmargin=*,topsep=0pt,itemsep=0pt]")
                    for em in sub.exam_moves:
                        L.append(r"\item " + _to_tex(em))
                    L.append(r"\end{itemize}")
                L.append(r"\end{tcolorbox}")
                L.append("")

            if sub.pitfalls:
                L.append(r"\begin{tcolorbox}[pitfallbox]")
                if len(sub.pitfalls) == 1:
                    L.append(_to_tex(sub.pitfalls[0]))
                else:
                    L.append(r"\begin{itemize}[leftmargin=*,topsep=0pt,itemsep=0pt]")
                    for p in sub.pitfalls:
                        L.append(r"\item " + _to_tex(p))
                    L.append(r"\end{itemize}")
                L.append(r"\end{tcolorbox}")
                L.append("")

            if sub.ascii_diagrams:
                for diag in sub.ascii_diagrams:
                    L.append(r"\begin{lstlisting}[language={},numbers=none,frame=single,backgroundcolor=\color{gray!6},basicstyle=\ttfamily\scriptsize,breaklines=true,columns=fixed]")
                    L.append(_sanitize_code(diag))
                    L.append(r"\end{lstlisting}")
                L.append("")

            if sub.common_exam_questions:
                L.append(r"\subsubsection*{\small\textcolor{Mulberry}{\textbf{Common Exam Questions}}}")
                L.append(r"\begin{itemize}[leftmargin=*,topsep=0pt,itemsep=1pt]")
                for q in sub.common_exam_questions:
                    L.append(r"\item " + _to_tex(q))
                L.append(r"\end{itemize}")
                L.append("")

        if sec.comparison_table:
            ct = sec.comparison_table
            L.append(r"\begin{tcolorbox}[cmptable,title={\textbf{" + _to_tex(ct.title) + r"}}]")
            L.append(r"\begin{tabular}{@{}p{2.5cm}p{2.5cm}p{2.5cm}@{}}")
            L.append(
                r"\textbf{Feature} & \textbf{"
                + _to_tex(ct.left_label) + r"} & \textbf{"
                + _to_tex(ct.right_label) + r"} \\"
            )
            L.append(r"\hline")
            for row in ct.rows:
                L.append(
                    _to_tex(row.feature) + " & "
                    + _to_tex(row.left) + " & "
                    + _to_tex(row.right) + r" \\"
                )
            L.append(r"\end{tabular}")
            L.append(r"\end{tcolorbox}")
            L.append("")

    # Switch back to single column for tables and checklist
    L += [r"\onecolumn", ""]

    if doc.complexity_table:
        L += [
            r"\section{One-Page Complexity Sheet}",
            r"\begin{tabular}{@{}p{5.5cm}p{4cm}p{7cm}@{}}",
            r"\toprule",
            r"\textbf{Structure / Algorithm} & \textbf{Complexity} & \textbf{Reason / Reminder} \\",
            r"\midrule",
        ]
        for row in doc.complexity_table:
            L.append(
                _to_tex(row.operation) + " & "
                + _to_tex(row.complexity) + " & "
                + _to_tex(row.note) + r" \\"
            )
        L += [r"\bottomrule", r"\end{tabular}", ""]

    if doc.final_checklist:
        L += [
            r"\section{MCQ Quick Reference}",
            r"\begin{multicols}{2}",
            r"\begin{itemize}[leftmargin=*,itemsep=0pt,topsep=0pt]",
        ]
        for item in doc.final_checklist:
            L.append(r"\item " + _to_tex(item))
        L += [r"\end{itemize}", r"\end{multicols}", ""]

    L.append(r"\end{document}")
    return "\n".join(L)


def compile_latex_to_pdf(tex_source: str) -> "tuple[bytes | None, str]":
    """Try multiple remote LaTeX compilers; return (PDF bytes or None, log string)."""
    import base64
    log_lines = []

    try:
        import requests
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except ImportError:
        return None, "requests not installed"

    tex_b64 = base64.b64encode(tex_source.encode("utf-8")).decode()

    # 0. latex.vercel.app — simple JSON API
    try:
        resp = requests.post(
            "https://latex.vercel.app/",
            json={"tex": tex_source},
            timeout=60,
            verify=False,
        )
        log_lines.append(f"latex.vercel.app → HTTP {resp.status_code} | content-type: {resp.headers.get('content-type', 'n/a')} | size: {len(resp.content)} bytes")
        if resp.status_code == 200 and len(resp.content) > 1000:
            return resp.content, "\n".join(log_lines)
    except Exception as e:
        log_lines.append(f"latex.vercel.app → error: {e}")

    # 1. YtoTech — JSON + base64
    try:
        resp = requests.post(
            "https://latex.ytotech.com/builds/sync",
            json={
                "compiler": "pdflatex",
                "resources": [{"main": True, "name": "document.tex", "content": tex_b64}],
            },
            timeout=60,
            verify=False,
        )
        log_lines.append(f"YtoTech → HTTP {resp.status_code} | content-type: {resp.headers.get('content-type', 'n/a')} | size: {len(resp.content)} bytes")
        if resp.status_code == 201 and "pdf" in resp.headers.get("content-type", ""):
            return resp.content, "\n".join(log_lines)
    except Exception as e:
        log_lines.append(f"YtoTech → error: {e}")

    # 2. TeXLive.net — multipart form
    try:
        resp = requests.post(
            "https://texlive.net/cgi-bin/latexcgi",
            files={
                "filecontents[]": ("document.tex", tex_source.encode("utf-8"), "application/x-tex"),
                "filename[]": (None, "document.tex"),
                "engine": (None, "pdflatex"),
                "return": (None, "pdf"),
            },
            timeout=90,
            verify=False,
        )
        log_lines.append(f"TeXLive.net → HTTP {resp.status_code} | content-type: {resp.headers.get('content-type', 'n/a')} | size: {len(resp.content)} bytes")
        if resp.status_code == 200 and "pdf" in resp.headers.get("content-type", ""):
            return resp.content, "\n".join(log_lines)
    except Exception as e:
        log_lines.append(f"TeXLive.net → error: {e}")

    return None, "\n".join(log_lines)
