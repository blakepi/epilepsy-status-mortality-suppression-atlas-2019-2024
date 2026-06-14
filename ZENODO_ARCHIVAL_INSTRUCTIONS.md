# Zenodo Archival Instructions

## GitHub Repository

Repository URL: https://github.com/blakepi/epilepsy-status-mortality-suppression-atlas-2019-2024

Release tag: v1.0.0

## Recommended Zenodo Metadata

Title: Suppression-Aware County-Level Epilepsy and Status Epilepticus Mortality in the United States, 2019-2024

Upload type: Software

Version: 1.0.0

Creator:

- Gregory Pierpoint, B.S.
- ORCID: https://orcid.org/0000-0001-8288-8549
- Affiliation: Macon & Joan Brock Virginia Health Sciences, Eastern Virginia Medical School at Old Dominion University
- Email: pierpogb@odu.edu

Recommended description:

Code, processed aggregate data, tables, figures, and documentation for a suppression-aware county-level analysis of epilepsy/status epilepticus mortality in the United States, 2019-2024. The repository preserves CDC WONDER exact, suppressed, and explicit zero county cells as distinct statuses and evaluates rurality-associated mortality patterns using observed-only models, bias-bounding scenarios, residual-allocation analyses, and interval-likelihood negative binomial models. No person-level data are included.

Recommended keywords:

- epilepsy
- status epilepticus
- mortality
- CDC WONDER
- small-cell suppression
- rural health
- ecological study
- county-level atlas

Recommended license language:

- Code: MIT License
- Documentation, derived aggregate tables, and figures: CC BY 4.0 unless otherwise noted
- Underlying source data remain subject to original source terms and citation requirements

## GitHub-Zenodo Integration Steps

1. Sign in to Zenodo with the account that should own the archive.
2. Open the Zenodo GitHub integration page.
3. Enable repository access for `blakepi/epilepsy-status-mortality-suppression-atlas-2019-2024`.
4. Confirm that the GitHub release `v1.0.0` is visible to Zenodo.
5. If Zenodo does not import the release automatically, trigger archival from the GitHub integration page after the GitHub release exists.
6. Review the imported metadata and apply the recommended title, creator, description, keywords, version, and license fields above.
7. Publish the Zenodo record.
8. Copy the Zenodo identifiers back into the manuscript package and repository metadata.

## Fields to Copy Back

- Zenodo version DOI:
- Zenodo concept DOI:

## After Zenodo Publication

Update the README citation section and `CITATION.cff` with the Zenodo DOI values, then create a follow-up repository commit and, if needed, a small patch release.
