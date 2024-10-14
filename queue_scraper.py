import json
from urllib.parse import urljoin, urlparse
import aiohttp
import asyncio
import queue
from bs4 import BeautifulSoup


async def scrap_course_data(root_url, identifying_id) -> list[str]:
    course_urls = []
    urls = queue.Queue()
    checked_urls = set()
    urls.put(root_url)
    checked_urls.add(root_url)

    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=60)
        ) as session:
            while not urls.empty():
                cur_url = urls.get()
                try:
                    async with session.get(cur_url) as response:
                        html = ""
                        if response.status == 200:
                            # utf-8 encoding error on some sites
                            try:
                                html = await response.text()
                            except:
                                continue
                        else:
                            print(
                                "Failed to retrieve the webpage. Status code:",
                                response.status,
                                cur_url,
                            )
                            continue
                except aiohttp.ClientError as e:
                    print(f"Client error: {e}")
                    continue
                except Exception as e:
                    print(f"Exception :{e} \n url: {cur_url}")
                    continue

                soup = BeautifulSoup(html, "lxml")

                if soup.find(id=identifying_id) != None:
                    course_urls.append(cur_url)
                    print(cur_url)

                for tag in soup.find_all("a"):
                    # avoid sites like https://examplesite.com/page#section
                    href = tag.get("href")
                    if href == None:
                        continue
                    href = href.split("#")[0]

                    # to avoid leaving the main site (dont want to go to facebook or something)
                    full_url = urljoin(cur_url, href)
                    base_url = urlparse(full_url).netloc
                    orig_base_url = urlparse(root_url).netloc
                    if base_url != orig_base_url:
                        continue

                    if not (full_url in checked_urls):
                        checked_urls.add(full_url)
                        urls.put(full_url)
        return course_urls
    except asyncio.TimeoutError:
        return course_urls


def write_to_file(output_path, course_urls):
    with open(output_path, "w") as f:
        json.dump(course_urls, f, indent=4)


def read_file(path):
    with open(path) as f:
        return json.load(f)


def process_urls(data):
    for uni in data:
        name = uni["name"]
        url = uni["url"]
        identifier = uni["identifier"]
        course_urls = asyncio.run(scrap_course_data(url, identifier))
        output_path = f"{name}.json"
        write_to_file(output_path, course_urls)


def main():
    json_path = "data.json"
    data = read_file(json_path)
    process_urls(data)


if __name__ == "__main__":
    main()
