import re
from urllib.parse import urldefrag, urlparse

from bs4 import BeautifulSoup
from pydantic import HttpUrl


def validate_https(url: HttpUrl) -> HttpUrl:
    if urlparse(str(url)).scheme != "https":
        raise ValueError("URL must use HTTPS protocol")
    return url


def clean_html(html_content: str) -> str:
    soup = BeautifulSoup(html_content, "lxml")
    text = soup.get_text()

    text = re.sub(r"\n\s*\n", "\n", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"([.!?])\s*([A-Z])", r"\1\n\2", text)
    text = text.strip()
    text = text.replace("\r\n", "\n")

    return str(text)


def normalize_url(url: str) -> str:
    """Normalize URL for comparison."""
    clean_url, _ = urldefrag(url)
    return clean_url.lower().rstrip("/")

def get_domain(url: str) -> str:
    return urlparse(url).netloc