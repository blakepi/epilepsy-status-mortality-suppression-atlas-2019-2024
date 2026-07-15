from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from submission_viz.io import ensure_output_dirs, load_config, write_manifest  # noqa: E402
from submission_viz.manuscript_text import write_reproducibility_manifest  # noqa: E402
from submission_viz.qc import run_qc  # noqa: E402


def _empty_generated_package_root(package_root: Path) -> None:
    expected = (ROOT / "outputs/submission/package").resolve()
    if package_root.resolve() != expected:
        raise SystemExit(f"Refusing to clean unexpected package directory: {package_root}")
    package_root.mkdir(parents=True, exist_ok=True)
    for child in package_root.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def _copy_tree(src: Path, dst: Path) -> list[Path]:
    copied: list[Path] = []
    if not src.exists():
        return copied
    for path in src.rglob("*"):
        if path.is_file():
            rel = path.relative_to(src)
            target = dst / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            copied.append(target)
    return copied


def _copy_final_manuscript_files(manuscript_dir: Path, package_root: Path) -> list[Path]:
    mapping = {
        "manuscript_submission.docx": "manuscript_submission_FINAL.docx",
        "manuscript_submission.md": "manuscript_submission_FINAL.md",
        "supplement_submission.docx": "supplement_submission_FINAL.docx",
        "supplement_submission.md": "supplement_submission_FINAL.md",
        "figure_captions.md": "figure_captions_FINAL.md",
        "data_code_availability.md": "data_code_availability_FINAL.md",
    }
    copied: list[Path] = []
    for src_name, dst_name in mapping.items():
        src = manuscript_dir / src_name
        if src.exists():
            dst = package_root / dst_name
            shutil.copy2(src, dst)
            copied.append(dst)
    return copied


def _copy_strobe(package_root: Path) -> list[Path]:
    candidates = [
        ROOT / "manuscript/final_submission_ready/docx/STROBE_checklist_revised.docx",
        ROOT / "manuscript/final_submission_ready/markdown/STROBE_checklist_revised.md",
    ]
    copied: list[Path] = []
    for src in candidates:
        if src.exists():
            suffix = src.suffix.lower()
            dst = package_root / f"STROBE_checklist_FINAL{suffix}"
            shutil.copy2(src, dst)
            copied.append(dst)
    return copied


def main() -> None:
    config = load_config()
    dirs = ensure_output_dirs(config)
    package_root = dirs["package"].resolve()
    _empty_generated_package_root(package_root)

    copied: list[Path] = []
    copied += _copy_final_manuscript_files(dirs["manuscript"], package_root)
    copied += _copy_tree(dirs["figures"], package_root / "figures")
    copied += _copy_tree(dirs["tables"], package_root / "tables")
    copied += _copy_strobe(package_root)

    readme = package_root / "README_SUBMISSION_PACKAGE_FINAL.md"
    readme.write_text(
        "# Final Submission Package\n\n"
        "This package contains the final Bayesian-constrained manuscript, supplement, figures, tables, captions, "
        "data/code availability statement, STROBE checklist, reproducibility manifest, and QC outputs. Posterior "
        "county-level quantities are constrained model-derived estimates, not observed or recovered suppressed counts.\n",
        encoding="utf-8",
    )
    copied.append(readme)

    manifest = write_reproducibility_manifest(config)
    copied.append(manifest)

    report = run_qc(config, exit_nonzero=False)
    for name in [
        "SUBMISSION_QC_REPORT_FINAL.md",
        "SUBMISSION_QC_REPORT_FINAL.json",
    ]:
        src = dirs["qc"] / name
        if src.exists():
            dst = package_root / name
            shutil.copy2(src, dst)
            copied.append(dst)

    qc_dir = package_root / "qc"
    for name in [
        "SUBMISSION_QC_REPORT_FINAL.md",
        "SUBMISSION_QC_REPORT_FINAL.json",
    ]:
        src = dirs["qc"] / name
        if src.exists():
            dst = qc_dir / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied.append(dst)

    manifest_csv = package_root / "submission_package_file_manifest_FINAL.csv"
    manifest_df = write_manifest([p for p in package_root.rglob("*") if p.is_file()], manifest_csv)
    copied.append(manifest_csv)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_build_dir = ROOT / "outputs/submission/package_zip_build"
    if zip_build_dir.exists():
        shutil.rmtree(zip_build_dir)
    zip_build_dir.mkdir(parents=True, exist_ok=True)
    zip_base = zip_build_dir / f"submission_package_FINAL_{timestamp}"
    zip_path = Path(shutil.make_archive(str(zip_base), "zip", root_dir=package_root))
    final_zip = package_root / zip_path.name
    shutil.move(str(zip_path), final_zip)
    shutil.rmtree(zip_build_dir)

    print(f"package_root={package_root.relative_to(ROOT)}")
    print(f"package_zip={final_zip.relative_to(ROOT)}")
    print(f"package_files={len(manifest_df)}")
    print(f"qc_passed={report['passed']}")
    print(f"stale_phrase_count={report['stale_phrase_count_submission_materials']}")
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
