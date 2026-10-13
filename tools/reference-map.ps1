# Managed launcher for the image-traced reference-map drive player (T-0090). Separate from tools/sandbox.ps1.
#   build : Unity batch ReferenceDriveBuild.Build, bounded (45 min) -> artifacts/build-reference-drive/IGVCReferenceDrive.exe
#   start : mission export, overlay check, OWN managed r3a session, visible player; runs until the player is closed
#   smoke : as start for -Seconds (<= 180); the player exiting early is a FAILURE. Process survival is not a sensor check.
#   trial : as start, then tools/reference_map_trial.py: sensor smoke, clock admission, one bounded sensor-led mission
#           (speed <= 0.6 m/s, timeout <= 180 s), no retry. Diagnostic only (no full-lap audit for this map).
# Ownership: holds all three exclusive simulator locks for the whole invocation; refuses if any Unity editor/player,
# IGVC/R3a player, port 10000-10002 (Windows or WSL) or ANY managed ROS group (r3a/probe, nav, perception) is active.
# Cleanup touches only what this invocation started and confirmed as newly owned. If cleanup cannot be confirmed it
# writes artifacts/iterations/reference-drive-ownership-retained.json and exits non-zero (the run directory is kept).
param(
    [ValidateSet('build','start','smoke','trial')][string]$Action='start',
    [ValidateSet('clear-noon','overcast','low-sun')][string]$Conditions='clear-noon',
    [ValidateRange(10,180)][int]$Seconds=60,
    [ValidateRange(0.1,0.6)][double]$MaxSpeed=0.6,
    [ValidateRange(10,180)][int]$TrialTimeout=180,
    [switch]$Hidden
)
$ErrorActionPreference='Stop'
$repoRoot=Split-Path $PSScriptRoot -Parent
$player=Join-Path $repoRoot 'artifacts/build-reference-drive/IGVCReferenceDrive.exe'
$editor='C:\Program Files\Unity\Hub\Editor\6000.3.23f1\Editor\Unity.exe'
$run=Join-Path $repoRoot ('artifacts/reference-drive/runs/'+(Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmss')+'-'+([guid]::NewGuid().ToString('N').Substring(0,8)))
New-Item -ItemType Directory -Force -Path $run | Out-Null
$log=Join-Path $run 'launcher.log'
$invariant=[Globalization.CultureInfo]::InvariantCulture
function Log($m){ $line="$(Get-Date -Format o) $m"; Add-Content -Encoding utf8 $log $line; Write-Output $line }
function Wsl([string[]]$CommandArgs){ $out=& wsl -d Ubuntu-24.04 -- @CommandArgs 2>&1; $code=$LASTEXITCODE; return @{code=$code; out=(($out|ForEach-Object{"$_"}) -join "`n")} }
function Wsl-Checked([string[]]$CommandArgs){ $r=Wsl $CommandArgs; if($r.code -ne 0){throw "WSL command failed ($($r.code)): $($CommandArgs -join ' '): $($r.out)"}; return $r.out }

$locks=@(); $ownedPlayer=$null; $ownedBuild=$null; $ownsRos=$false; $failure=$null; $cleanupFailed=@(); $linuxRoot=$null
try {
    foreach($name in 'live.lock','live-instance-1.lock','live-instance-2.lock'){
        try { $locks+=[IO.File]::Open((Join-Path $repoRoot "artifacts/iterations/$name"),'OpenOrCreate','ReadWrite','None'); Log "acquired $name" }
        catch { throw "Simulator lock busy: $name (another session owns the simulator)" }
    }
    # Idle preflight (fail closed on any query error).
    $busy=@(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object { $_.Name -match '^(Unity|IGVC.*|R3a.*|.*Terrain.*|.*Inspection.*)\.exe$' })
    $ports=@(Get-NetTCPConnection -State Listen -ErrorAction Stop | Where-Object { $_.LocalPort -in 10000,10001,10002 })
    $ss=Wsl @('ss','-H','-ltn'); if($ss.code -ne 0){ throw "WSL port query failed ($($ss.code))" }
    $wslPorts=@($ss.out -split "`n" | Where-Object { $_ -match ':(10000|10001|10002)\s' })
    Log "idle check: unity/players=$($busy.Count) [$(($busy|ForEach-Object{$_.Name}) -join ',')] windows_ports=$($ports.Count) wsl_ports=$($wslPorts.Count)"
    if($busy.Count -or $ports.Count -or $wslPorts.Count){ throw 'Simulator resources in use; not starting (no foreign process is touched)' }

    if($Action -eq 'build'){
        $buildLog=Join-Path $run 'unity-build.log'
        $ownedBuild=Start-Process -FilePath $editor -ArgumentList "-batchmode -quit -buildTarget Win64 -projectPath `"$repoRoot/unity/IGVCSim`" -executeMethod ReferenceDriveBuild.Build -logFile `"$buildLog`"" -WindowStyle Hidden -PassThru
        Log "unity build pid=$($ownedBuild.Id)"
        if(-not $ownedBuild.WaitForExit(45*60*1000)){ throw 'Unity build exceeded 45 minutes' }
        $ownedBuild.WaitForExit(); Log "unity build exit=$($ownedBuild.ExitCode)"
        if($ownedBuild.ExitCode -ne 0){ throw "Reference drive build failed; see $buildLog" }
        $ownedBuild=$null
    }
    else {
        if(!(Test-Path -LiteralPath $player)){ throw "Player missing: run '-Action build' first ($player)" }
        # ROS environment of the original single simulator (domain 42, no instance).
        $linuxRoot=(Wsl-Checked @('wslpath','-a',$repoRoot)).Trim()
        $linuxRun=(Wsl-Checked @('wslpath','-a',$run)).Trim()
        $wslHome=(Wsl-Checked @('printenv','HOME')).Trim()
        $env:IGVC_ROS_WORKSPACE="$wslHome/igvc_ws"; $env:IGVC_ROS_DOMAIN_ID='42'; Remove-Item Env:IGVC_INSTANCE -ErrorAction SilentlyContinue
        $env:WSLENV=(@($env:WSLENV -split ':' | Where-Object {$_ -and $_ -notmatch '^IGVC_(ROS_WORKSPACE|ROS_DOMAIN_ID|INSTANCE)(/.*)?$'})+@('IGVC_ROS_WORKSPACE','IGVC_ROS_DOMAIN_ID')) -join ':'
        # Every managed ROS group must be stopped; nothing existing is ever claimed.
        foreach($mode in 'r3a','nav','perception'){
            $status=Wsl-Checked @('python3',"$linuxRoot/tools/ros_session.py",'status',$mode)
            Log "ros_session status $mode : $status"
            if($status -notmatch 'stopped'){ throw "Managed ROS $mode group is active; not starting (it is not ours)" }
        }
        Wsl-Checked @('bash',"$linuxRoot/tools/run_ros.sh",'python3',"$linuxRoot/tools/reference_map_mission.py",'--out',"$linuxRun/autonomy.json",'--max-speed',$MaxSpeed.ToString($invariant)) | Out-Null
        Wsl-Checked @('bash',"$linuxRoot/tools/run_ros.sh",'python3',"$linuxRoot/tools/agents/verify_iteration_overlay.py",$linuxRoot,$env:IGVC_ROS_WORKSPACE) | Out-Null
        $started=Wsl-Checked @('python3',"$linuxRoot/tools/ros_session.py",'start','r3a')
        if($started -notmatch 'ROS started: PID (\d+)'){ throw "r3a session not newly started by this invocation: $started" }
        $ownsRos=$true; Log "owned managed r3a session pid=$($Matches[1])"
        $style=if($Hidden){'Hidden'}else{'Normal'}
        $playerArgs="-screen-fullscreen 0 -screen-width 1600 -screen-height 1000 --line-guard scoring --reference-conditions $Conditions --reference-run-dir `"$run`" -logFile `"$(Join-Path $run 'unity.log')`""
        $ownedPlayer=Start-Process -FilePath $player -ArgumentList $playerArgs -WindowStyle $style -PassThru
        Log "owned player pid=$($ownedPlayer.Id) conditions=$Conditions"
        switch($Action){
            'smoke' {
                if($ownedPlayer.WaitForExit($Seconds*1000)){ throw "Player exited early (code $($ownedPlayer.ExitCode)) during the smoke window" }
                Log "smoke window ($Seconds s) elapsed with the player running (process survival only; not a sensor check)"
            }
            'trial' {
                Start-Sleep -Seconds 10   # bridge/endpoint startup; the trial itself gates on received streams and clock
                if($ownedPlayer.HasExited){ throw "Player exited before the trial (code $($ownedPlayer.ExitCode))" }
                $trial=Wsl @('bash',"$linuxRoot/tools/run_ros.sh",'python3',"$linuxRoot/tools/reference_map_trial.py",'--run-dir',$linuxRun,'--mission',"$linuxRun/autonomy.json",'--speed',$MaxSpeed.ToString($invariant),'--timeout',"$TrialTimeout")
                Set-Content -Encoding utf8 (Join-Path $run 'trial-driver.log') $trial.out
                Log "trial driver exit=$($trial.code)"
                if($trial.code -eq 3){ $cleanupFailed+='trial driver could not confirm mission/navigation cleanup' }
                if($ownedPlayer.HasExited){ throw "Player exited during the trial (code $($ownedPlayer.ExitCode))" }
                if($trial.code -ne 0){ throw "Trial did not complete (driver exit $($trial.code)); see trial-report.json" }
            }
            default { $ownedPlayer.WaitForExit(); Log "player exited code=$($ownedPlayer.ExitCode)" }
        }
    }
}
catch { $failure=$_.Exception.Message; Log "STOPPED: $failure" }
finally {
    foreach($p in @($ownedPlayer,$ownedBuild)){
        if($p -and -not $p.HasExited){
            Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
            if($p.WaitForExit(15000)){ Log "stopped owned process $($p.Id)" } else { $cleanupFailed+="owned process $($p.Id) did not exit" }
        }
    }
    if($ownsRos){
        $stop=Wsl @('python3',"$linuxRoot/tools/ros_session.py",'stop','r3a')
        Log "ros_session stop r3a exit=$($stop.code): $($stop.out)"
        if($stop.code -ne 0){ $cleanupFailed+='owned r3a ROS group did not stop' }
    }
    if($cleanupFailed.Count){
        $marker=Join-Path $repoRoot 'artifacts/iterations/reference-drive-ownership-retained.json'
        Set-Content -Encoding utf8 $marker ("{`"run`": `"$($run -replace '\\','/')`", `"problems`": [" + (($cleanupFailed|ForEach-Object{"`"$_`""}) -join ', ') + "]}")
        Log "CLEANUP NOT CONFIRMED: $($cleanupFailed -join '; '); marker $marker written"
    }
    foreach($h in $locks){ $h.Dispose() }
    Log "released $($locks.Count) locks; run directory kept: $run"
}
if($cleanupFailed.Count){ throw "Cleanup not confirmed: $($cleanupFailed -join '; ')" }
if($failure){ throw $failure }
