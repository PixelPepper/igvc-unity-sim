# Managed launcher for the image-traced reference-map drive player (T-0090). Separate from tools/sandbox.ps1.
#   build : Unity batch -executeMethod ReferenceDriveBuild.Build -> artifacts/build-reference-drive/IGVCReferenceDrive.exe
#   start : mission export + overlay check + managed ROS (ros_session.py r3a) + visible player; runs until closed
#   smoke : as start, for -Seconds (max 180), then stops what it started; no mission is driven
# Holds all three exclusive simulator locks (live, live-instance-1, live-instance-2) for the whole invocation and
# refuses to run if any Unity editor/player, IGVC player or ports 10000-10002 (Windows or WSL) are in use.
# Every run writes to a new artifacts/reference-drive/runs/<utc>-<id>/ directory, kept on failure. Sensor-led mission
# trials are run by ASTRA's root harness (sensor_course.py with this run's autonomy.json); this script never retries.
param(
    [ValidateSet('build','start','smoke')][string]$Action='start',
    [ValidateSet('clear-noon','overcast','low-sun')][string]$Conditions='clear-noon',
    [ValidateRange(10,180)][int]$Seconds=60,
    [ValidateRange(0.1,0.6)][double]$MaxSpeed=0.6,
    [switch]$Hidden
)
$ErrorActionPreference='Stop'
$repoRoot=Split-Path $PSScriptRoot -Parent
$linuxRoot='/mnt/'+$repoRoot.Substring(0,1).ToLower()+($repoRoot.Substring(2) -replace '\\','/')
$player=Join-Path $repoRoot 'artifacts/build-reference-drive/IGVCReferenceDrive.exe'
$editor='C:\Program Files\Unity\Hub\Editor\6000.3.23f1\Editor\Unity.exe'
$run=Join-Path $repoRoot ('artifacts/reference-drive/runs/'+(Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmss')+'-'+([guid]::NewGuid().ToString('N').Substring(0,8)))
New-Item -ItemType Directory -Force -Path $run | Out-Null
$log=Join-Path $run 'launcher.log'
function Log($m){ $line="$(Get-Date -Format o) $m"; Add-Content -Encoding utf8 $log $line; Write-Output $line }
function Wsl-Checked([string[]]$CommandArgs){ & wsl -d Ubuntu-24.04 -- @CommandArgs; if($LASTEXITCODE -ne 0){throw "WSL command failed ($LASTEXITCODE): $($CommandArgs -join ' ')"} }
$locks=@(); $ownedProcess=$null; $rosStarted=$false
try {
    foreach($name in 'live.lock','live-instance-1.lock','live-instance-2.lock'){
        $path=Join-Path $repoRoot "artifacts/iterations/$name"
        try { $locks+=[IO.File]::Open($path,'OpenOrCreate','ReadWrite','None'); Log "acquired $name" }
        catch { throw "Simulator lock busy: $name (another session owns the simulator)" }
    }
    $busy=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'Unity.exe' -or $_.Name -like 'IGVC*.exe' })
    $ports=@(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.LocalPort -in 10000,10001,10002 })
    $wslPorts=@(& wsl -d Ubuntu-24.04 -- ss -H -ltn | Where-Object { $_ -match ':(10000|10001|10002)\s' })
    Log "idle check: unity/igvc=$($busy.Count) windows_ports=$($ports.Count) wsl_ports=$($wslPorts.Count)"
    if($busy.Count -or $ports.Count -or $wslPorts.Count){ throw 'Simulator resources in use; not starting (no foreign process is touched)' }

    if($Action -eq 'build'){
        $buildLog=Join-Path $run 'unity-build.log'
        $p=Start-Process -FilePath $editor -ArgumentList "-batchmode -quit -buildTarget Win64 -projectPath `"$repoRoot/unity/IGVCSim`" -executeMethod ReferenceDriveBuild.Build -logFile `"$buildLog`"" -WindowStyle Hidden -PassThru
        $ownedProcess=$p; $p.WaitForExit(); Log "unity build exit=$($p.ExitCode)"; $ownedProcess=$null
        if($p.ExitCode -ne 0){ throw "Reference drive build failed; see $buildLog" }
        return
    }

    if(!(Test-Path -LiteralPath $player)){ throw "Player missing: run '-Action build' first ($player)" }
    # Same ROS environment as the original single simulator (sandbox.ps1): domain 42, overlay in the WSL home.
    $wslUserHome=(& wsl -d Ubuntu-24.04 -- bash -lc 'printf %s "$HOME"')
    $env:IGVC_ROS_WORKSPACE="$wslUserHome/igvc_ws"; $env:IGVC_ROS_DOMAIN_ID='42'
    $env:WSLENV=(@($env:WSLENV -split ':' | Where-Object {$_ -and $_ -notmatch '^IGVC_(ROS_WORKSPACE|ROS_DOMAIN_ID|INSTANCE)(/.*)?$'})+@('IGVC_ROS_WORKSPACE','IGVC_ROS_DOMAIN_ID')) -join ':'
    $linuxRun='/mnt/'+$run.Substring(0,1).ToLower()+($run.Substring(2) -replace '\\','/')
    Wsl-Checked @('bash',"$linuxRoot/tools/run_ros.sh",'python3',"$linuxRoot/tools/reference_map_mission.py",'--out',"$linuxRun/autonomy.json",'--max-speed',$MaxSpeed.ToString([Globalization.CultureInfo]::InvariantCulture))
    # Same overlay verification as sandbox.ps1: the installed ROS overlay must match this checkout's sources.
    Wsl-Checked @('bash',"$linuxRoot/tools/run_ros.sh",'python3',"$linuxRoot/tools/agents/verify_iteration_overlay.py",$linuxRoot,$env:IGVC_ROS_WORKSPACE)
    Wsl-Checked @('python3',"$linuxRoot/tools/ros_session.py",'start','r3a'); $rosStarted=$true; Log 'managed ROS r3a session started'
    $style=if($Hidden){'Hidden'}else{'Normal'}
    $playerArgs="-screen-fullscreen 0 -screen-width 1600 -screen-height 1000 --line-guard scoring --reference-conditions $Conditions --reference-run-dir `"$run`" -logFile `"$(Join-Path $run 'unity.log')`""
    $ownedProcess=Start-Process -FilePath $player -ArgumentList $playerArgs -WindowStyle $style -PassThru
    Log "player pid=$($ownedProcess.Id) conditions=$Conditions"
    if($Action -eq 'smoke'){
        if(-not $ownedProcess.WaitForExit($Seconds*1000)){ Log "smoke window ($Seconds s) elapsed; stopping our player" }
        else { Log "player exited early with code $($ownedProcess.ExitCode)" }
    } else { $ownedProcess.WaitForExit(); Log "player exited code=$($ownedProcess.ExitCode)" }
}
catch { Log "STOPPED: $($_.Exception.Message)"; throw }
finally {
    if($ownedProcess -and -not $ownedProcess.HasExited){ Stop-Process -Id $ownedProcess.Id -Force; Log "stopped owned process $($ownedProcess.Id)" }
    if($rosStarted){ try { Wsl-Checked @('python3',"$linuxRoot/tools/ros_session.py",'stop','r3a'); Log 'managed ROS r3a session stopped' } catch { Log "ROS stop failed: $($_.Exception.Message)" } }
    foreach($h in $locks){ $h.Dispose() }
    Log "released $($locks.Count) locks; run directory kept: $run"
}
