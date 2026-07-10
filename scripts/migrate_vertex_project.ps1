param(
    [string]$OldProjectId = "project-c779f701-1a49-4a58-b54",
    [string]$OldBucket = "project-c779f701-1a49-4a58-b54-agorasim",
    [string]$OldConfig = "default",
    [string]$NewProjectId = "project-82d97cf9-5889-43a4-850",
    [string]$NewAccount = "jjjsresearch@gmail.com",
    [string]$NewConfig = "agorasim-new",
    [string]$Region = "us-central1",
    [string]$Repo = "agorasim",
    [string]$NewBucket = "",
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

if (-not $NewBucket) {
    $NewBucket = "$NewProjectId-agorasim"
}

$oldPrefix = "gs://$OldBucket"
$newPrefix = "gs://$NewBucket"
$newImageUri = "$Region-docker.pkg.dev/$NewProjectId/$Repo/worker:latest"
$requiredServices = @(
    "aiplatform.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "compute.googleapis.com",
    "iam.googleapis.com",
    "serviceusage.googleapis.com",
    "storage.googleapis.com"
)

function Invoke-Gcloud {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$GcloudArgs)
    & gcloud @GcloudArgs
    if ($LASTEXITCODE -ne 0) {
        throw "gcloud $($GcloudArgs -join ' ') failed with exit code $LASTEXITCODE"
    }
}

function Test-GcloudSuccess {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$GcloudArgs)
    & gcloud @GcloudArgs *> $null
    return $LASTEXITCODE -eq 0
}

function Replace-TextFile {
    param(
        [string]$Path,
        [string]$OldText,
        [string]$NewText
    )
    $content = Get-Content -LiteralPath $Path -Raw
    $updated = $content.Replace($OldText, $NewText)
    if ($updated -ne $content) {
        Set-Content -LiteralPath $Path -Value $updated -NoNewline
    }
}

Write-Host "== AgoraSim Vertex migration =="
Write-Host "Old: $OldProjectId / $oldPrefix"
Write-Host "New: $NewProjectId / $newPrefix / $NewAccount"

$configs = (& gcloud config configurations list --format="value(name)")
if ($configs -notcontains $NewConfig) {
    Invoke-Gcloud -GcloudArgs @("config", "configurations", "create", $NewConfig, "--no-activate")
}
Invoke-Gcloud -GcloudArgs @("config", "set", "project", $NewProjectId, "--configuration=$NewConfig")
Invoke-Gcloud -GcloudArgs @("config", "set", "account", $NewAccount, "--configuration=$NewConfig")
Invoke-Gcloud -GcloudArgs @("config", "set", "ai/region", $Region, "--configuration=$NewConfig")

$authAccounts = (& gcloud auth list --format="value(account)")
if ($authAccounts -notcontains $NewAccount) {
    Write-Host ""
    Write-Host "ACTION REQUIRED: authenticate the new account, then rerun this script:"
    Write-Host "  gcloud auth login $NewAccount --configuration=$NewConfig --update-adc"
    Write-Host ""
    exit 20
}

Invoke-Gcloud -GcloudArgs @("config", "set", "compute/region", $Region, "--configuration=$NewConfig")
Invoke-Gcloud -GcloudArgs @("projects", "describe", $NewProjectId, "--configuration=$NewConfig", "--format=value(projectId)")

Write-Host "== Enabling APIs in new project =="
$enableServiceArgs = @("services", "enable") + $requiredServices + @("--project=$NewProjectId", "--configuration=$NewConfig")
Invoke-Gcloud -GcloudArgs $enableServiceArgs

Write-Host "== Creating or verifying storage bucket =="
if (-not (Test-GcloudSuccess -GcloudArgs @("storage", "buckets", "describe", $newPrefix, "--configuration=$NewConfig"))) {
    Invoke-Gcloud -GcloudArgs @(
        "storage", "buckets", "create", $newPrefix,
        "--project=$NewProjectId",
        "--location=$Region",
        "--uniform-bucket-level-access",
        "--configuration=$NewConfig"
    )
}

Write-Host "== Creating or verifying Artifact Registry repo =="
if (-not (Test-GcloudSuccess -GcloudArgs @("artifacts", "repositories", "describe", $Repo, "--location=$Region", "--project=$NewProjectId", "--configuration=$NewConfig"))) {
    Invoke-Gcloud -GcloudArgs @(
        "artifacts", "repositories", "create", $Repo,
        "--repository-format=docker",
        "--location=$Region",
        "--description=AgoraSim Vertex worker images",
        "--project=$NewProjectId",
        "--configuration=$NewConfig"
    )
}

Write-Host "== Granting new account read access to old bucket =="
Invoke-Gcloud -GcloudArgs @(
    "storage", "buckets", "add-iam-policy-binding", $oldPrefix,
    "--member=user:$NewAccount",
    "--role=roles/storage.objectViewer",
    "--configuration=$OldConfig",
    "--quiet"
)

Write-Host "== Copying AgoraSim artifacts to new bucket =="
Invoke-Gcloud -GcloudArgs @(
    "storage", "rsync",
    "$oldPrefix/agorasim",
    "$newPrefix/agorasim",
    "--recursive",
    "--configuration=$NewConfig"
)

