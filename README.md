# article-practice-tool

Local browser-based tool for practising English article usage with your own text.

## Repo Structure

```text
article_practice/
  __init__.py
  __main__.py
  core.py
  web.py
  static/
tests/
plan.md
```

`article_practice/core.py` contains the exercise and grading logic.
`article_practice/web.py` contains the local HTTP server.
`article_practice/static/` contains the browser UI.

## Why This Interface

The original repo used email as the user interface. The useful part of the idea was never the mailbox workflow; it was the exercise loop:

1. Paste real English.
2. Remove `a`, `an`, and `the`.
3. Restore them.
4. Grade the result.

This version keeps that loop and removes the email round-trip.

## Run

```bash
python3 -m article_practice
```

The app prints the local URL it started on, for example `http://127.0.0.1:62986`.

To open the browser automatically:

```bash
python3 -m article_practice --open-browser
```

To request a specific port:

```bash
python3 -m article_practice --port 8000
```

## Tests

```bash
python3 -m unittest discover -s tests -v
```
