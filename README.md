# COMS 4995 Applied Machine Learning (Fall 2026)

Course website: https://columbia-coms4995.github.io/aml-fall2026/

Columbia University, Department of Computer Science. Instructor: Dr. Spencer W. Luo.

Materials for Weeks 8–12 are uploaded in advance. Their links live in
`<template data-release-date="YYYY-MM-DD">` elements in `index.html` and appear
at midnight in `America/New_York` on the Wednesday before class:

| Lecture | Release date |
| --- | --- |
| L8 | October 28, 2026 |
| L9 | November 4, 2026 |
| L10 | November 11, 2026 |
| L11 | November 18, 2026 |
| L12 | December 2, 2026 |

The page uses the visitor's clock, converted to New York time, including daylight
saving time. Links appear on page load, when the page becomes visible again, or
within 30 seconds if it stays open across midnight. Released links stay visible;
the Thanksgiving break has no release. The existing past-class materials banner
keeps its previous behavior. JavaScript must be enabled to show scheduled links.

This is display scheduling: the repository and uploaded PDFs are public at all
times. PDFs are final snapshots exported from Drive; later Drive edits require a
new export and commit. No weekly job or running local computer is needed.

To verify the release boundaries in a browser, serve this directory and run
`python3 tests/material_release.py http://127.0.0.1:8765/`. The check uses Python
Playwright and a local Chrome installation (or Playwright Chromium).
