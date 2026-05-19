"""
Async automation runner for media platform uploads.
"""

import os
import json
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
    """
    Upload media files and download generated CSV.
    """

    if not file_list:
        logger.warning("No files provided")

        return {
            "success": False,
            "message": "No files provided"
        }

    browser = context = page = None

    try:
        #
        # LAUNCH BROWSER
        #

        logger.info("Launching browser")

        browser, context, page = await create_browser_context(
            headless=False
        )

        #
        # LOGIN
        #

        logger.info("Performing login")

        page, login_success = await login(
            page,
            context,
            force_relogin=True
        )

        if not login_success:
            logger.error("Login failed")

            return {
                "success": False,
                "message": "Login failed"
            }

        #
        # OPEN UPLOAD PAGE
        #

        logger.info("Opening upload page")

        await page.goto(
            config["upload_url"],
            timeout=120000,
            wait_until="domcontentloaded"
        )

        #
        # WAIT FOR FILE INPUT
        #

        logger.info("Waiting for file input")

        file_input = page.locator("#filename")

        await file_input.wait_for(
            state="visible",
            timeout=30000
        )

        #
        # UPLOAD FILES
        #

        logger.info("Uploading files")

        await file_input.set_input_files(file_list)

        #
        # VERIFY FILES ATTACHED
        #

        file_count = await file_input.evaluate(
            "(el) => el.files.length"
        )

        logger.info(f"Files attached: {file_count}")

        if file_count == 0:
            raise Exception("No files were attached")

        #
        # WAIT FOR UPLOAD BUTTON
        #

        logger.info("Waiting for upload button")

        upload_button = page.locator(
            "button[type='submit'][value='Upload']"
        )

        await upload_button.wait_for(
            state="visible",
            timeout=30000
        )

        #
        # CLICK UPLOAD BUTTON
        #

        logger.info("Clicking upload button")

        await upload_button.click()

        #
        # WAIT FOR DOWNLOAD CSV BUTTON
        #

        logger.info("Waiting for Download CSV button")

        download_btn = page.locator(
            "button[onclick='downloadCSV()']"
        )

        await download_btn.wait_for(
            state="visible",
            timeout=120000
        )

        logger.info("Download button found")

        #
        # DOWNLOAD CSV
        #

        logger.info("Starting CSV download")

        async with page.expect_download() as download_info:
            await download_btn.click()

        download = await download_info.value

        #
        # BUILD OUTPUT FILENAME
        #

        input_filename = os.path.basename(file_list[0])

        ticket_id = input_filename.split("_", 1)[0]

        original_name = (
            os.path.splitext(input_filename)[0]
            .split("_", 1)[-1]
        )

        save_path = os.path.join(
            OUTPUT_DIR,
            f"{ticket_id}_{original_name}.csv"
        )

        #
        # SAVE DOWNLOADED FILE
        #

        await download.save_as(save_path)

        logger.info(f"CSV saved successfully: {save_path}")

        return {
            "success": True,
            "output_file": save_path
        }

    except Exception as e:

        logger.error(
            f"Automation failed: {e}",
            exc_info=True
        )

        #
        # SAVE DEBUG SCREENSHOT
        #

        try:
            if page:

                debug_path = os.path.join(
                    OUTPUT_DIR,
                    "automation_error.png"
                )

                await page.screenshot(
                    path=debug_path,
                    full_page=True
                )

                logger.info(
                    f"Saved debug screenshot: {debug_path}"
                )

        except Exception as screenshot_error:

            logger.warning(
                f"Could not save screenshot: {screenshot_error}"
            )

        return {
            "success": False,
            "message": str(e)
        }

    finally:

        logger.info("Closing browser")

        if browser or context or page:

            await close_browser(
                browser,
                context,
                page
            )