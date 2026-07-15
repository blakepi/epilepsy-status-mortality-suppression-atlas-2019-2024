param(
    [string]$Midas = "pierpogb",
    [string]$HostName = "wahab.hpc.odu.edu",
    [string]$RemoteProject = "/home/pierpogb/EpilepsyMortalityOptionB",
    [switch]$Overwrite
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Get-Location).Path
if (-not (Test-Path (Join-Path $ProjectRoot "hpc\wahab\local_fetch_results.ps1"))) {
    throw "Run this script from the project root: C:\Research\EpilepsyMortalityOptionB"
}

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Destination = Join-Path $ProjectRoot "wahab_results\$Timestamp"
if ((Test-Path $Destination) -and (-not $Overwrite)) {
    throw "Destination exists. Re-run with -Overwrite or choose a new timestamped folder: $Destination"
}
New-Item -ItemType Directory -Force -Path $Destination | Out-Null

$RemoteSpec = "$Midas@$HostName"
$items = @(
    "outputs/bayes_constrained/hpc",
    "RUN_BAYES_CONSTRAINED_REPORT.md",
    "tables/bayes_constrained_primary_irrs.csv",
    "tables/bayes_constrained_primary_irrs.xlsx",
    "tables/table_bayes_vs_existing_scenarios.csv",
    "tables/table_bayes_vs_existing_scenarios.xlsx",
    "figures/main",
    "figures/supplement",
    "manuscript/manuscript_main_bayes_constrained.md",
    "manuscript/manuscript_main_bayes_constrained.docx",
    "manuscript/manuscript_main_bayes_constrained_HPC_FINAL.docx",
    "supplement/supplement_bayes_constrained.docx",
    "supplement/supplement_bayes_constrained_HPC_FINAL.docx"
)

foreach ($item in $items) {
    $targetParent = Join-Path $Destination (Split-Path -Parent $item)
    if ($targetParent -and -not (Test-Path $targetParent)) {
        New-Item -ItemType Directory -Force -Path $targetParent | Out-Null
    }
    & scp -r "${RemoteSpec}:$RemoteProject/$item" $targetParent 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "skipped_missing_or_unavailable=$item"
        $global:LASTEXITCODE = 0
    }
}

Write-Host "results_saved_to=$Destination"