Write-Host "== Rewriting copied GCS manifests to point at new bucket =="
$tmpRoot = Join-Path $env:TEMP "agorasim_vertex_migration"
New-Item -ItemType Directory -Force -Path $tmpRoot | Out-Null

$snapshotManifest = Join-Path $tmpRoot "G1_SNAPSHOT_MANIFEST.new-gcs.json"
Copy-Item -LiteralPath "docs\G1_SNAPSHOT_MANIFEST.json" -Destination $snapshotManifest -Force
Replace-TextFile -Path $snapshotManifest -OldText $oldPrefix -NewText $newPrefix
Invoke-Gcloud -GcloudArgs @(
    "storage", "cp", $snapshotManifest,
    "$newPrefix/agorasim/snapshots/g1/manifest.json",
    "--configuration=$NewConfig"
)

$modelManifest = Join-Path $tmpRoot "_cache_manifest.json"
Invoke-Gcloud -GcloudArgs @(
    "storage", "cp",
    "$newPrefix/agorasim/models/_cache_manifest.json",
    $modelManifest,
    "--configuration=$NewConfig"
)
Replace-TextFile -Path $modelManifest -OldText $oldPrefix -NewText $newPrefix
Invoke-Gcloud -GcloudArgs @(
    "storage", "cp", $modelManifest,
    "$newPrefix/agorasim/models/_cache_manifest.json",
    "--configuration=$NewConfig"
)

Write-Host "== Granting runtime service accounts access =="
$projectNumber = (& gcloud projects describe $NewProjectId --configuration=$NewConfig --format="value(projectNumber)").Trim()
$computeSa = "$projectNumber-compute@developer.gserviceaccount.com"
$vertexSa = "service-$projectNumber@gcp-sa-aiplatform.iam.gserviceaccount.com"
$cloudBuildSa = "$projectNumber@cloudbuild.gserviceaccount.com"

foreach ($sa in @($computeSa, $vertexSa)) {
    Invoke-Gcloud -GcloudArgs @(
        "storage", "buckets", "add-iam-policy-binding", $newPrefix,
        "--member=serviceAccount:$sa",
        "--role=roles/storage.objectAdmin",
        "--configuration=$NewConfig",
        "--quiet"
    )
    Invoke-Gcloud -GcloudArgs @(
        "artifacts", "repositories", "add-iam-policy-binding", $Repo,
        "--location=$Region",
        "--member=serviceAccount:$sa",
        "--role=roles/artifactregistry.reader",
        "--project=$NewProjectId",
        "--configuration=$NewConfig",
        "--quiet"
    )
}

Invoke-Gcloud -GcloudArgs @(
    "artifacts", "repositories", "add-iam-policy-binding", $Repo,
    "--location=$Region",
    "--member=serviceAccount:$cloudBuildSa",
    "--role=roles/artifactregistry.writer",
    "--project=$NewProjectId",
    "--configuration=$NewConfig",
    "--quiet"
)

if (-not $SkipBuild) {
    Write-Host "== Building and pushing worker image to new project =="
    Invoke-Gcloud -GcloudArgs @(
        "builds", "submit",
        "--config", "cloudbuild.worker.yaml",
        "--project", $NewProjectId,
        "--substitutions=_IMAGE_URI=$newImageUri",
        "--configuration=$NewConfig",
        "."
    )
}

Write-Host "== Updating local launch defaults for future training =="
Replace-TextFile -Path "configs\sim_oos_2025.yaml" `
    -OldText "$oldPrefix/agorasim/snapshots/g1/manifest.json" `
    -NewText "$newPrefix/agorasim/snapshots/g1/manifest.json"
Replace-TextFile -Path "configs\sim_calib_2019.yaml" `
    -OldText "$oldPrefix/agorasim/snapshots/g1/manifest.json" `
    -NewText "$newPrefix/agorasim/snapshots/g1/manifest.json"
Replace-TextFile -Path "scripts\run_sim_phase.py" `
    -OldText "$oldPrefix/agorasim/runs" `
    -NewText "$newPrefix/agorasim/runs"
Replace-TextFile -Path "scripts\run_sim_phase.py" `
    -OldText "$oldPrefix/agorasim/models" `
    -NewText "$newPrefix/agorasim/models"
Replace-TextFile -Path "cloudbuild.worker.yaml" `
    -OldText "us-central1-docker.pkg.dev/$OldProjectId/agorasim/worker:latest" `
    -NewText $newImageUri

Write-Host ""
Write-Host "MIGRATION READY"
Write-Host "New image: $newImageUri"
Write-Host "New run root: $newPrefix/agorasim/runs"
Write-Host "New model root: $newPrefix/agorasim/models"
Write-Host "New snapshot manifest: $newPrefix/agorasim/snapshots/g1/manifest.json"
Write-Host ""
Write-Host "Recommended verification:"
Write-Host "  python -m pytest -q"
Write-Host "  git diff -- configs scripts cloudbuild.worker.yaml"
