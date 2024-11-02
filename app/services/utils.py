import re

import aiohttp
from bs4 import BeautifulSoup
from fastapi import HTTPException


async def fetch_html(
    url: str, session: aiohttp.ClientSession = None
) -> tuple[str, str]:
    """Fetch HTML content and final URL from URL"""
    if session is None:
        async with aiohttp.ClientSession() as session:
            return await _fetch_html_with_session(url, session)
    else:
        return await _fetch_html_with_session(url, session)


async def _fetch_html_with_session(
    url: str, session: aiohttp.ClientSession
) -> tuple[str, str]:
    """Helper function to fetch HTML content and final URL using an existing session"""
    try:
        async with session.get(url) as response:
            if response.status == 200:
                final_url = str(response.url)
                html_content = await response.text(errors="replace")
                return html_content, final_url
            else:
                raise HTTPException(
                    status_code=response.status, detail="Failed to fetch URL"
                )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching URL: {str(e)}")


def clean_html_content(html_content: str) -> str:
    """
    Clean text content extracted from HTML by:
    1. Removing excessive newlines
    2. Removing excessive whitespace
    3. Ensuring proper spacing between sentences
    4. Preserving meaningful paragraph breaks

    Args:
        html_content (str): Raw HTML content

    Returns:
        str: Cleaned text content
    """
    # Extract text from HTML
    soup = BeautifulSoup(html_content, "lxml")
    text = soup.get_text()

    # Replace multiple newlines with a single newline
    text = re.sub(r"\n\s*\n", "\n", text)

    # Replace multiple spaces with a single space
    text = re.sub(r"\s+", " ", text)

    # Ensure proper spacing after punctuation
    text = re.sub(r"([.!?])\s*([A-Z])", r"\1\n\2", text)

    # Remove leading/trailing whitespace
    text = text.strip()

    # Ensure consistent newline character
    text = text.replace("\r\n", "\n")

    return text
