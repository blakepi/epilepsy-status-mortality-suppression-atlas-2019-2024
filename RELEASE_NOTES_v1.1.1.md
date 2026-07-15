# v1.1.1 — Archive checksum preservation patch

This packaging-only patch does not change the analysis, posterior draws, diagnostics, manuscript results, tables, or figures from v1.1.0.

It adds a targeted `.gitattributes` rule so the checksum-gated eight-chain production evidence is preserved byte-for-byte across local, GitHub, and Zenodo archives. It also regenerates `repository_file_checksums.csv` from the Git archive blobs, excluding the manifest itself.

Validation for this patch requires:

- GitHub and Zenodo archives contain identical relative file trees and file contents.
- `outputs/bayes_constrained/production_8chain/derived_artifact_manifest.csv` passes 62 of 62 checks inside the extracted archive.
- `repository_file_checksums.csv` passes for every listed archive file.
- The public convergence gate remains `finalize`; tests and submission QC remain unchanged from v1.1.0.
