"""Check scheduled materials through the actual website in Chrome.

Usage: python3 tests/material_release.py http://127.0.0.1:8765/ [artifact-directory]
Requires Python Playwright plus Chrome or Playwright Chromium.
"""
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8765/'
OUTPUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path('/tmp/aml-material-release-check')
OUTPUT.mkdir(parents=True, exist_ok=True)
RELEASES = [
    (8, '2026-10-28T04:00:00+00:00', '2026-10-29'),
    (9, '2026-11-04T05:00:00+00:00', '2026-11-05'),
    (10, '2026-11-11T05:00:00+00:00', '2026-11-12'),
    (11, '2026-11-18T05:00:00+00:00', '2026-11-19'),
    (12, '2026-12-02T05:00:00+00:00', '2026-12-03'),
]
checks = []
errors = []


def check_links(page, released):
    for week, _, date in RELEASES:
        links = page.locator(f'#class-{date} .materials a')
        expected = (2 if week == 8 else 1) if week in released else 0
        assert links.count() == expected, (week, released, links.count())
        for link in links.all():
            assert link.is_visible(), (week, 'link is hidden after release')
    assert page.locator('#class-2026-10-22 .materials a').count() == 3
    assert page.locator('#class-2026-09-10 .materials a').count() == 1


with sync_playwright() as playwright:
    chrome = Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
    browser = playwright.chromium.launch(channel='chrome' if chrome.exists() else None)
    context = browser.new_context(timezone_id='Asia/Tokyo', viewport={'width': 1440, 'height': 1000})

    def open_at(when, context=context):
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.clock.set_fixed_time(when)
        page.goto(BASE, wait_until='networkidle')
        return page

    # Every configured release: one second before midnight and exactly at midnight.
    for index, (week, instant, _) in enumerate(RELEASES):
        midnight = datetime.fromisoformat(instant)
        for label, now, released in [
            ('before', midnight - timedelta(seconds=1), set(range(8, week))),
            ('at', midnight, set(range(8, week + 1))),
        ]:
            page = open_at(now)
            check_links(page, released)
            checks.append(f'L{week} {label} New York midnight, browser in Tokyo')
            if week == 8:
                page.locator('#schedule').screenshot(path=str(OUTPUT / f'desktop-{label}.png'))
            page.close()

    # Both occurrences of the repeated local hour on the DST transition day.
    for instant in ['2026-11-01T05:30:00+00:00', '2026-11-01T06:30:00+00:00']:
        page = open_at(datetime.fromisoformat(instant))
        check_links(page, {8})
        page.close()
    checks.append('DST repeated hour does not release L9 early')

    page = open_at(datetime.fromisoformat('2026-11-25T05:00:00+00:00'))
    check_links(page, {8, 9, 10, 11})
    assert page.locator('#class-2026-11-26 .materials a').count() == 0
    page.close()
    checks.append('Thanksgiving has no release; L12 stays hidden')

    page = open_at(datetime.fromisoformat('2026-10-29T16:00:00+00:00'))
    assert page.locator('.update-material-title').inner_text() == 'Neural Networks Fundamentals'
    assert 'Past class' in page.locator('.update-recent .update-label').inner_text()
    assert page.locator('.update-materials a').count() == 3
    page.close()
    checks.append('Existing past-class banner remains unchanged on class day')

    # A tab stays open across release time; the real page timer must reveal links.
    page = context.new_page()
    before = datetime.fromisoformat('2026-10-28T03:59:59+00:00')
    page.clock.install(time=before)
    page.clock.set_fixed_time(before)
    page.goto(BASE, wait_until='networkidle')
    check_links(page, set())
    page.clock.set_fixed_time(datetime.fromisoformat('2026-10-28T04:00:00+00:00'))
    page.clock.fast_forward(31000)
    check_links(page, {8})
    page.evaluate("window.dispatchEvent(new Event('pageshow'))")
    page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
    check_links(page, {8})
    page.close()
    checks.append('Open-tab timer releases links without refresh or duplication')

    mobile = browser.new_context(timezone_id='Pacific/Honolulu', viewport={'width': 390, 'height': 844}, is_mobile=True)
    page = open_at(datetime.fromisoformat('2026-10-28T04:00:00+00:00'), mobile)
    check_links(page, {8})
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    page.locator('#schedule').screenshot(path=str(OUTPUT / 'mobile-released.png'))
    page.close()
    mobile.close()
    checks.append('Mobile layout and Honolulu timezone')

    # Templates are inert even before JavaScript runs; old links remain available.
    no_js = browser.new_context(java_script_enabled=False)
    page = no_js.new_page()
    page.goto(BASE, wait_until='networkidle')
    for week, _, _ in RELEASES:
        row = page.locator('.schedule tbody tr').filter(has_text=re.compile(rf'Week {week}\b'))
        assert row.locator('.materials a').count() == 0
    assert page.locator('.schedule tbody tr').filter(has_text='Week 7').locator('.materials a').count() == 3
    no_js.close()
    checks.append('No early link flash when JavaScript is disabled')

    # Fetch each released PDF through the site's actual URL and record its bytes.
    page = open_at(datetime.fromisoformat('2026-12-18T17:00:00+00:00'))
    check_links(page, {8, 9, 10, 11, 12})
    downloads = []
    for week, _, date in RELEASES:
        href = page.locator(f'#class-{date} .materials a.slides').get_attribute('href')
        response = context.request.get(urljoin(BASE, href))
        content = response.body()
        assert response.status == 200 and content.startswith(b'%PDF-'), (week, response.status)
        downloads.append({'lecture': f'L{week}', 'url': response.url, 'bytes': len(content),
                          'sha256': hashlib.sha256(content).hexdigest()})
    page.close()
    checks.append('All five PDF links return PDFs; released links remain visible')
    assert not errors, errors
    browser.close()

report = {'baseUrl': BASE, 'passed': True, 'checks': checks, 'pdfDownloads': downloads, 'pageErrors': errors}
(OUTPUT / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'passed': True, 'checks': len(checks), 'pdfs': len(downloads), 'report': str(OUTPUT / 'report.json')}))
