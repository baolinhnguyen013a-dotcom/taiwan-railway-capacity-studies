# railML 3.2 Evaluation & Conformance Classification Report

## Overview
This report evaluates the status of the two railML data files within the repository:
1. `01_alignment_topology/railml_infrastructure_east_section.xml`
2. `03_rolling_stock_signalling/railml_rollingstock_hitachi_emu.xml`

## Schema Definitions & Claimed Namespaces
- **Claimed Standard**: railML version 3.2
- **Namespace**: `https://www.railml.org/schemas/3.2`
- **Dublin Core Metadata**: `http://purl.org/dc/elements/1.1/`
- **XML Schema Instance**: `http://www.w3.org/2001/XMLSchema-instance`

## Evaluation Findings & Independent Verification

### 1. XML Well-Formedness (VERIFIED)
- `railml_infrastructure_east_section.xml` parses successfully with XML 1.0 parsers. Root tag: `<railML xmlns="https://www.railml.org/schemas/3.2" version="3.2">`.
- `railml_rollingstock_hitachi_emu.xml` parses successfully with XML 1.0 parsers. Root tag: `<railML xmlns="https://www.railml.org/schemas/3.2" version="3.2">`.

### 2. XSD Schema Validation (NOT PERFORMED - NO XSD BUNDLE/RUN/LOG)
- **XSD Bundle**: No official railML 3.2 XSD schema files (`.xsd`) are present in the repository.
- **Validation Run**: No XSD validator executable or automated schema test has been executed against schema definitions.
- **Validation Log**: No schema validation execution log exists.
- Consequently, claims of formal railML 3.2 schema compliance are **unsupported**.

## Conformance Classification: XML_WELL_FORMED_ONLY

Both files are classified as **`XML_WELL_FORMED_ONLY`**. They cannot be certified as schema-conformant or analysis-ready for external railML toolchains without an official XSD bundle and validation log. Finding F-010 remains OPEN / UNVERIFIED at the schema level.
