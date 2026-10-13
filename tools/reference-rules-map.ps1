# Managed launcher for the PROPOSED rule-dimensioned reference-course drive player (T-0091), derived from
# tools/reference-map.ps1 (T-0090) with ONLY these changes: build method/output, player path/name, run folder, and the
# mission export from root-pinned spawn/goal metadata (tools/reference_rules_mission.py). Locks, preflight, cleanup,
# ownership latches, WSL stderr handling and the trial driver/policy are unchanged. Separate from tools/sandbox.ps1.
# The 180 s diagnostic trial is NOT six-minute rule enforcement.
#   build : Unity batch ReferenceRulesDriveBuild.Build, bounded (45 min) -> artifacts/build-reference-rules/IGVCReferenceRules.exe
#   start : mission export, overlay check, OWN managed r3a session, visible player; runs until the player is closed
#   smoke : as start for -Seconds (<= 180); the player exiting early is a FAILURE. Process survival is not a sensor check.
#   trial : as start, then tools/reference_map_trial.py: sensor smoke, clock admission, one bounded sensor-led mission
#           (speed <= 0.6 m/s, timeout <= 180 s), no retry. Diagnostic only (no full-lap audit for this map).
# Ownership: holds all three exclusive simulator locks for the whole invocation; refuses if any Unity editor/player,
# IGVC/R3a player, port 10000-10002 (Windows or WSL) or ANY managed ROS group (r3a/probe, nav, perception) is active.
# Cleanup touches only what this invocation started and confirmed as newly owned. If cleanup cannot be confirmed the
# launcher does NOT release its locks: it stays alive holding the real lock handles, re-checks only its owned PIDs/ROS
# group every 30 s (read-only), keeps <run>/ownership-retained.json current with recovery instructions, and releases
# only when everything owned is verifiably gone or root creates <run>/root-recovery-release.
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
$player=Join-Path $repoRoot 'artifacts/build-reference-rules/IGVCReferenceRules.exe'
$editor='C:\Program Files\Unity\Hub\Editor\6000.3.23f1\Editor\Unity.exe'
$run=Join-Path $repoRoot ('artifacts/reference-rules/runs/'+(Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmss')+'-'+([guid]::NewGuid().ToString('N').Substring(0,8)))
New-Item -ItemType Directory -Force -Path $run | Out-Null
$log=Join-Path $run 'launcher.log'
$invariant=[Globalization.CultureInfo]::InvariantCulture
function Log($m){ $line="$(Get-Date -Format o) $m"; Add-Content -Encoding utf8 $log $line; Write-Output $line }
# Native WSL call with deterministic capture: stderr goes to a temp file (never 2>&1 under Stop, which throws
# NativeCommandError in Windows PowerShell 5.1); returns code/out/err. Any capture exception yields code -1.
function Wsl([string[]]$CommandArgs){
    $previous=$ErrorActionPreference; $ErrorActionPreference='Continue'; $errFile=$null
    try {
        $errFile=[IO.Path]::GetTempFileName()
        # wsl.exe explicitly: a bare `wsl` would resolve to this Wsl function (case-insensitive, functions first).
        $out=& wsl.exe -d Ubuntu-24.04 -- @CommandArgs 2> $errFile; $code=$LASTEXITCODE
        $err=Get-Content -Raw -LiteralPath $errFile -ErrorAction SilentlyContinue
    } catch { $out=@(); $code=-1; $err="capture failed: $($_.Exception.Message)" }
    finally { $ErrorActionPreference=$previous; if($errFile){ Remove-Item -LiteralPath $errFile -ErrorAction SilentlyContinue } }
    return @{code=$code; out=((@($out)|ForEach-Object{"$_"}) -join "`n"); err="$err".Trim()}
}
function Wsl-Checked([string[]]$CommandArgs){ $r=Wsl $CommandArgs; if($r.code -ne 0){throw "WSL command failed ($($r.code)): $($CommandArgs -join ' '): $($r.out) $($r.err)"}; return $r.out }

$locks=@(); $ownedPlayer=$null; $ownedBuild=$null; $ownsRos=$false; $failure=$null; $cleanupFailed=@(); $linuxRoot=$null
# Set when ownership cannot be verified from here (trial cleanup unknown, unreceipted ROS group, cleanup exception):
# the locks are then released ONLY by root's <run>/root-recovery-release, never by automatic checks.
$rootReleaseRequired=$false
# True from just before the trial driver call until its exit code (0, 1 or 2) is evaluated; still true in finally means
# the call was interrupted or threw, so navigation and the mission may be alive: root release is required.
$trialInFlight=$false
try {
    foreach($name in 'live.lock','live-instance-1.lock','live-instance-2.lock'){
        try { $locks+=[IO.File]::Open((Join-Path $repoRoot "artifacts/iterations/$name"),'OpenOrCreate','ReadWrite','None'); Log "acquired $name" }
        catch { throw "Simulator lock busy: $name (another session owns the simulator)" }
    }
    # Idle preflight (fail closed on any query error).
    $busy=@(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object { $_.Name -match '^(Unity|IGVC.*|IGVCReferenceRules|R3a.*|.*Terrain.*|.*Inspection.*)\.exe$' })
    $ports=@(Get-NetTCPConnection -State Listen -ErrorAction Stop | Where-Object { $_.LocalPort -in 10000,10001,10002 })
    $ss=Wsl @('ss','-H','-ltn'); if($ss.code -ne 0){ throw "WSL port query failed ($($ss.code))" }
    $wslPorts=@($ss.out -split "`n" | Where-Object { $_ -match ':(10000|10001|10002)\s' })
    Log "idle check: unity/players=$($busy.Count) [$(($busy|ForEach-Object{$_.Name}) -join ',')] windows_ports=$($ports.Count) wsl_ports=$($wslPorts.Count)"
    if($busy.Count -or $ports.Count -or $wslPorts.Count){ throw 'Simulator resources in use; not starting (no foreign process is touched)' }
    # ROS environment of the original single simulator (domain 42, no instance); managed ROS idle check for EVERY action.
    $linuxRoot=(Wsl-Checked @('wslpath','-a',$repoRoot)).Trim()
    $linuxRun=(Wsl-Checked @('wslpath','-a',$run)).Trim()
    $wslHome=(Wsl-Checked @('printenv','HOME')).Trim()
    $env:IGVC_ROS_WORKSPACE="$wslHome/igvc_ws"; $env:IGVC_ROS_DOMAIN_ID='42'; Remove-Item Env:IGVC_INSTANCE -ErrorAction SilentlyContinue
    $env:WSLENV=(@($env:WSLENV -split ':' | Where-Object {$_ -and $_ -notmatch '^IGVC_(ROS_WORKSPACE|ROS_DOMAIN_ID|INSTANCE)(/.*)?$'})+@('IGVC_ROS_WORKSPACE','IGVC_ROS_DOMAIN_ID')) -join ':'
    foreach($mode in 'r3a','nav','perception'){
        $status=Wsl-Checked @('python3',"$linuxRoot/tools/ros_session.py",'status',$mode)
        Log "ros_session status $mode : $status"
        if($status -notmatch 'stopped'){ throw "Managed ROS $mode group is active; not starting (it is not ours)" }
    }

    if($Action -eq 'build'){
        $buildLog=Join-Path $run 'unity-build.log'
        $ownedBuild=Start-Process -FilePath $editor -ArgumentList "-batchmode -quit -buildTarget Win64 -projectPath `"$repoRoot/unity/IGVCSim`" -executeMethod ReferenceRulesDriveBuild.Build -logFile `"$buildLog`"" -WindowStyle Hidden -PassThru
        Log "unity build pid=$($ownedBuild.Id)"
        if(-not $ownedBuild.WaitForExit(45*60*1000)){ throw 'Unity build exceeded 45 minutes' }
        $ownedBuild.WaitForExit(); Log "unity build exit=$($ownedBuild.ExitCode)"
        if($ownedBuild.ExitCode -ne 0){ throw "Reference rules build failed; see $buildLog" }
        $ownedBuild=$null
    }
    else {
        if(!(Test-Path -LiteralPath $player)){ throw "Player missing: run '-Action build' first ($player)" }
        Wsl-Checked @('bash',"$linuxRoot/tools/run_ros.sh",'python3',"$linuxRoot/tools/reference_rules_mission.py",'--metadata',"$linuxRoot/artifacts/agents/T-0091/mission-metadata.json",'--out',"$linuxRun/autonomy.json",'--max-speed',$MaxSpeed.ToString($invariant)) | Out-Null
        Wsl-Checked @('bash',"$linuxRoot/tools/run_ros.sh",'python3',"$linuxRoot/tools/agents/verify_iteration_overlay.py",$linuxRoot,$env:IGVC_ROS_WORKSPACE) | Out-Null
        $start=Wsl @('python3',"$linuxRoot/tools/ros_session.py",'start','r3a')
        if($start.code -eq 0 -and $start.out -match 'ROS started: PID (\d+)'){ $ownsRos=$true; Log "owned managed r3a session pid=$($Matches[1]) (fresh-start receipt)" }
        else {
            # No fresh-start receipt (including 'already running'): never claim or stop it. If a group is running now,
            # its owner is uncertain, so the locks stay held for root.
            $after=Wsl @('python3',"$linuxRoot/tools/ros_session.py",'status','r3a')
            if($after.code -ne 0 -or $after.out -notmatch 'stopped'){
                $rootReleaseRequired=$true; $cleanupFailed+="unreceipted r3a group present after failed start ($($start.out) $($start.err)); not stopped"
            }
            throw "r3a session start gave no fresh-start receipt ($($start.code)): $($start.out) $($start.err)"
        }
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
                $trialInFlight=$true
                $trial=Wsl @('bash',"$linuxRoot/tools/run_ros.sh",'python3',"$linuxRoot/tools/reference_map_trial.py",'--run-dir',$linuxRun,'--mission',"$linuxRun/autonomy.json",'--speed',$MaxSpeed.ToString($invariant),'--timeout',"$TrialTimeout")
                if($trial.code -in 0,1,2){ $trialInFlight=$false }   # evaluated before any logging/file write
                Set-Content -Encoding utf8 (Join-Path $run 'trial-driver.log') ($trial.out+"`n"+$trial.err)
                Log "trial driver exit=$($trial.code)"
                if($trial.code -eq 3){ $rootReleaseRequired=$true; $cleanupFailed+='trial driver could not confirm mission/navigation cleanup (see trial-report.json)' }
                elseif($trial.code -lt 0){ $rootReleaseRequired=$true; $cleanupFailed+="trial driver call failed to capture ($($trial.err)); its children may be alive" }
                if($ownedPlayer.HasExited){ throw "Player exited during the trial (code $($ownedPlayer.ExitCode))" }
                if($trial.code -ne 0){ throw "Trial did not complete (driver exit $($trial.code)); see trial-report.json" }
            }
            default { $ownedPlayer.WaitForExit(); Log "player exited code=$($ownedPlayer.ExitCode)" }
        }
    }
}
catch { $failure=$_.Exception.Message; Log "STOPPED: $failure" }
finally {
    if($trialInFlight){ $rootReleaseRequired=$true; $cleanupFailed+='trial driver call interrupted or ended without a 0/1/2 exit; navigation and mission may be alive' }
    foreach($p in @($ownedPlayer,$ownedBuild)){
        try {
            if($p -and -not $p.HasExited){
                Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
                if($p.WaitForExit(15000)){ Log "stopped owned process $($p.Id)" } else { $cleanupFailed+="owned process $($p.Id) did not exit" }
            }
        } catch { $rootReleaseRequired=$true; $cleanupFailed+="cleanup of owned process raised: $($_.Exception.Message)" }
    }
    if($ownsRos){
        try {
            $stop=Wsl @('python3',"$linuxRoot/tools/ros_session.py",'stop','r3a')
            Log "ros_session stop r3a exit=$($stop.code): $($stop.out) $($stop.err)"
            if($stop.code -ne 0){ $cleanupFailed+='owned r3a ROS group did not stop' }
        } catch { $rootReleaseRequired=$true; $cleanupFailed+="r3a stop raised: $($_.Exception.Message)" }
    }
    if($cleanupFailed.Count){
        # A file is not a lease: keep holding the real lock handles until everything owned is verifiably gone.
        $statusFile=Join-Path $run 'ownership-retained.json'; $release=Join-Path $run 'root-recovery-release'
        Log "CLEANUP NOT CONFIRMED: $($cleanupFailed -join '; '). Holding all locks (launcher pid $PID); see $statusFile"
        while($true){
            $alive=@(); $groups=@{}; $verified=$false
            try {
                $alive=@(@($ownedPlayer,$ownedBuild) | Where-Object { $_ -and -not $_.HasExited } | ForEach-Object { $_.Id })
                # Read-only supporting evidence for EVERY managed group; nothing is stopped here.
                foreach($mode in 'r3a','nav','perception'){ $s=Wsl @('python3',"$linuxRoot/tools/ros_session.py",'status',$mode); $groups[$mode]=($s.code -ne 0 -or $s.out -notmatch 'stopped') }
                $verified=$true
            } catch { $rootReleaseRequired=$true }
            $rosAlive=($groups.Values -contains $true)
            $problems=(($cleanupFailed|ForEach-Object{"`"$_`""}) -join ', ')
            $recovery="Root: stop the listed owned processes and/or the r3a group (python3 tools/ros_session.py stop r3a), or after manual verification create $($release -replace '\\','/') so this launcher releases its locks."
            Set-Content -Encoding utf8 $statusFile ("{`"launcher_pid`": $PID, `"locks_held`": true, `"run`": `"$($run -replace '\\','/')`", `"owned_pids_alive`": [$($alive -join ', ')], `"managed_groups_alive`": `"$(($groups.GetEnumerator()|ForEach-Object{"$($_.Key)=$($_.Value)"}) -join ' ')`", `"root_release_required`": $($rootReleaseRequired.ToString().ToLower()), `"checked`": `"$(Get-Date -Format o)`", `"problems`": [$problems], `"recovery`": `"$recovery`"}")
            if(-not $rootReleaseRequired -and $verified -and -not $alive.Count -and -not $rosAlive){ Log 'owned processes gone and r3a/nav/perception all stopped; releasing locks'; $cleanupFailed=@(); break }
            if(Test-Path -LiteralPath $release){ Log 'root recovery release file present; releasing locks on root instruction'; break }
            Start-Sleep -Seconds 30
        }
    }
    foreach($h in $locks){ $h.Dispose() }
    Log "released $($locks.Count) locks; run directory kept: $run"
}
if($cleanupFailed.Count){ throw "Cleanup not confirmed: $($cleanupFailed -join '; ')" }
if($failure){ throw $failure }
