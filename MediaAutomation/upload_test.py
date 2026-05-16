import os
import json
import logging
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# =========================
# INIT
# =========================

load_dotenv()

logging.basicConfig(
    filename="log.txt",
    level=logging.INFO,
    format="%(asctime)s - %(message)s"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", "config.json"))

with open(CONFIG_PATH, "r") as f:
    config = json.load(f)

OUTPUT_DIR = os.getenv("OUTPUT_DIR")


# =========================
# MAIN FUNCTION
# =========================

def run_bulk_automation(file_list):

    if not file_list:
        logging.warning("No files provided")
        return {"success": False, "message": "No files provided"}

    try:
        with sync_playwright() as p:

            logging.info("Launching browser")

            browser = p.chromium.launch(headless=False)
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()

            # =========================
            # LOGIN
            # =========================
            logging.info("Opening login page")
            page.goto(config["login_url"], timeout=120000)

            page.fill("#email", config["username"])
            page.fill("#password", config["password"])
            page.click("button[type='submit']")
            page.wait_for_load_state("networkidle")

            logging.info("Login successful")

            # =========================
            # UPLOAD
            # =========================
            page.goto(config["upload_url"], timeout=120000)

            logging.info(f"Uploading files: {file_list}")

            page.set_input_files("#filename", file_list)
            page.click("button[value='Upload']")

            # =========================
            # WAIT DOWNLOAD
            # =========================
            logging.info("Waiting for Download CSV button")

            download_btn = page.locator("button:has-text('Download CSV')")
            download_btn.wait_for(state="visible", timeout=120000)

            with page.expect_download() as download_info:
                download_btn.click()

            download = download_info.value

            # =========================
            # SAVE FILE
            # =========================
            input_filename = os.path.basename(file_list[0])
            ticket_id = input_filename.split("_", 1)[0]
            original_name = os.path.splitext(input_filename)[0].split("_", 1)[-1]

            save_path = os.path.join(
                OUTPUT_DIR,
                f"{ticket_id}_{original_name}.csv"
            )

            download.save_as(save_path)

            logging.info(f"CSV saved successfully: {save_path}")

            browser.close()

            return {
                "success": True,
                "output_file": save_path
            }

    except Exception as e:
        logging.error(f"Automation failed: {e}", exc_info=True)

        return {
            "success": False,
            "message": str(e)
        }