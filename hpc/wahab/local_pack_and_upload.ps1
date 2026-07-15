param(
    [string]$Midas = "pierpogb",
    [string]$HostName = "wahab.hpc.odu.edu",
    [string]$RemoteProject = "/home/pierpogb/EpilepsyMortalityOptionB",
    [switch]$IncludeOutputs,
    [switch]$SkipUnpack
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Get-Location).Path
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$TempRoot = Join-Path $env:TEMP "EpilepsyMortalityOptionB_upload_$Timestamp"
$StageRoot = Join-Path $TempRoot "EpilepsyMortalityOptionB"
$Archive = Join-Path $env:TEMP "EpilepsyMortalityOptionB_$Timestamp.zip"
$RemoteUploads = "~/EpilepsyMortalityOptionB_uploads"

if (-not (Test-Path (Join-Path $ProjectRoot "hpc\wahab\submit_pipeline.sh"))) {
    throw "Run this script from the project root: C:\Research\EpilepsyMortalityOptionB"
}

New-Item -ItemType Directory -Force -Path $StageRoot | Out-Null
$excludedDirs = @(".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "wahab_results")
if (-not $IncludeOutputs) {
    $excludedDirs += "outputs"
}

Get-ChildItem -LiteralPath $ProjectRoot -Recurse -Force -File | ForEach-Object {
    $relative = $_.FullName.Substring($ProjectRoot.Length).TrimStart("\")
    $parts = $relative -split "\\"
    if ($parts | Where-Object { $excludedDirs -contains $_ }) {
        return
    }
    if ($_.Name -like "~$*" -or $_.Name -eq "Thumbs.db" -or $_.Name.EndsWith(".tmp")) {
        return
    }
    $target = Join-Path $StageRoot $relative
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null; Copy-Item -LiteralPath param(
    [string]$Midas = "pierpogb",
    [string]$HostName = "wahab.hpc.odu.edu",
    [string]$RemoteProject = "/home/pierpogb/EpilepsyMortalityOptionB",
    [switch]$IncludeOutputs,
    [switch]$SkipUnpack
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Get-Location).Path
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$TempRoot = Join-Path $env:TEMP "EpilepsyMortalityOptionB_upload_$Timestamp"
$StageRoot = Join-Path $TempRoot "EpilepsyMortalityOptionB"
$Archive = Join-Path $env:TEMP "EpilepsyMortalityOptionB_$Timestamp.zip"
$RemoteUploads = "~/EpilepsyMortalityOptionB_uploads"

if (-not (Test-Path (Join-Path $ProjectRoot "hpc\wahab\submit_pipeline.sh"))) {
    throw "Run this script from the project root: C:\Research\EpilepsyMortalityOptionB"
}

New-Item -ItemType Directory -Force -Path $StageRoot | Out-Null
$excludedDirs = @(".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "wahab_results")
if (-not $IncludeOutputs) {
    $excludedDirs += "outputs"
}

Get-ChildItem -LiteralPath $ProjectRoot -Recurse -Force -File | ForEach-Object {
    $relative = $_.FullName.Substring($ProjectRoot.Length).TrimStart("\")
    $parts = $relative -split "\\"
    if ($parts | Where-Object { $excludedDirs -contains $_ }) {
        return
    }
    if ($_.Name -like "~$*" -or $_.Name -eq "Thumbs.db" -or $_.Name.EndsWith(".tmp")) {
        return
    }
    $target = Join-Path $StageRoot $relative
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
    Copy-Item -LiteralPath $_.FullName -Destination $target -Force
}

if (Test-Path $Archive) {
    Remove-Item -LiteralPath $Archive -Force
}
Compress-Archive -Path (Join-Path $StageRoot "*") -DestinationPath $Archive -Force

ssh "$Midas@$HostName" "mkdir -p $RemoteUploads $RemoteProject"
scp "$Archive" "${Midas}@${HostName}:$RemoteUploads/"

if (-not $SkipUnpack) {
    $RemoteArchive = "$RemoteUploads/$(Split-Path -Leaf $Archive)"
    ssh "$Midas@$HostName" "mkdir -p $RemoteProject && python3 -m zipfile -e $RemoteArchive $RemoteProject"
}

Remove-Item -LiteralPath $TempRoot -Recurse -Force

Write-Host "archive=$Archive"
Write-Host "uploaded_to=${Midas}@${HostName}:$RemoteUploads/"
Write-Host ""
Write-Host "Next SSH commands:"
Write-Host "ssh $Midas@$HostName"
Write-Host "cd $RemoteProject"
Write-Host "bash hpc/wahab/bootstrap_env.sh"
Write-Host "bash hpc/wahab/stage_to_scratch.sh"
Write-Host "bash hpc/wahab/submit_pipeline.sh"
.FullName -Destination $target -Force
}

if (Test-Path $Archive) {
    Remove-Item -LiteralPath $Archive -Force
}
Compress-Archive -Path (Join-Path $StageRoot "*") -DestinationPath $Archive -Force

ssh "$Midas@$HostName" "mkdir -p $RemoteUploads $RemoteProject"
scp "$Archive" "${Midas}@${HostName}:$RemoteUploads/"

if (-not $SkipUnpack) {
    $RemoteArchive = "$RemoteUploads/$(Split-Path -Leaf $Archive)"
    ssh "$Midas@$HostName" "mkdir -p $RemoteProject && python3 -m zipfile -e $RemoteArchive $RemoteProject"
}

Remove-Item -LiteralPath $TempRoot -Recurse -Force

Write-Host "archive=$Archive"
Write-Host "uploaded_to=${Midas}@${HostName}:$RemoteUploads/"
Write-Host ""
Write-Host "Next SSH commands:"
Write-Host "ssh $Midas@$HostName"
Write-Host "cd $RemoteProject"
Write-Host "bash hpc/wahab/bootstrap_env.sh"
Write-Host "bash hpc/wahab/stage_to_scratch.sh"
Write-Host "bash hpc/wahab/submit_pipeline.sh"

