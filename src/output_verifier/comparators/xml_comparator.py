"""XML file comparator using lxml."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from lxml import etree

from output_verifier.constants import (
    MAX_LOGGED_VALUE_LENGTH,
    MAX_REPORTED_DIFFERENCES,
    DifferenceType,
    VerificationStatus,
)
from output_verifier.models import (
    ComparisonDifference,
    ComparisonOptions,
    ComparisonResult,
)

LOGGER = logging.getLogger(__name__)

_SIMPLE_PATH_SEGMENT = re.compile(r"^([A-Za-z_][\w.-]*)(\[\d+\])?$")


def _truncate(value: str | None) -> str:
    if value is None:
        return ""
    if len(value) <= MAX_LOGGED_VALUE_LENGTH:
        return value
    return value[:MAX_LOGGED_VALUE_LENGTH] + "...(truncated)"


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def _qualified_name(element: etree._Element) -> str:
    return str(element.tag)


def _to_local_name_xpath(xpath_expression: str) -> str | None:
    """
    Convert a simple absolute path to a namespace-tolerant local-name XPath.

    Example:
      /LH1StandardClaimsExchange/@CreatedDateTime
    becomes:
      /*[local-name()='LH1StandardClaimsExchange']/@CreatedDateTime
    """
    expression = xpath_expression.strip()
    if not expression.startswith("/"):
        return None
    if "local-name(" in expression or "namespace-uri(" in expression:
        return None

    segments = [segment for segment in expression.split("/") if segment]
    rewritten: list[str] = []
    for segment in segments:
        if segment.startswith("@"):
            rewritten.append(segment)
            continue
        match = _SIMPLE_PATH_SEGMENT.fullmatch(segment)
        if match is None:
            return None
        element_name = match.group(1)
        index_suffix = match.group(2) or ""
        rewritten.append(f"*[local-name()='{element_name}']{index_suffix}")
    return "/" + "/".join(rewritten)


def _node_path(element: etree._Element) -> str:
    segments: list[str] = []
    current: etree._Element | None = element
    while current is not None:
        parent = current.getparent()
        name = _local_name(str(current.tag))
        if parent is None:
            segments.append(name)
            break
        same_name_siblings = [child for child in parent if _local_name(str(child.tag)) == name]
        if len(same_name_siblings) > 1:
            index = same_name_siblings.index(current) + 1
            segments.append(f"{name}[{index}]")
        else:
            segments.append(name)
        current = parent
    return "/" + "/".join(reversed(segments))


def _element_text(element: etree._Element) -> str:
    """
    Return element text for comparison.

    Whitespace-only text is treated as insignificant formatting (indentation /
    line endings between child elements). Meaningful text is preserved exactly
    and is not trimmed.
    """
    if element.text is None:
        return ""
    if element.text.strip() == "":
        return ""
    return element.text


def _xpath_matches(root: etree._Element, xpath_expression: str) -> list:
    try:
        matches = root.xpath(xpath_expression)
    except etree.XPathError as error:
        raise ValueError(f"Invalid XPath '{xpath_expression}': {error}") from error

    if matches:
        return list(matches)

    alternate = _to_local_name_xpath(xpath_expression)
    if alternate is None or alternate == xpath_expression:
        return []

    try:
        matches = root.xpath(alternate)
    except etree.XPathError as error:
        raise ValueError(f"Invalid XPath '{alternate}': {error}") from error

    if matches:
        LOGGER.debug(
            "Ignore XPath %s matched via namespace-tolerant form %s",
            xpath_expression,
            alternate,
        )
    return list(matches)


def _apply_ignore_paths(root: etree._Element, ignored_paths: tuple[str, ...], side: str) -> None:
    for xpath_expression in ignored_paths:
        matches = _xpath_matches(root, xpath_expression)

        if not matches:
            LOGGER.debug(
                "Configured ignore XPath not found in %s XML: %s",
                side,
                xpath_expression,
            )
            continue

        for match in matches:
            if isinstance(match, etree._Element):
                parent = match.getparent()
                if parent is not None:
                    parent.remove(match)
                    LOGGER.debug("Ignored element via XPath %s on %s", xpath_expression, side)
            elif isinstance(match, etree._ElementUnicodeResult):
                # Attribute result from XPath like /Root/@Attr
                attribute_owner = match.getparent()
                attribute_name = match.attrname
                if attribute_owner is not None and attribute_name is not None:
                    if attribute_name in attribute_owner.attrib:
                        del attribute_owner.attrib[attribute_name]
                        LOGGER.debug(
                            "Ignored attribute %s via XPath %s on %s",
                            attribute_name,
                            xpath_expression,
                            side,
                        )
            else:
                LOGGER.warning(
                    "Unsupported XPath match type for ignore path %s on %s: %s",
                    xpath_expression,
                    side,
                    type(match),
                )


def _compare_elements(
    expected: etree._Element,
    actual: etree._Element,
    differences: list[ComparisonDifference],
) -> None:
    if len(differences) >= MAX_REPORTED_DIFFERENCES:
        return

    path = _node_path(expected)

    if _qualified_name(expected) != _qualified_name(actual):
        differences.append(
            ComparisonDifference(
                description=(
                    f"{path}: {DifferenceType.ELEMENT_NAME_MISMATCH.value}. "
                    f"Expected: {_qualified_name(expected)}, Actual: {_qualified_name(actual)}"
                ),
                difference_type=DifferenceType.ELEMENT_NAME_MISMATCH.value,
                expected_value=_qualified_name(expected),
                actual_value=_qualified_name(actual),
                location=path,
            )
        )
        return

    expected_text = _element_text(expected)
    actual_text = _element_text(actual)
    if expected_text != actual_text:
        differences.append(
            ComparisonDifference(
                description=(
                    f"{path}: {DifferenceType.TEXT_MISMATCH.value}. "
                    f"Expected: {_truncate(expected_text)}, Actual: {_truncate(actual_text)}"
                ),
                difference_type=DifferenceType.TEXT_MISMATCH.value,
                expected_value=expected_text,
                actual_value=actual_text,
                location=path,
            )
        )
        if len(differences) >= MAX_REPORTED_DIFFERENCES:
            return

    expected_attributes = dict(expected.attrib)
    actual_attributes = dict(actual.attrib)

    for attribute_name, expected_value in expected_attributes.items():
        if len(differences) >= MAX_REPORTED_DIFFERENCES:
            return
        if attribute_name not in actual_attributes:
            differences.append(
                ComparisonDifference(
                    description=(
                        f"{path}/@{attribute_name}: {DifferenceType.ATTRIBUTE_MISSING.value}. "
                        f"Expected: {_truncate(expected_value)}, Actual: "
                    ),
                    difference_type=DifferenceType.ATTRIBUTE_MISSING.value,
                    expected_value=expected_value,
                    actual_value="",
                    location=f"{path}/@{attribute_name}",
                )
            )
            continue
        actual_value = actual_attributes[attribute_name]
        if expected_value != actual_value:
            differences.append(
                ComparisonDifference(
                    description=(
                        f"{path}/@{attribute_name}: {DifferenceType.ATTRIBUTE_VALUE_MISMATCH.value}. "
                        f"Expected: {_truncate(expected_value)}, Actual: {_truncate(actual_value)}"
                    ),
                    difference_type=DifferenceType.ATTRIBUTE_VALUE_MISMATCH.value,
                    expected_value=expected_value,
                    actual_value=actual_value,
                    location=f"{path}/@{attribute_name}",
                )
            )

    for attribute_name, actual_value in actual_attributes.items():
        if len(differences) >= MAX_REPORTED_DIFFERENCES:
            return
        if attribute_name not in expected_attributes:
            differences.append(
                ComparisonDifference(
                    description=(
                        f"{path}/@{attribute_name}: {DifferenceType.UNEXPECTED_ATTRIBUTE.value}. "
                        f"Expected: , Actual: {_truncate(actual_value)}"
                    ),
                    difference_type=DifferenceType.UNEXPECTED_ATTRIBUTE.value,
                    expected_value="",
                    actual_value=actual_value,
                    location=f"{path}/@{attribute_name}",
                )
            )

    expected_children = list(expected)
    actual_children = list(actual)
    if len(expected_children) != len(actual_children):
        differences.append(
            ComparisonDifference(
                description=(
                    f"{path}: {DifferenceType.CHILD_COUNT_MISMATCH.value}. "
                    f"Expected: {len(expected_children)}, Actual: {len(actual_children)}"
                ),
                difference_type=DifferenceType.CHILD_COUNT_MISMATCH.value,
                expected_value=str(len(expected_children)),
                actual_value=str(len(actual_children)),
                location=path,
            )
        )
        if len(differences) >= MAX_REPORTED_DIFFERENCES:
            return

    pair_count = min(len(expected_children), len(actual_children))
    for index in range(pair_count):
        if len(differences) >= MAX_REPORTED_DIFFERENCES:
            return
        _compare_elements(expected_children[index], actual_children[index], differences)

    if len(expected_children) > len(actual_children):
        for missing in expected_children[len(actual_children) :]:
            if len(differences) >= MAX_REPORTED_DIFFERENCES:
                return
            missing_path = _node_path(missing)
            differences.append(
                ComparisonDifference(
                    description=(
                        f"{missing_path}: {DifferenceType.ELEMENT_MISSING.value}. "
                        f"Expected: {_qualified_name(missing)}, Actual: "
                    ),
                    difference_type=DifferenceType.ELEMENT_MISSING.value,
                    expected_value=_qualified_name(missing),
                    actual_value="",
                    location=missing_path,
                )
            )
    elif len(actual_children) > len(expected_children):
        for unexpected in actual_children[len(expected_children) :]:
            if len(differences) >= MAX_REPORTED_DIFFERENCES:
                return
            unexpected_path = _node_path(unexpected)
            differences.append(
                ComparisonDifference(
                    description=(
                        f"{unexpected_path}: {DifferenceType.UNEXPECTED_ELEMENT.value}. "
                        f"Expected: , Actual: {_qualified_name(unexpected)}"
                    ),
                    difference_type=DifferenceType.UNEXPECTED_ELEMENT.value,
                    expected_value="",
                    actual_value=_qualified_name(unexpected),
                    location=unexpected_path,
                )
            )


class XmlComparator:
    """Compare XML files structurally using lxml."""

    def compare(
        self,
        expected_path: Path,
        actual_path: Path,
        options: ComparisonOptions,
    ) -> ComparisonResult:
        """Compare two XML files and return the first differences found."""
        try:
            expected_tree = etree.parse(str(expected_path))
            actual_tree = etree.parse(str(actual_path))
        except etree.XMLSyntaxError as error:
            LOGGER.error("Malformed XML while comparing %s and %s: %s", expected_path, actual_path, error)
            return ComparisonResult(
                status=VerificationStatus.FAILED,
                issue=f"XML parsing error: {error}",
            )
        except OSError as error:
            LOGGER.error("Unable to read XML files %s / %s: %s", expected_path, actual_path, error)
            return ComparisonResult(
                status=VerificationStatus.FAILED,
                issue=f"Unable to read XML file: {error}",
            )

        expected_root = expected_tree.getroot()
        actual_root = actual_tree.getroot()

        try:
            _apply_ignore_paths(expected_root, options.ignored_xml_paths, "expected")
            _apply_ignore_paths(actual_root, options.ignored_xml_paths, "actual")
        except ValueError as error:
            # Invalid XPath at runtime is a configuration/system error; re-raise for exit code 2.
            raise

        differences: list[ComparisonDifference] = []
        _compare_elements(expected_root, actual_root, differences)

        if differences:
            LOGGER.info(
                "XML mismatch for %s vs %s (%s differences reported)",
                expected_path.name,
                actual_path.name,
                len(differences),
            )
            return ComparisonResult(
                status=VerificationStatus.FAILED,
                issue="XML content mismatch",
                differences=differences[:MAX_REPORTED_DIFFERENCES],
            )

        LOGGER.debug("XML match for %s vs %s", expected_path.name, actual_path.name)
        return ComparisonResult(status=VerificationStatus.PASSED)
