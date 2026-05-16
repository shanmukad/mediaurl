import os
import time
from playwright.sync_api import sync_playwright
from Shared.attachment_handler import create_ticket_staging

SUPPORTED_PROVIDERS = {
    "sharepoint": [
        "sharepoint.com",
        "1drv.ms",
        "onedrive.live.com"
    ],
    "google_drive": [
        "drive.google.com"
    ],
    "dropbox": [
        "dropbox.com"
    ]
}


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PLAYWRIGHT_PROFILE = os.path.join(
    BASE_DIR,
    "..",
    "playwright_profile"
)



def identify_provider(link: str):

    for provider, domains in SUPPORTED_PROVIDERS.items():

        for domain in domains:

            if domain in link:
                return provider

    return None


def download_sharepoint_folder(
        
          link: str,
    ticket_id: int
):
    downloaded_files = []

    ticket_folder = create_ticket_staging(ticket_id)

    with sync_playwright() as p:

        browser = p.chromium.launch_persistent_context(
            user_data_dir=PLAYWRIGHT_PROFILE,
            headless=False,
            accept_downloads=True
        )

        page = browser.new_page()

        print("Opening SharePoint link...")

        page.goto(link)

        page.wait_for_timeout(5000)

        rows = page.locator("div[role='row']")

        count = rows.count()

        print(f"Detected rows: {count}")

        for i in range(count):

            try:

                row = rows.nth(i)

                text = row.inner_text()

                if ".pdf" not in text.lower():
                    continue

                print(f"Downloading: {text}")

                with page.expect_download() as download_info:
                    row.click()

                download = download_info.value

                filename = download.suggested_filename

                save_path = os.path.join(
                    ticket_folder,
                    filename
                )

                download.save_as(save_path)

                downloaded_files.append(save_path)

                time.sleep(2)

            except Exception as e:
                print(f"Download failed: {e}")

        browser.close()

    return downloaded_files


def process_cloud_links(
    links,
    ticket_id
):

    all_files = []

    for link in links:

        provider = identify_provider(link)

        print(f"Provider detected: {provider}")

        try:

            if provider == "sharepoint":

                files = download_sharepoint_folder(
                    link,
                    ticket_id
                )

                all_files.extend(files)

        except Exception as e:
            print(f"Cloud download failed: {e}")

    return all_files
