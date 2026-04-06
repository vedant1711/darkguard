"""
crawler/service.py — Playwright-based headless page crawler.

Extracts DOM metadata, text content, and screenshots from a URL
so the backend can analyze pages server-side without the extension.
"""

from __future__ import annotations

import asyncio
import base64
import logging
from dataclasses import dataclass, field

from playwright.async_api import async_playwright, Page, Browser

logger = logging.getLogger(__name__)

# Max time to wait for page load (ms)
PAGE_TIMEOUT = 15_000
# Max number of elements to collect per category (matches extension collector.ts)
MAX_ELEMENTS = 100


@dataclass
class CrawlResult:
    """Result of crawling a URL — ready to pass to the dispatcher."""
    dom_metadata: dict
    text_content: dict
    screenshot_b64: str
    review_text: str | None = None
    checkout_flow: dict | None = None
    nagging_events: dict | None = None
    url: str = ""


async def _extract_dom_metadata(page: Page, url: str) -> dict:
    """Extract hidden elements, interactive elements, and prechecked inputs."""
    return await page.evaluate("""(maxElements) => {
        function getSelector(el) {
            if (el.id) return '#' + el.id;
            const tag = el.tagName.toLowerCase();
            const parent = el.parentElement;
            if (!parent) return tag;
            const siblings = Array.from(parent.children).filter(c => c.tagName === el.tagName);
            const idx = siblings.indexOf(el);
            return getSelector(parent) + ' > ' + tag + (siblings.length > 1 ? ':nth-child(' + (idx+1) + ')' : '');
        }
        function getRect(el) {
            const r = el.getBoundingClientRect();
            return { x: r.x, y: r.y, width: r.width, height: r.height };
        }
        function getStyles(el) {
            const s = getComputedStyle(el);
            return {
                color: s.color, background_color: s.backgroundColor,
                font_size: s.fontSize, opacity: s.opacity,
                display: s.display, visibility: s.visibility
            };
        }
        function toInfo(el) {
            const attrs = {};
            for (const a of el.attributes) attrs[a.name] = a.value;
            return {
                selector: getSelector(el),
                tag_name: el.tagName.toLowerCase(),
                text_content: (el.textContent || '').slice(0, 200),
                attributes: attrs,
                bounding_rect: getRect(el),
                computed_styles: getStyles(el)
            };
        }

        // Hidden elements (display:none, visibility:hidden, opacity:0, tiny size)
        const hidden = [];
        document.querySelectorAll('*').forEach(el => {
            if (hidden.length >= maxElements) return;
            const s = getComputedStyle(el);
            const r = el.getBoundingClientRect();
            if (
                (s.display === 'none' || s.visibility === 'hidden' || parseFloat(s.opacity) === 0 ||
                (r.width < 2 && r.height < 2)) &&
                el.textContent && el.textContent.trim().length > 0
            ) {
                hidden.push(toInfo(el));
            }
        });

        // Interactive elements — match extension selector: button, [role="button"], a[href], input[type="submit"], input[type="button"], select
        const interactive = [];
        document.querySelectorAll('button, [role="button"], a[href], input[type="submit"], input[type="button"], select').forEach(el => {
            if (interactive.length >= maxElements) return;
            interactive.push(toInfo(el));
        });

        // Prechecked inputs
        const prechecked = [];
        document.querySelectorAll('input[type="checkbox"]:checked, input[type="radio"]:checked').forEach(el => {
            if (prechecked.length >= maxElements) return;
            prechecked.push(toInfo(el));
        });

        return {
            hidden_elements: hidden,
            interactive_elements: interactive,
            prechecked_inputs: prechecked,
            url: window.location.href
        };
    }""", MAX_ELEMENTS)


async def _extract_text_content(page: Page) -> dict:
    """Extract button labels, headings, and body text."""
    return await page.evaluate("""() => {
        function getSelector(el) {
            if (el.id) return '#' + el.id;
            const tag = el.tagName.toLowerCase();
            const parent = el.parentElement;
            if (!parent) return tag;
            const siblings = Array.from(parent.children).filter(c => c.tagName === el.tagName);
            const idx = siblings.indexOf(el);
            return getSelector(parent) + ' > ' + tag + (siblings.length > 1 ? ':nth-child(' + (idx+1) + ')' : '');
        }

        const buttons = [];
        // Match extension selector: button, [role="button"], a.btn, a.button, input[type="submit"]
        document.querySelectorAll('button, [role="button"], a[href], input[type="submit"]').forEach(el => {
            const text = (el.textContent || el.value || '').trim();
            if (text && buttons.length < 50) {
                buttons.push({ selector: getSelector(el), text: text.slice(0, 200) });
            }
        });

        const headings = [];
        document.querySelectorAll('h1, h2, h3, h4, h5, h6').forEach(el => {
            const text = (el.textContent || '').trim();
            if (text && headings.length < 30) {
                headings.push({ selector: getSelector(el), text: text.slice(0, 200) });
            }
        });

        const body = document.body ? document.body.innerText.slice(0, 5000) : '';

        return {
            button_labels: buttons,
            headings: headings,
            body_text: body
        };
    }""")


async def _extract_reviews(page: Page) -> str | None:
    """Try to extract review text if the page looks like it has reviews."""
    review_text = await page.evaluate("""() => {
        const selectors = [
            '[data-testid*="review"]', '.review', '.customer-review',
            '[class*="review"]', '[class*="testimonial"]',
            '#reviews', '#customer-reviews'
        ];
        let text = '';
        for (const sel of selectors) {
            document.querySelectorAll(sel).forEach(el => {
                text += (el.textContent || '').slice(0, 500) + '\\n';
            });
            if (text.length > 100) break;
        }
        return text.trim() || null;
    }""")
    return review_text


async def crawl_url(url: str) -> CrawlResult:
    """Crawl a URL with Playwright and extract all data needed for analysis.

    Launches a headless Chromium browser, navigates to the URL,
    extracts DOM metadata, text content, screenshots, and reviews.
    """
    async with async_playwright() as p:
        browser: Browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            page = await context.new_page()

            # Navigate and wait for network idle
            await page.goto(url, wait_until="networkidle", timeout=PAGE_TIMEOUT)

            # Wait a bit for dynamic content
            await page.wait_for_timeout(1500)

            # Extract data
            dom_metadata = await _extract_dom_metadata(page, url)
            text_content = await _extract_text_content(page)
            review_text = await _extract_reviews(page)

            # Screenshot
            screenshot_bytes = await page.screenshot(full_page=False)
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")

            return CrawlResult(
                dom_metadata=dom_metadata,
                text_content=text_content,
                screenshot_b64=screenshot_b64,
                review_text=review_text,
                url=url,
            )
        finally:
            await browser.close()


def crawl_url_sync(url: str) -> CrawlResult:
    """Synchronous wrapper for crawl_url."""
    return asyncio.run(crawl_url(url))
