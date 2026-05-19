"""
Authentication module for media platform automation.
Async Playwright version (required for FastAPI/Uvicorn compatibility).
Handles login with session persistence via cookies.
"""

import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

from playwright.async_api import async_playwright

load_dotenv()

logger = logging.getLogger(__name__)

# =========================
# COOKIE STORAGE
# =========================

COOKIES_DIR = Path(__file__).parent.parent / "runtime" / "cookies"
COOKIES_DIR.mkdir(parents=True, exist_ok=True)


# =========================
# CONFIG / CREDENTIALS
# =========================

def get_config():
    config_path = Path(__file__).parent.parent / "MediaAutomation" / "config.json"
    with open(config_path, "r") as f:
        return json.load(f)


def get_credentials():
    username = os.getenv("UI_USERNAME")
    password = os.getenv("UI_PASSWORD")

    if not username or not password:
        raise ValueError("UI_USERNAME and UI_PASSWORD must be set in .env")

    return username, password


# =========================
# COOKIE HELPERS (optional future use)
# =========================

async def save_cookies(context, cookie_file):
    cookies = await context.cookies()
    with open(cookie_file, "w") as f:
        json.dump(cookies, f)
    logger.info(f"Cookies saved to {cookie_file}")


async def load_cookies(context, cookie_file):
    if cookie_file.exists():
        try:
            with open(cookie_file, "r") as f:
                cookies = json.load(f)

            await context.add_cookies(cookies)
            logger.info(f"Cookies loaded from {cookie_file}")
            return True

        except Exception as e:
            logger.warning(f"Failed to load cookies: {e}")

    return False


# =========================
# LOGIN (ASYNC)
# =========================

async def login(page, context=None, force_relogin=True):
    """
    Perform login to the media platform (async version).

    Args:
        page: Playwright page object
        context: Playwright context object (optional)
        force_relogin: kept for compatibility (not used currently)

    Returns:
        tuple: (page, success boolean)
    """

    config = get_config()
    username, password = get_credentials()

    try:
        logger.info("Starting login process")

        # Navigate to login page
        logger.info(f"Navigating to: {config['login_url']}")
        await page.goto(config["login_url"], timeout=120000)

        # Wait for form
        await page.wait_for_selector("#email", timeout=10000)

        # Fill credentials
        logger.info("Filling login credentials")
        await page.fill("#email", username)
        await page.fill("#password", password)

        # Submit
        logger.info("Submitting login form")
        await page.click("button[type='submit']")

        # Wait for navigation
        await page.wait_for_load_state("networkidle", timeout=30000)

        logger.info(f"Login complete, current URL: {page.url}")

        # Save cookies (optional)
        if context:
            cookie_file = COOKIES_DIR / "session_cookies.json"
            await save_cookies(context, cookie_file)

        return page, True

    except Exception as e:
        logger.error(f"Login failed: {e}", exc_info=True)
        return page, False


# =========================
# BROWSER CREATION (ASYNC)
# =========================

async def create_browser_context(headless=False):
    """
    Create async Playwright browser context.

    Returns:
        (browser, context, page)
    """

    playwright = await async_playwright().start()

    browser = await playwright.chromium.launch(headless=headless)

    context = await browser.new_context(accept_downloads=True)

    page = await context.new_page()

    return browser, context, page


# =========================
# CLEANUP
# =========================

async def close_browser(browser, context, page):
    """Clean up browser resources safely."""

    try:
        if page:
            await page.close()

        if context:
            await context.close()

        if browser:
            await browser.close()

        logger.info("Browser closed successfully")

    except Exception as e:
        logger.error(f"Failed to close browser: {e}")


# =========================
# OPTIONAL LOGOUT
# =========================

async def logout(page):
    """
    Clear session data.
    """

    try:
        await page.context.clear_cookies()
        await page.evaluate("() => { localStorage.clear(); }")

        logger.info("Logout completed")
        return True

    except Exception as e:
        logger.error(f"Logout failed: {e}")
        return False