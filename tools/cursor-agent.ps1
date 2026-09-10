param(
    [Parameter(Position=0)][ValidateSet('doctor','review','dry-run')][string]$Action = 'doctor',
    [string]$Task = '',
    [ValidateSet('low','medium','high','xhigh')][string]$Effort = 'medium',
    [switch]$Fast
)
$ErrorActionPreference = 'Stop'
$runner = Join-Path $PSScriptRoot 'agents/runner.mjs'
if (!(Test-Path $runner)) { throw 'Cursor runner is not installed' }
$credentialPath = Join-Path $env:LOCALAPPDATA 'IGVCSim/cursor-key.dpapi'
$previousKey = $env:CURSOR_API_KEY
$previousEffort = $env:IGVC_CURSOR_EFFORT
$previousFast = $env:IGVC_CURSOR_FAST
try {
    $env:IGVC_CURSOR_EFFORT = $Effort
    $env:IGVC_CURSOR_FAST = $Fast.IsPresent.ToString().ToLowerInvariant()
    if ($Action -ne 'dry-run' -and !$env:CURSOR_API_KEY) {
        if (!(Test-Path $credentialPath)) { throw 'Set CURSOR_API_KEY locally or configure the encrypted Windows credential.' }
        $encrypted = (Get-Content -LiteralPath $credentialPath -Raw).Trim() | ConvertTo-SecureString
        $env:CURSOR_API_KEY = [System.Net.NetworkCredential]::new('', $encrypted).Password
    }
    $runnerArgs = @($runner, $Action)
    if ($Task) { $runnerArgs += @('--task', $Task) }
    & node @runnerArgs
    if ($LASTEXITCODE -ne 0) { throw "Cursor job failed ($LASTEXITCODE); inspect its report." }
} finally {
    $env:CURSOR_API_KEY = $previousKey
    $env:IGVC_CURSOR_EFFORT = $previousEffort
    $env:IGVC_CURSOR_FAST = $previousFast
    Remove-Variable encrypted -ErrorAction SilentlyContinue
}
