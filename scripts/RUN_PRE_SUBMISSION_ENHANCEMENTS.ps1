param(
    [ValidateSet("reports", "hosting-smoke", "hosting-formal", "alibaba-smoke", "alibaba-formal", "all-formal")]
    [string]$Mode = "reports",
    [string]$Python = "python",
    [string]$AlibabaArchive = "",
    [string]$Device = "cuda",
    [string]$SafeMode = "gru-native",
    [string]$HostLabel = "laptop_cpu_gpu"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$EnhRoot = "outputs/pre_submission_enhancements_d2904_t2904"
$Prepared = Join-Path $EnhRoot "alibaba_domain/prepared/real_trace_domain_manifest.json"
$BankDir = Join-Path $EnhRoot "alibaba_domain/bank"
$DomainResult = Join-Path $EnhRoot "alibaba_domain/alibaba_domain_result.json"
$HostingResult = Join-Path $EnhRoot "hosting/hosting_profile.json"
$ReportDir = Join-Path $EnhRoot "report"

function Run-Reports {
    & $Python ".\scripts\generate_pre_submission_reports.py" `
        --project-root "." `
        --output-root $ReportDir
}

function Run-Hosting([bool]$Smoke) {
    $args = @(
        ".\scripts\run_hosting_profile.py",
        "--project-root", ".",
        "--out", $HostingResult,
        "--devices", "cpu,cuda",
        "--safe-mode", $SafeMode,
        "--host-label", $HostLabel
    )
    if ($Smoke) { $args += "--smoke" }
    & $Python @args
}

function Ensure-AlibabaPrepared {
    if ([string]::IsNullOrWhiteSpace($AlibabaArchive)) {
        throw "AlibabaArchive is required for Alibaba modes."
    }
    if (-not (Test-Path $Prepared)) {
        & $Python ".\scripts\prepare_alibaba_domain_trace.py" `
            --input $AlibabaArchive `
            --out-dir (Split-Path -Parent $Prepared)
    }
}

function Run-Alibaba([bool]$Smoke) {
    Ensure-AlibabaPrepared
    $bankArgs = @(
        ".\scripts\build_alibaba_domain_bank.py",
        "--project-root", ".",
        "--manifest", $Prepared,
        "--out-dir", $BankDir,
        "--device", $Device,
        "--safe-mode", $SafeMode
    )
    $evalArgs = @(
        ".\scripts\run_alibaba_domain_calibration.py",
        "--project-root", ".",
        "--manifest", $Prepared,
        "--bank-dir", $BankDir,
        "--out", $DomainResult,
        "--device", $Device,
        "--safe-mode", $SafeMode
    )
    if ($Smoke) {
        $bankArgs += "--smoke"
        $evalArgs += "--smoke"
    }
    & $Python @bankArgs
    & $Python @evalArgs
}

switch ($Mode) {
    "reports"        { Run-Reports }
    "hosting-smoke"  { Run-Hosting $true; Run-Reports }
    "hosting-formal" { Run-Hosting $false; Run-Reports }
    "alibaba-smoke"  { Run-Alibaba $true; Run-Reports }
    "alibaba-formal" { Run-Alibaba $false; Run-Reports }
    "all-formal"     { Run-Hosting $false; Run-Alibaba $false; Run-Reports }
}
