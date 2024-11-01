import aiohttp
from fastapi import HTTPException


async def fetch_html(url: str, session: aiohttp.ClientSession = None) -> tuple[str, str]:
    """Fetch HTML content and final URL from URL"""
    if session is None:
        async with aiohttp.ClientSession() as session:
            return await _fetch_html_with_session(url, session)
    else:
        return await _fetch_html_with_session(url, session)


async def _fetch_html_with_session(url: str, session: aiohttp.ClientSession) -> tuple[str, str]:
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
