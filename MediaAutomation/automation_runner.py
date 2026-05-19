"""
Async automation runner for media platform uploads.
"""

import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

from Shared.auth import create_browser_context, close_browser, login
from Shared.logging_config import setup_logging

load_dotenv()
logger = setup_logging(__name__)

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.json"

with open(CONFIG_PATH, "r") as f:
    config = json.load(f)

OUTPUT_DIR = os.getenv("OUTPUT_DIR") or str(BASE_DIR / "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


async def run_bulk_automation(file_list):
    if not file_list:
        logger.warning("No files provided")
        return {"success": False, "message": "No files provided"}

    browser = context = page = None

    try:
        logger.info("Launching browser")
        browser, context, page = await create_browser_context(headless=False)

        logger.info("Performing login")
        page, login_success = await login(page, context, force_relogin=True)

        if not login_success:
            return {"success": False, "message": "Login failed"}

        await page.goto(config["upload_url"], timeout=120000)

        logger.info("Uploading files")
        await page.set_input_files("#filename", file_list)
        await page.click("button[value='Upload']")

        logger.info("Waiting for Download CSV button")
        download_btn = page.locator("button:has-text('Download CSV')")
        await download_btn.wait_for(state="visible", timeout=120000)

        async with page.expect_download() as download_info:
            await download_btn.click()

        download = await download_info.value

        input_filename = os.path.basename(file_list[0])
        ticket_id = input_filename.split("_", 1)[0]
        original_name = os.path.splitext(input_filename)[0].split("_", 1)[-1]

        save_path = os.path.join(OUTPUT_DIR, f"{ticket_id}_{original_name}.csv")

        await download.save_as(save_path)

        logger.info(f"Saved CSV: {save_path}")

        return {"success": True, "output_file": save_path}

    except Exception as e:
        logger.error(f"Automation failed: {e}", exc_info=True)
        return {"success": False, "message": str(e)}

    finally:
        if browser or context or page:
            await close_browser(browser, context, page)