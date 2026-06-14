# API Limitations Report

Generated: 2026-06-13

CDC WONDER API requests are XML-over-HTTP POSTs to:

```text
https://wonder.cdc.gov/controller/datarequest/[database ID]
```

The submitted form field is `request_xml`; data-use restriction acceptance must
also be supplied. The XML request format and valid parameters are specific to
each online database.

Source: https://wonder.cdc.gov/wonder/help/wonder-api.html

## Project Policy

This project uses API mode only for non-location national queries, currently:

- `Q003_national_year_mc_g40_g41_2019_2024`
- `Q013_national_age_year_mc_g40_g41_2019_2024`

The API exporter is template-based. It submits request XML previously exported
from CDC WONDER's `API Options` tab and saved under `data\raw\xml_requests`.
It does not synthesize undocumented D157 XML parameters.

## Location Limitation

CDC WONDER documentation states that only national data are accessible to API
queries for National Vital Statistics System data. Therefore this project does
not attempt API submissions for grouping or limiting by:

- County
- State
- Region
- Division
- Urbanization

Those queries are routed to browser/manual mode.

## Runtime Probe

A direct non-browser HTTP request to `https://wonder.cdc.gov/mcd.html` on
2026-06-13 returned HTTP 403 in this environment. Browser automation may still
work after Playwright is installed; if it does not, the generated manual
instructions are the supported fallback.
