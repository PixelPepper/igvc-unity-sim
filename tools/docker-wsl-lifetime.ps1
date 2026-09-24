# Keep WSL-hosted Docker alive after the short-lived Compose client exits.
# Only stop a helper whose PID, start time and executable still match our record.
function Get-IgvcWslKeeper {
    if (!(Test-Path -LiteralPath $script:igvcKeeperState)) { return $null }
    try {
        $saved = Get-Content -LiteralPath $script:igvcKeeperState -Raw | ConvertFrom-Json
        $process = Get-Process -Id $saved.pid -ErrorAction SilentlyContinue
        if ($process -and $process.Path -eq $saved.executable -and
            $process.StartTime.ToUniversalTime().Ticks -eq ([datetime]$saved.start).ToUniversalTime().Ticks) {
            return $process
        }
    } catch { }
    return $null
}

function Start-IgvcWslKeeper {
    if (Get-IgvcWslKeeper) { return }
    $executable = (Get-Command wsl.exe -ErrorAction Stop).Source
    $process = Start-Process -FilePath $executable -ArgumentList '-d Ubuntu-24.04 -u root -- sleep infinity' -WindowStyle Hidden -PassThru
    New-Item -ItemType Directory -Force (Split-Path $script:igvcKeeperState) | Out-Null
    @{pid=$process.Id; executable=$process.Path; start=$process.StartTime.ToUniversalTime().ToString('o')} |
        ConvertTo-Json | Set-Content -LiteralPath $script:igvcKeeperState
}

function Stop-IgvcWslKeeper {
    $process = Get-IgvcWslKeeper
    if ($process) { Stop-Process -Id $process.Id }
    if (Test-Path -LiteralPath $script:igvcKeeperState) {
        Remove-Item -LiteralPath $script:igvcKeeperState
    }
}
