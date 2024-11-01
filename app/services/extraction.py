from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from bs4 import BeautifulSoup

from app.core.config import logger


@dataclass
class ExtractionRule:
    name: str
    primary_selector: str
    fallback_selectors: List[str]
    data_type: str
    nested_fields: Optional[List["ExtractionRule"]] = None


class DataExtractor:
    def __init__(self, target_fields: List):
        """Initialize extractor with schema"""
        self.target_fields = target_fields
        self.extraction_rules, self.total_fields = self._create_extraction_rules()

    def _create_extraction_rules(
        self, nested_fields: Optional[List[Dict]] = None
    ) -> Tuple[List[ExtractionRule], int]:
        """Convert schema into extraction rules with validation"""
        rules = []
        count = 0
        fields = nested_fields if nested_fields else self.target_fields
        for field in fields:
            if not self._validate_selector(field["primary_selector"]):
                logger.warning(
                    f"Invalid primary selector '{field['primary_selector']}' for field '{field['name']}'. Checking fallbacks."
                )
                valid_selector = self._get_valid_fallback(
                    field.get("fallback_selectors", [])
                )
                if not valid_selector:
                    logger.warning(
                        f"No valid selectors found for field '{field['name']}'. Skipping."
                    )
                    count += 1
                    continue
                field["primary_selector"] = valid_selector

            nested_fields = None
            if field.get("nested_fields"):
                nested_fields, nested_count = self._create_extraction_rules(
                    field["nested_fields"]
                )
                count += nested_count
            else:
                count += 1

            rule = ExtractionRule(
                name=field["name"],
                primary_selector=field["primary_selector"],
                fallback_selectors=field.get("fallback_selectors", []),
                data_type=field["data_type"],
                nested_fields=nested_fields,
            )
            rules.append(rule)
        return rules, count

    def _validate_selector(self, selector: str) -> bool:
        """Validate if a CSS selector is syntactically correct"""
        if not selector or not isinstance(selector, str):
            return False
        try:
            soup = BeautifulSoup("<html></html>", "lxml")
            soup.select(selector)
            return True
        except ValueError:
            return False

    def _get_valid_fallback(self, fallback_selectors: List[str]) -> Optional[str]:
        """Find first valid selector from fallback list"""
        for selector in fallback_selectors:
            if self._validate_selector(selector):
                return selector
        return None

    def _convert_value(self, value: str, data_type: str) -> Any:
        """Convert extracted string value to specified data type"""
        try:
            if data_type == "integer":
                return int("".join(filter(str.isdigit, value)))
            elif data_type == "float":
                return float("".join(filter(lambda x: x.isdigit() or x == ".", value)))
            elif data_type == "boolean":
                return value.lower() in ["true", "yes", "1"]
            return value
        except (ValueError, TypeError):
            logger.warning(f"Failed to convert value '{value}' to type {data_type}")
            return None

    def _extract_fields(
        self, element: BeautifulSoup, rules: Optional[List[ExtractionRule]] = None
    ) -> Tuple[Dict[str, Any], int]:
        """Extract fields recursively similar to _create_extraction_rules"""
        data = {}
        extracted_count = 0

        current_rules = rules if rules is not None else self.extraction_rules

        for rule in current_rules:
            logger.debug(
                f"Extracting field '{rule.name}' using primary selector '{rule.primary_selector}'"
            )
            target = element.select_one(rule.primary_selector)

            if not target and rule.fallback_selectors:
                logger.debug(
                    f"Primary selector failed for field '{rule.name}'. Trying fallbacks."
                )
                for selector in rule.fallback_selectors:
                    if self._validate_selector(selector):
                        target = element.select_one(selector)
                        if target:
                            logger.debug(
                                f"Found valid fallback '{selector}' for '{rule.name}'"
                            )
                            break

            if not target:
                logger.warning(
                    f"Failed to extract field '{rule.name}'. No valid selectors."
                )
                continue

            if rule.nested_fields:
                nested_data, nested_count = self._extract_fields(
                    target, rule.nested_fields
                )
                if nested_data:
                    data[rule.name] = nested_data
                    extracted_count += nested_count
            else:
                value = target.get_text(strip=True)
                converted_value = self._convert_value(value, rule.data_type)
                if converted_value is not None:
                    data[rule.name] = converted_value
                    extracted_count += 1
                    logger.debug(
                        f"Extracted value for '{rule.name}': {converted_value}"
                    )

        return data, extracted_count

    def extract_data(self, html_content: str) -> Optional[Dict[str, Any]]:
        """Extract data from HTML content using the schema"""
        soup = BeautifulSoup(html_content, "lxml")
        data, total_extracted_fields = self._extract_fields(soup)

        if total_extracted_fields >= (self.total_fields * 0.75):
            return data
        return None


async def extract_data_from_html(
    html_content: str, target_fields: List
) -> Optional[Dict[str, Any]]:
    """Main function to extract data from HTML using a schema"""
    try:
        extractor = DataExtractor(target_fields)
        return extractor.extract_data(html_content)
    except Exception as e:
        logger.error(f"Error during data extraction: {e}")
        return None
