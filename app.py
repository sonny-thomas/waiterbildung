import asyncio
import json
import logging
from collections import deque
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup, Tag
from openai import OpenAI
from rich import print as rprint
from rich.console import Console
from rich.table import Table

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
console = Console()


@dataclass
class ExtractionRule:
    selector: str
    selector_type: str
    field_name: str
    data_type: str
    nested_fields: Optional[List["ExtractionRule"]] = None


class SchemaGenerator:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)

    async def analyze_page_structure(
        self, html_content: str, target_fields: List[str]
    ) -> Dict:
        """Have OpenAI analyze the page and generate extraction rules, with guidance on nested fields"""
        soup = BeautifulSoup(html_content, "lxml")

        # Create a simplified HTML structure focusing on relevant elements
        simplified_html = self._simplify_html(soup)
        prompt = f"""
        Given this HTML structure and the target fields {target_fields}, 
        create a JSON schema for extracting data. For each field, identify:
        1. The most reliable CSS selector or identifier
        2. Alternative selectors as fallbacks
        3. The data type (string, integer, float, object, array)
        4. For fields marked with nested content, identify their nested fields and nest them in the json, including their CSS selectors and data types.
        5. Ensure that the extraction is robust to changes in the page layout and can handle missing fields gracefully.
        Note: nested this schema is very important and should be the most accurate way to automatically retrieve these fields from the page.
        Ensure that all the nested fields are fetch that even if interchanged we still get the right data.
        
        Example schema:
        {{
            "fields": [
            {{
                "name": "field_name",
                "primary_selector": "CSS selector",
                "fallback_selectors": ["alternative1", "alternative2"],
                "data_type": "type",
                "nested_fields": [
                {{
                    "name": "nested_field_name",
                    "primary_selector": "CSS selector",
                    "fallback_selectors": ["alternative1", "alternative2"],
                    "data_type": "type"
                }}
                ] // if applicable
            }}
            ]
        }}
        
        HTML Structure:
        {simplified_html}
    
        Note: Do not write any text in the response. Just return the JSON schema.
        """

        response = await asyncio.to_thread(
            self.client.chat.completions.create,
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are a web scraping expert. Generate precise CSS selectors and extraction rules.",
                },
                {"role": "user", "content": prompt},
            ],
        )
        print(response)

        schema = json.loads(response.choices[0].message.content)
        return schema

    def _simplify_html(self, soup: BeautifulSoup) -> str:
        """Simplify HTML to focus on structure and identifiers"""
        # Remove scripts, styles, and comments
        for element in soup(["script", "style"]):
            element.decompose()

        simplified = []
        for tag in soup.find_all(True):
            attributes = []
            if tag.get("id"):
                attributes.append(f'id="{tag["id"]}"')
            if tag.get("class"):
                attributes.append(f'class="{" ".join(tag["class"])}"')

            attr_str = " ".join(attributes)
            simplified.append(f"<{tag.name} {attr_str}>")

        return "\n".join(simplified)


class DataExtractor:
    def __init__(self, schema: Dict):
        self.schema = schema
        self.extraction_rules = self._create_extraction_rules()

    def _create_extraction_rules(self) -> List[ExtractionRule]:
        """Convert schema into extraction rules"""
        rules = []
        for field in self.schema["fields"]:
            rule = ExtractionRule(
                selector=field["primary_selector"],
                selector_type="css",
                field_name=field["name"],
                data_type=field["data_type"],
                nested_fields=self._process_nested_fields(
                    field.get("nested_fields", [])
                ),
            )
            rules.append(rule)
        return rules

    def _process_nested_fields(
        self, nested_fields: List
    ) -> Optional[List[ExtractionRule]]:
        if not nested_fields:
            return None
        return [
            ExtractionRule(
                selector=field["primary_selector"],
                selector_type="css",
                field_name=field["name"],
                data_type=field["data_type"],
            )
            for field in nested_fields
        ]

    def extract_data(self, html_content: str) -> Dict[str, Any]:
        """Extract data using the generated schema"""
        soup = BeautifulSoup(html_content, "lxml")
        data = {}

        for rule in self.extraction_rules:
            value = self._extract_field(soup, rule)
            if value is not None:
                data[rule.field_name] = value
                console.print(f"[green]Found {rule.field_name}:[/green] {value}")
            else:
                console.print(f"[yellow]Could not find {rule.field_name}[/yellow]")

        return data

    def _extract_field(self, soup: BeautifulSoup, rule: ExtractionRule) -> Any:
        """Extract a single field using the rule"""
        element = soup.select_one(rule.selector)
        if not element:
            return None

        value = element.get_text(strip=True)

        # Convert to appropriate data type
        if rule.data_type == "integer":
            try:
                return int("".join(filter(str.isdigit, value)))
            except ValueError:
                return None
        elif rule.data_type == "float":
            try:
                return float("".join(filter(lambda x: x.isdigit() or x == ".", value)))
            except ValueError:
                return None
        elif rule.data_type == "object" and rule.nested_fields:
            nested_data = {}
            for nested_rule in rule.nested_fields:
                nested_value = self._extract_field(element, nested_rule)
                if nested_value is not None:
                    nested_data[nested_rule.field_name] = nested_value
            return nested_data

        return value


