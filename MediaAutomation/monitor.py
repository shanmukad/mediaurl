import time
import os
import shutil
import logging
from dotenv import load_dotenv
from Shared.automation_service import run_automation_sync

load_dotenv()

logging.basicConfig(
    filename="log.txt",
    level=logging.INFO,
    format="%(asctime)s - %(message)s"
)

INPUT_DIR = os.getenv("INPUT_DIR")
PROCESSED_DIR = os.getenv("PROCESSED_DIR")
OUTPUT_DIR = os.getenv("OUTPUT_DIR")

SUPPORTED_EXTS = (".jpg", ".jpeg", ".png", ".mp4", ".mov", ".pdf")


# =========================
# MOVE FILES
# =========================
def move_input_to_processed(file_list):
    for f in file_list:
        try:
            dst = os.path.join(PROCESSED_DIR, os.path.basename(f))
            shutil.move(f, dst)
            logging.info(f"Moved to PROCESSED: {dst}")
        except Exception as e:
            logging.error(f"Move failed: {e}")


# =========================
# MONITOR LOOP (SAFE 3 RETRIES)
# =========================
def monitor():

    logging.info("=== MONITOR STARTED ===")

    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    while True:

        try:
            file_list = [
                os.path.join(INPUT_DIR, f)
                for f in os.listdir(INPUT_DIR)
                if f.lower().endswith(SUPPORTED_EXTS)
                and os.path.isfile(os.path.join(INPUT_DIR, f))
            ]

            if not file_list:
                time.sleep(5)
                continue

            logging.info(f"Processing files: {[os.path.basename(f) for f in file_list]}")

            result = None

            # =========================
            # RUN AUTOMATION (3 RETRIES)
            # =========================
            for attempt in range(3):

                logging.info(f"Attempt {attempt + 1} running automation")

                result = run_automation_sync(file_list)

                if isinstance(result, dict) and result.get("success"):
                    logging.info(f"Success: {result.get('output_file')}")
                    break

                logging.warning(f"Attempt {attempt + 1} failed")

            # =========================
            # MOVE ONLY ON SUCCESS
            # =========================
            if isinstance(result, dict) and result.get("success"):
                move_input_to_processed(file_list)
            else:
                logging.error("All attempts failed — not moving files")

        except Exception as e:
            logging.error(f"Monitor loop error: {e}")

        time.sleep(10)


if __name__ == "__main__":
    monitor()