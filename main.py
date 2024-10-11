import requests
import json
import sys
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

def main():
    sys.setrecursionlimit(3000)
    identifying_id = "ce-at-a-glance"
    f = open("course_urls.json", "w")
    uni_url = "https://www.zhaw.ch/de/hochschule/"
    course_urls = recursive_searching(uni_url, identifying_id)
    json.dump(course_urls, f, indent = 4)
    f.close()


def recursive_searching(url, identifying_id, checked_urls = set(), course_urls = list()):
    response = requests.get(url)
    html = ""
    if (response.status_code == 200):
        html = response.text
    else:
        print("Failed to retrieve the webpage. Status code:", response.status_code)
        return;

    soup = BeautifulSoup(html, "lxml")

    if soup.find(id=identifying_id) != None:
        course_urls.append(url)
        print(url)

    # lxml supposedly faster parser than html.parser
    for tag in soup.find_all("a"):
        tag = tag.get("href")
        if tag == None or tag[0] == "#":
            continue

        full_url = urljoin(url, tag)

        base_url = urlparse(full_url).netloc
        orig_base_url = urlparse(url).netloc
        if base_url != orig_base_url:
            continue

        if not (full_url in checked_urls):
            checked_urls.add(full_url)
            recursive_searching(full_url, identifying_id, checked_urls, course_urls)

    return course_urls




if __name__ == "__main__":
    main()
