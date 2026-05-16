import os
import requests
from dotenv import load_dotenv

load_dotenv()

ALLOWED_EXTENSIONS = [
    ".jpg",
    ".jpeg",
    ".png",
    ".pdf",
    ".mp4"
]
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

STAGING_DIR = os.path.join(
    BASE_DIR,
    "staging"
)

os.makedirs(STAGING_DIR, exist_ok=True)



def is_supported_file(filename: str):

    filename = filename.lower()

    return any(
        filename.endswith(ext)
        for ext in ALLOWED_EXTENSIONS
    )



def create_ticket_staging(ticket_id: int):

    ticket_folder = os.path.join(
        STAGING_DIR,
        str(ticket_id)
    )

    os.makedirs(ticket_folder, exist_ok=True)

    return ticket_folder



def save_attachment(
    content,
    filename,
    ticket_id
):

    if not is_supported_file(filename):
        return None

    ticket_folder = create_ticket_staging(ticket_id)

    file_path = os.path.join(
        ticket_folder,
        filename
    )

    with open(file_path, "wb") as f:
        f.write(content)

    return file_path