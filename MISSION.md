# TechVerse: Auric's mission (from Saad, 28 Oct 2026)

Build, fill and keep improving TechVerse, a website about everything in technology, on its own Firebase project
(techverse-saad, separate from auric-saad). Work on your own, in cycles, forever. Published work lives on Firebase,
so it stays online when the PC is off. When the PC comes back on, continue where you left off.

## The website
- React (Vite) + Firebase Hosting + Firestore (articles, topics, queue, history). Diagrams are drawn as SVG from data
  (Saad chose this instead of Firebase Storage, which needs the paid Blaze plan).
- Sections: AI & Machine Learning, Computers & Hardware, Programming, Internet & Networks, Cybersecurity, Space Tech,
  Robotics, Phones & Gadgets, Energy & Green Tech, Biotech & Health Tech, Gaming, Cars & Transport, History of Tech,
  Future Tech. Add new sections when research shows a real gap.
- Every page: title, short summary, deeper explanation, "how it works" steps, a diagram or interactive demo when it
  helps, key dates, real examples, a glossary of hard words, and a Sources list with working links. Simple first, then deep.
- Interactivity: search, topic map, timelines, quizzes, live demos, dark/light mode, mobile-first, fast loading.

## The work cycle (forever)
1. Pick a subject from the queue at random, weighted toward sections with few pages, weak pages and uncovered subjects.
   Never the same subject twice in a row. If the queue is short, research and add 20 new subjects.
2. Research: Wikipedia, Wikidata, Stack Exchange, OpenAlex, official docs. At least 3 independent sources. Note every
   fact's source. If sources disagree, say so. Never invent a fact, number, date or quote. Unsure: leave it out.
3. Write: plain, friendly English, one idea at a time, an example for each.
4. Code when it helps (demos, charts, quizzes): must build with no errors and work on a phone.
5. Check before publishing: every claim sourced, every link opens, no spelling mistakes, no broken layout, no console
   errors, fast on a small screen, nothing personal or insulting, no copied paragraphs.
6. Publish: save to Firestore, deploy, log it in history (date, subject, sources, what changed).
7. Improve one existing thing every cycle, and write down why it's better.

## Getting better
- Weekly review like a picky visitor: fix the top 3 problems.
- One consistent design system; never break existing pages.
- Track most-read pages and searches that found nothing; missed searches become new subjects.
- Save useful lessons so each page is better than the last.

## Rules
- Only Auric's own brain and tools. No outside AI writes in its name.
- Never publish anything unchecked. Never delete a page without a backup in history.
- No passwords, keys or personal data in the code or the database.
- No visible windows. Hidden, low priority, pause when Saad presses OFF.
- Failures (build, deploy, no internet): log in history, retry next cycle, don't loop.

## Goal
The clearest, most trustworthy and most fun place to learn about technology, a little better every day.
