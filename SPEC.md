# AI Study Assistant — Remaining Work Spec

Last updated: 2026-06-09.

---

## Status: What's been done

All critical bugs fixed. All priority items from the original list are complete.
Remaining items below are polish/enhancements only — nothing is broken.

---

## 1. GENERATOR QUALITY

### 1a. ~~`→` arrow breaks LaTeX compilation~~ DONE
### 1b. ~~`\midrule` inside cmptable tcolorbox~~ DONE (replaced with `\hline`)
### 1c. ~~`patternbox` uses `\texttt{}`~~ DONE (now `\textit`)
### 1d. ~~Code blocks missing language tag~~ DONE (C++/Python auto-detection)
### 1e. ~~Pattern hints too vague~~ DONE (6 concrete examples in prompt)
### 1f. ~~Exam traces capped at 1-2~~ DONE (now 3-4 with edge-case instruction)
### 1g. ~~Comparison tables rarely generated~~ DONE (REQUIRED in prompt + example)
### 1h. ~~Worked examples capped by token budget~~ DONE
Per-algorithm splitting now automatic. Known compound topics expand into
individual calls before generation:
- `"Sorting"` → Bubble, Selection, Insertion, Quick, Merge (5 calls)
- `"Trees"` → BST, Traversals, AVL (3 calls)
- `"Hashing"` → Hash Functions, Hash Tables, Open Addressing (3 calls)
- `"Recursion"` → Fundamentals, Fibonacci, Tower of Hanoi (3 calls)
- `"Linked Lists"` → SLL, DLL (2 calls)
- `"Searching"` → Linear Search, Binary Search (2 calls)
- `"Graphs"` → Representation, BFS, DFS (3 calls)

---

## 2. PDF COMPILATION

### ~~Both remote APIs failing~~ DONE
- `latex.vercel.app` added as first-choice API
- In-app PDF preview via base64 iframe when any API succeeds
- Full compilation log in `st.expander` when all APIs fail (HTTP status, size, error)

---

## 3. UI/UX

### ~~5a. No per-topic progress~~ DONE (`st.status()` with per-topic tick)
### ~~5b. API key test~~ DONE (manual Test button only; removed auto-test — it ran on every render and caused model selector to reset to top option)
### ~~5c. Model/token info lost after rerun~~ DONE (stored in session_state per course, replayed as caption on last AI message in history)
### ~~5e. Scroll button broken~~ DONE (removed useless nav-row button; auto-scroll fires via session flag after each new message send)
### ~~5d. No topic history~~ DONE (last 5 topics as quick-select chips)

---

## 4. LATEX OUTPUT

### ~~6c. No page numbers on TOC~~ DONE (roman for TOC, arabic for main)
### ~~6d. Code overflow in two-column~~ DONE (`columns=flexible` in lstset)

### 4a. Complexity table column widths (OPEN)
Single-column layout wastes space. Note column is often short.
**Fix:** Adjust widths: `p{4cm}p{3.5cm}p{9cm}` or use `\begin{multicols}{2}`.

---

## 5. STRUCTURAL FEATURES

### ~~7. Master example + ASCII diagrams + Common Exam Questions~~ DONE
All three now implemented:
- `master_example` on `LatexSection` — canonical structure used across all ops
- `ascii_diagrams` on `LatexSubsection` — ASCII art in lstlisting blocks
- `common_exam_questions` on `LatexSubsection` — 3-5 most-asked question types
Rendered in both the Streamlit preview and the LaTeX/PDF output.

---

## 6. CODE QUALITY

### ~~compile_latex_to_pdf silent failures~~ DONE (returns log string, shown in UI)
### ~~`_retrieve_multi_topic` undocumented behaviour~~ DONE (documented in docstring)
### ~~LatexSubsection docstring outdated~~ DONE

---

## OPEN ITEMS (not blocking anything)

1. **Complexity table layout** (6a) — column widths, low priority cosmetic
2. **Cover page course code prominence** (6b) — minor cosmetic