class UniversityScraperWithAISchema:
    def __init__(self, base_url: str, target_fields: List[str], openai_api_key: str):
        self.base_url = base_url
        self.target_fields = target_fields
        self.schema_generator = SchemaGenerator(openai_api_key)
        self.data_extractor = None
        self.visited_urls = set()

    def _print_course_details(self, course_data: Dict[str, Any], url: str):
        """Print course details in a formatted table"""
        table = Table(title=f"Course Details - {url}")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="green")

        for field, value in course_data.items():
            if isinstance(value, (dict, list)):
                value = json.dumps(value, indent=2)
            table.add_row(field, str(value))

        console.print(table)
        console.print("=" * 80)

    async def initialize_schema(self, initial_course_url: str):
        """Generate schema from initial course page"""
        console.print(f"[blue]Initializing schema from {initial_course_url}[/blue]")
        async with aiohttp.ClientSession() as session:
            async with session.get(initial_course_url) as response:
                html_content = await response.text()

        schema = await self.schema_generator.analyze_page_structure(
            html_content, self.target_fields
        )

        self.data_extractor = DataExtractor(schema)
        console.print("[green]Schema generated and initialized successfully[/green]")
        return schema

    async def scrape_university(self, max_pages: int = 100):
        """Scrape university courses using the generated schema"""
        if not self.data_extractor:
            raise ValueError("Schema not initialized. Call initialize_schema first.")

        courses = []
        queue = deque([self.base_url])

        console.print(f"[blue]Starting scraping from {self.base_url}[/blue]")
        console.print(f"[blue]Maximum pages to scrape: {max_pages}[/blue]")

        async with aiohttp.ClientSession() as session:
            while queue and len(self.visited_urls) < max_pages:
                url = queue.popleft()
                if url in self.visited_urls:
                    continue

                self.visited_urls.add(url)
                console.print(f"\n[yellow]Processing URL: {url}[/yellow]")

                try:
                    async with session.get(url) as response:
                        if response.status != 200:
                            console.print(
                                f"[red]Failed to fetch {url}: Status {response.status}[/red]"
                            )
                            continue
                        html_content = await response.text()

                    # Extract course data
                    course_data = self.data_extractor.extract_data(html_content)
                    if course_data:
                        course_data["url"] = url
                        courses.append(course_data)
                        self._print_course_details(course_data, url)
                        console.print(
                            f"[green]Successfully extracted course data from {url}[/green]"
                        )
                    else:
                        console.print(f"[yellow]No course data found at {url}[/yellow]")

                    # Find new URLs
                    soup = BeautifulSoup(html_content, "lxml")
                    new_urls = 0
                    for link in soup.find_all("a", href=True):
                        new_url = urljoin(url, link["href"])
                        if (
                            urlparse(new_url).netloc == urlparse(self.base_url).netloc
                            and new_url not in self.visited_urls
                            and new_url not in queue
                        ):
                            queue.append(new_url)
                            new_urls += 1

                    console.print(f"[blue]Found {new_urls} new URLs to process[/blue]")

                except Exception as e:
                    console.print(f"[red]Error processing {url}: {str(e)}[/red]")

        console.print(f"\n[green]Scraping completed![/green]")
        console.print(f"[green]Total pages visited: {len(self.visited_urls)}[/green]")
        console.print(f"[green]Total courses found: {len(courses)}[/green]")
        return courses


async def main():
    target_fields = [
        "program_name",
        "description",
        "key_data.diploma",
        "key_data.ects_points",
        "key_data.study_mode",
        "key_data.teaching_days",
        "key_data.language_of_instruction",
        "key_data.location",
        "key_data.registration_fees.amount",
        "key_data.registration_fees.currency",
        "key_data.registration_fees.period",
        "contact.phone_number",
        "contact.email",
        "contact.address.street",
        "contact.address.city",
        "contact.address.postal_code",
        "contact.address.country",
    ]

    console.print("[blue]Starting the university scraper...[/blue]")

    scraper = UniversityScraperWithAISchema(
        base_url="https://www.fhnw.ch/de/studium/lifesciences/bachelor/umweltwissenschaften-und-technologie",
        target_fields=target_fields,
        openai_api_key="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",
    )

    # Initialize schema from a known course page
    console.print("\n[yellow]Phase 1: Generating Schema[/yellow]")
    schema = await scraper.initialize_schema(
        "https://www.fhnw.ch/de/studium/lifesciences/bachelor/umweltwissenschaften-und-technologie"
    )
    console.print("Generated Schema:", json.dumps(schema, indent=2))

    # Use the schema to scrape all courses
    console.print("\n[yellow]Phase 2: Scraping Courses[/yellow]")
    courses = await scraper.scrape_university()

    # Save results to file
    with open("courses.json", "w", encoding="utf-8") as f:
        json.dump(courses, f, indent=2, ensure_ascii=False)
    console.print(f"\n[green]Saved {len(courses)} courses to courses.json[/green]")


if __name__ == "__main__":
    asyncio.run(main())
