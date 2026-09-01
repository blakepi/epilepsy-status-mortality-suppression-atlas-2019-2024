from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.data import load_model_frame  # noqa: E402
from bayes_constrained.support_graph import analyze_state_support, overall_support_summary  # noqa: E402


def main() -> None:
    frame = load_model_frame()
    by_state = analyze_state_support(frame)
    overall = overall_support_summary(by_state)
    output_dir = ROOT / "outputs" / "scientific_reports_v2" / "latent_support"
    output_dir.mkdir(parents=True, exist_ok=True)
    by_state.to_csv(output_dir / "latent_support_by_state.csv", index=False)
    (output_dir / "latent_support_summary.json").write_text(
        json.dumps(overall, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# Full-data latent support-graph diagnostics",
        "",
        "The exact-margin free-cell support is represented as a bipartite graph linking counties to years within each state. Two-by-two moves traverse length-four cycles. Edges that belong to a cycle but no length-four cycle require longer alternating moves or another Markov-basis element.",
        "",
        "| Quantity | Value |",
        "| --- | ---: |",
    ]
    for key, value in overall.items():
        lines.append(f"| {key.replace('_', ' ')} | {value:,} |")
    lines.extend(
        [
            "",
            "This is a structural-support diagnostic, not a proof that the full bounded fiber is irreducible. It determines whether the support contains real-data cycle directions that the v1.1.1 length-four move family could not directly traverse.",
        ]
    )
    (output_dir / "latent_support_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(overall, sort_keys=True))


if __name__ == "__main__":
    main()
