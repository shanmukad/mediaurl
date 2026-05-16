import re

def normalize_text(text: str) -> str:
    if not text:
        return ""

    return text.lower().strip()



def contains_media_keywords(subject: str, body: str) -> bool:

    content = (
        normalize_text(subject) + " " +
        normalize_text(body)
    )

    for keyword in MEDIA_KEYWORDS:
        if keyword in content:
            return True

    return False



def detect_cloud_links(body: str):

    if not body:
        return []

    patterns = [
        r'https?://[^\s]*sharepoint\.com[^\s]+',
        r'https?://1drv\.ms[^\s]+',
        r'https?://[^\s]*onedrive\.live\.com[^\s]+',
        r'https?://drive\.google\.com[^\s]+',
        r'https?://dropbox\.com[^\s]+'
    ]

    links = []

    for pattern in patterns:
        matches = re.findall(pattern, body)
        links.extend(matches)

    return list(set(links))



def is_valid_media_request(subject: str, body: str):

    has_keywords = contains_media_keywords(
        subject,
        body
    )

    links = detect_cloud_links(body)

    return {
        "valid": has_keywords,
        "keywords_found": has_keywords,
        "cloud_links": links,
        "has_cloud_links": len(links) > 0
    }