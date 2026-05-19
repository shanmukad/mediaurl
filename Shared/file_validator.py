"""
File validation module for media platform automation.
Standalone SAFE validation layer (no impact on existing logic).
"""

import os
import re
import logging
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# =========================
# CONFIG
# =========================

MAX_SINGLE_FILE_SIZE = 15 * 1024 * 1024  # 15MB
MAX_BULK_FILE_COUNT = 50

SUPPORTED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".mp4", ".mov", ".pdf")

DRIVE_DOMAINS = [
    "drive.google.com",
    "docs.google.com",
    "1drv.ms",
    "dropbox.com",
    "sharepoint.com",
    "onedrive.live.com"
]


# =========================
# FILE SIZE CHECK
# =========================

def check_file_size(file_path: str):
    try:
        path = Path(file_path)

        if not path.exists():
            return False, "File not found"

        size = path.stat().st_size

        if size == 0:
            return False, "File is empty"

        if size > MAX_SINGLE_FILE_SIZE:
            return False, f"File exceeds 15MB limit ({size / 1024 / 1024:.2f}MB)"

        return True, "OK"

    except Exception as e:
        return False, f"Size check failed: {str(e)}"


# =========================
# BULK CHECK
# =========================

def check_bulk_file_count(file_list: list):
    count = len(file_list)

    if count == 0:
        return False, "No files provided"

    if count > MAX_BULK_FILE_COUNT:
        return False, f"Too many files ({count}), max allowed is {MAX_BULK_FILE_COUNT}"

    return True, "OK"


# =========================
# FILENAME VALIDATION
# =========================

def is_valid_filename(filename: str):
    try:
        path = Path(filename)

        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return False, f"Unsupported extension: {path.suffix}"

        # Format: ticketId_filename.ext
        parts = path.stem.split("_")

        if len(parts) < 2:
            return False, "Invalid format (expected ticketId_filename.ext)"

        if not parts[0].isdigit():
            return False, "Invalid ticket ID in filename"

        return True, "OK"

    except Exception as e:
        return False, str(e)


# =========================
# DRIVE LINK CHECK
# =========================

def is_drive_link(url: str):
    try:
        domain = urlparse(url).netloc.lower()

        return any(d in domain for d in DRIVE_DOMAINS)

    except Exception:
        return False


def extract_drive_file_id(url: str):
    patterns = [
        r"/file/d/([a-zA-Z0-9_-]+)",
        r"id=([a-zA-Z0-9_-]+)"
    ]

    for p in patterns:
        match = re.search(p, url)
        if match:
            return match.group(1)

    return None


# =========================
# DRIVE VALIDATION
# =========================

def validate_drive_link(url: str):
    if not is_drive_link(url):
        return False, "Not a supported cloud link"

    file_id = extract_drive_file_id(url)

    if not file_id:
        return False, "Invalid Drive link format"

    return True, file_id


# =========================
# MAIN FILE VALIDATION
# =========================

def validate_bulk_files(file_list: list):
    result = {
        "bulk_valid": False,
        "valid_files": [],
        "invalid_files": [],
        "drive_links": [],
        "local_files": [],
        "bulk_error": None
    }

    ok, msg = check_bulk_file_count(file_list)

    if not ok:
        result["bulk_error"] = msg
        result["invalid_files"] = [
            {"file": f, "errors": [msg]} for f in file_list
        ]
        return result

    result["bulk_valid"] = True

    for f in file_list:

        # DRIVE LINK HANDLING
        if isinstance(f, str) and f.startswith("http"):
            if is_drive_link(f):
                result["drive_links"].append(f)
                result["valid_files"].append(f)
            else:
                result["invalid_files"].append({
                    "file": f,
                    "errors": ["Unsupported external link"]
                })
            continue

        # LOCAL FILE CHECK
        if not os.path.exists(f):
            result["invalid_files"].append({
                "file": f,
                "errors": ["File not found"]
            })
            continue

        filename = os.path.basename(f)

        ok, msg = is_valid_filename(filename)
        if not ok:
            result["invalid_files"].append({
                "file": f,
                "errors": [msg]
            })
            continue

        ok, msg = check_file_size(f)
        if not ok:
            result["invalid_files"].append({
                "file": f,
                "errors": [msg]
            })
            continue

        result["valid_files"].append(f)
        result["local_files"].append(f)

    return result


# =========================
# GENERIC ERROR MESSAGE
# =========================

def get_generic_error_message(validation_result: dict):
    errors = []

    if validation_result.get("bulk_error"):
        errors.append(validation_result["bulk_error"])

    for item in validation_result.get("invalid_files", []):
        file_name = os.path.basename(item["file"])
        err = item["errors"][0] if item.get("errors") else "Unknown error"

        if "15MB" in err:
            errors.append(f"{file_name} exceeds 15MB limit")
        elif "format" in err or "ticket ID" in err:
            errors.append(f"{file_name} invalid naming format")
        elif "not found" in err.lower():
            errors.append(f"{file_name} not found")
        else:
            errors.append(f"{file_name}: {err}")

    return "; ".join(errors[:5])