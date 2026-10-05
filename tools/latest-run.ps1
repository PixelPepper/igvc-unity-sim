param([switch]$SmokeTest)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $repoRoot
$lease = $null
$ownsRuntime = $false
$launchFailure = $null
function Wsl-Checked([string[]]$CommandArgs) {
    & wsl -d Ubuntu-24.04 -- @CommandArgs
    if ($LASTEXITCODE -ne 0) { throw "WSL command failed ($LASTEXITCODE): $($CommandArgs[0])" }
}
try {
    $linuxRoot = (& wsl -d Ubuntu-24.04 -- wslpath -a $repoRoot).Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Ubuntu-24.04 is unavailable.' }
    $wslUserHome = (& wsl -d Ubuntu-24.04 -- printenv HOME).Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Cannot locate the WSL home directory.' }
    $env:IGVC_ROS_WORKSPACE = "$wslUserHome/igvc_ws"
    $env:IGVC_ROS_DOMAIN_ID = '42'
    $env:WSLENV = (@($env:WSLENV -split ':' | Where-Object { $_ -and $_ -notmatch '^IGVC_ROS_(WORKSPACE|DOMAIN_ID)(/.*)?$' }) + @('IGVC_ROS_WORKSPACE','IGVC_ROS_DOMAIN_ID')) -join ':'
    $lockDir = Join-Path $repoRoot 'artifacts/iterations'
    New-Item -ItemType Directory -Force -Path $lockDir | Out-Null
    try { $lease = [IO.File]::Open((Join-Path $lockDir 'live.lock'), 'OpenOrCreate', 'ReadWrite', 'None') }
    catch { throw 'A simulation trial owns this session. Wait for it to finish before opening the shortcut.' }
    if (@(Get-Process IGVCProbe,R3aDrive,IGVCCourse,IGVCTerrain,IGVCSandbox -ErrorAction SilentlyContinue).Count) {
        throw 'A simulator is already open. Close its managed session before using this shortcut.'
    }
    $portOwner = & wsl -d Ubuntu-24.04 -- bash -c 'ss -H -ltn sport = :10000'
    if ($LASTEXITCODE -ne 0) { throw 'Could not check the WSL simulator bridge port.' }
    if ($portOwner) { throw 'Bridge port 10000 is occupied. Close the current simulation; if Unity is already closed, run: powershell -NoProfile -ExecutionPolicy Bypass -File tools/igvc.ps1 stop' }
    $profile = "$linuxRoot/docs/evidence/navigation-2026-10-01-success/profile.yaml"
    $assembly = Join-Path $repoRoot 'artifacts/build-course/IGVCCourse_Data/Managed/Assembly-CSharp.dll'
    if (!(Test-Path -LiteralPath $assembly)) { throw 'Course player missing. Run tools/igvc.ps1 course-build first.' }
    Write-Host 'Checking installed perception code...'
    & wsl -d Ubuntu-24.04 -- bash "$linuxRoot/tools/run_ros.sh" python3 "$linuxRoot/tools/agents/verify_iteration_overlay.py" $linuxRoot $env:IGVC_ROS_WORKSPACE
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'Updating the native ROS workspace to the current source...'
        Wsl-Checked @('bash',"$linuxRoot/tools/build_ros.sh")
        Wsl-Checked @('bash',"$linuxRoot/tools/run_ros.sh",'python3',"$linuxRoot/tools/agents/verify_iteration_overlay.py",$linuxRoot,$env:IGVC_ROS_WORKSPACE)
    }
    Write-Host 'Opening Unity, the successful 6/6 navigation profile, and RViz...'
    $ownsRuntime = $true
    & powershell -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot/igvc.ps1" variant-start -Seed 2027 -Difficulty normal -Visible
    if ($LASTEXITCODE -ne 0) { throw 'Unity/ROS startup failed.' }
    Wsl-Checked @('python3',"$linuxRoot/tools/ros_session.py",'start','nav','--params-file',$profile)
    $viewerArgs = @('bash',"$linuxRoot/tools/run_ros.sh",'python3',"$linuxRoot/tools/latest_run_viewer.py")
    if ($SmokeTest) { $viewerArgs += '--smoke-test' }
    Wsl-Checked $viewerArgs
} catch {
    $launchFailure = $_
    Write-Host $_ -ForegroundColor Red
} finally {
    if ($ownsRuntime) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot/igvc.ps1" stop
        if ($LASTEXITCODE -ne 0) { Write-Warning 'Session shutdown failed. Inspect tools/igvc.ps1 status before restarting.' }
    }
    if ($lease) { $lease.Dispose() }
}
# Release runtime ownership before waiting at an error prompt.
if ($launchFailure) {
    if (!$SmokeTest) { Read-Host 'Press Enter to close this launcher' | Out-Null }
    exit 1
}
