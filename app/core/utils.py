import re
from urllib.parse import urlparse

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
