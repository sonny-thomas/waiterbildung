import json
from urllib.parse import urljoin, urlparse
import aiohttp
import asyncio
from bs4 import BeautifulSoup


async def scrap_course_data(url, identifying_id, checked_urls = set()) -> list[str]:
    try:
        course_urls = []
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
            async with session.get(url) as response:
                html = ""
                if response.status == 200:
                    html = await response.text()
                else:
                    print("Failed to retrieve the webpage. Status code:", response.status)
                    return []
                
                soup = BeautifulSoup(html, "lxml")

                if soup.find(id=identifying_id) != None:
                    course_urls.append(url)
                    print(url)

                for tag in soup.find_all("a"):
                    # avoid sites like https://examplesite.com/page#section
                    href = tag.get("href")
                    if href == None:
                        continue
                    href = href.split("#")[0]

                    # to avoid leaving the main site (dont want to go to facebook or something)
                    full_url = urljoin(url, href)
                    base_url = urlparse(full_url).netloc
                    orig_base_url = urlparse(url).netloc
                    if base_url != orig_base_url:
                        continue

                    if not (full_url in checked_urls):
                        checked_urls.add(full_url)
                        course_urls.extend(await scrap_course_data(full_url, identifying_id, checked_urls))
        return course_urls
    except asyncio.TimeoutError:
        return []
    except aiohttp.ClientError as e:
        print(f"Client error: {e}")
        return []

def write_to_file(output_path, course_urls):
    with open(output_path, "w") as f:
        json.dump(course_urls, f, indent = 4)

def main():
    url = "https://www.zhaw.ch/de/hochschule/"
    identifying_id = "ce-at-a-glance"
    output_path = "course_urls.json"
    course_urls = asyncio.run(scrap_course_data(url, identifying_id))
    write_to_file(output_path, course_urls)

if __name__ == "__main__":
    main()
