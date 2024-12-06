from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from app.core import logger


@dataclass
class ExtractionRule:
    name: str
    primary_selector: str
    fallback_selectors: List[str]
    data_type: str
    is_mandatory: bool = False
    nested_fields: Optional[List["ExtractionRule"]] = None


class DataExtractor:
    def __init__(self, target_fields: List):
        """Initialize extractor with schema"""
        self.target_fields = target_fields
        self.extraction_rules = self._create_extraction_rules()

    def _create_extraction_rules(
        self, nested_fields: Optional[List[Dict]] = None
    ) -> List[ExtractionRule]:
        """Convert schema into extraction rules with validation"""
        rules = []
        fields = nested_fields if nested_fields else self.target_fields

        for field in fields:
            if not self._validate_selector(field["primary_selector"]):
                logger.debug(
                    f"Invalid primary selector '{field['primary_selector']}' for field '{field['name']}'. Checking fallbacks."
                )
                valid_selector = self._get_valid_fallback(
                    field.get("fallback_selectors", [])
                )
                if not valid_selector:
                    logger.debug(
                        f"No valid selectors found for field '{field['name']}'. Skipping."
                    )
                    continue
                field["primary_selector"] = valid_selector

            nested_fields = None
            if field.get("nested_fields"):
                nested_fields = self._create_extraction_rules(field["nested_fields"])

            rule = ExtractionRule(
                name=field["name"],
                primary_selector=field["primary_selector"],
                fallback_selectors=field.get("fallback_selectors", []),
                data_type=field["data_type"],
                is_mandatory=field.get("is_mandatory", False),
                nested_fields=nested_fields,
            )
            rules.append(rule)
        return rules

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
            logger.debug(f"Failed to convert value '{value}' to type {data_type}")
            return None

    def _extract_fields(
        self, element: BeautifulSoup, rules: Optional[List[ExtractionRule]] = None
    ) -> Optional[Dict[str, Any]]:
        """Extract fields recursively and fail fast if a mandatory field is missing"""
        data = {}
        current_rules = rules if rules is not None else self.extraction_rules

        for rule in current_rules:
            target = element.select_one(rule.primary_selector)

            if not target and rule.fallback_selectors:
                for selector in rule.fallback_selectors:
                    if self._validate_selector(selector):
                        target = element.select_one(selector)
                        if target:
                            break

            if not target:
                if rule.is_mandatory:
                    logger.debug(
                        f"Failed to extract mandatory field '{rule.name}'. No valid selectors."
                    )
                    return None
                continue

            if rule.nested_fields:
                nested_data = self._extract_fields(target, rule.nested_fields)
                if nested_data is None and rule.is_mandatory:
                    return None
                if nested_data:
                    data[rule.name] = nested_data
            else:
                value = target.get_text(strip=True)
                converted_value = self._convert_value(value, rule.data_type)
                if converted_value is None and rule.is_mandatory:
                    logger.debug(
                        f"Failed to convert mandatory field '{rule.name}' value"
                    )
                    return None
                if converted_value is not None:
                    data[rule.name] = converted_value
                    logger.debug(
                        f"Extracted value for '{rule.name}': {converted_value}"
                    )

        return data

    def extract_data(self, html_content: str) -> Optional[Dict[str, Any]]:
        """Extract data from HTML content using the schema"""
        soup = BeautifulSoup(html_content, "lxml")
        return self._extract_fields(soup)


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
