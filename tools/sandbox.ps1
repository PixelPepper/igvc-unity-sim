param(
    [ValidateSet('start','build','shortcut')][string]$Action='start',
    [switch]$SmokeTest,
    [switch]$Hidden,
    # Unattended sequential trials: path to a batch plan JSON (see docs/LEARNING_PLAN.md).
    [string]$Batch,
    # Parallel simulations: isolated instance n (1..8) with its own session folder, lease, TCP port 10000+n,
    # ROS domain 60+n and no RViz. Omit for the original single simulator.
    [ValidateRange(0,8)][int]$Instance=0,
    [int]$Width=1600,
    [int]$Height=1000
)
$ErrorActionPreference='Stop'
$repoRoot=Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $repoRoot
$player=Join-Path $repoRoot 'artifacts/build-sandbox/IGVCSandbox.exe'
if($Action -eq 'shortcut') {
    $link=(New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'IGVC Sandbox + RViz.lnk'))
    $link.TargetPath="$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
    $link.Arguments='-NoProfile -ExecutionPolicy Bypass -File "'+$PSCommandPath+'"'
    $link.WorkingDirectory=$repoRoot;$link.IconLocation=$player+',0';$link.WindowStyle=1
    $link.Description='Edit the IGVC course and tune navigation from a large Unity control panel.'
    $link.Save();Write-Output 'Created desktop shortcut: IGVC Sandbox + RViz';exit 0
}
$lease=$null;$ownsRuntime=$false;$unityPlayer=$null;$supervisor=$null
$launchFailure=$null
$sessionDirectory=Join-Path $repoRoot $(if($Instance){"artifacts/sandbox-instance-$Instance"}else{'artifacts/sandbox'})
$rosPort=10000+$Instance
function Wsl-Checked([string[]]$CommandArgs) {
    & wsl -d Ubuntu-24.04 -- @CommandArgs
    if($LASTEXITCODE -ne 0){throw "WSL command failed ($LASTEXITCODE)"}
}
try {
    New-Item -ItemType Directory -Force -Path (Join-Path $repoRoot 'artifacts/iterations'),$sessionDirectory,(Join-Path $repoRoot 'artifacts/logs') | Out-Null
    $lease=[IO.File]::Open((Join-Path $repoRoot $(if($Instance){"artifacts/iterations/live-instance-$Instance.lock"}else{'artifacts/iterations/live.lock'})),'OpenOrCreate','ReadWrite','None')
    # Instances are isolated by port/domain/folder; the original mode still refuses to share the machine with any player.
    if(!$Instance -and @(Get-Process IGVCProbe,R3aDrive,IGVCCourse,IGVCTerrain,IGVCSandbox -ErrorAction SilentlyContinue).Count){throw 'Stop the existing simulator first.'}
    if($Action -eq 'build') {
        $project=Join-Path $repoRoot 'unity/IGVCSim'
        $editor='C:\Program Files\Unity\Hub\Editor\6000.3.23f1\Editor\Unity.exe'
        $log=Join-Path $repoRoot 'artifacts/logs/sandbox-build.log'
        $build=Start-Process -FilePath $editor -ArgumentList "-batchmode -quit -buildTarget Win64 -projectPath `"$project`" -executeMethod SandboxBuild.Build -logFile `"$log`"" -WindowStyle Hidden -PassThru
        $build.WaitForExit();if($build.ExitCode -ne 0){throw "Sandbox build failed; inspect $log"}
        Write-Output 'Sandbox player built. The existing course player was not replaced.'
    } else {
        if(!(Test-Path -LiteralPath $player)){throw 'Build first: powershell -ExecutionPolicy Bypass -File tools/sandbox.ps1 build'}
        $linuxRoot=(& wsl -d Ubuntu-24.04 -- wslpath -a $repoRoot).Trim()
        if($LASTEXITCODE -ne 0){throw 'Ubuntu-24.04 unavailable'}
        $wslUserHome=(& wsl -d Ubuntu-24.04 -- printenv HOME).Trim()
        $env:IGVC_ROS_WORKSPACE="$wslUserHome/igvc_ws";$env:IGVC_ROS_DOMAIN_ID=if($Instance){"$(60+$Instance)"}else{'42'}
        if($Instance){$env:IGVC_INSTANCE="$Instance"}else{Remove-Item Env:IGVC_INSTANCE -ErrorAction SilentlyContinue}
        $env:WSLENV=(@($env:WSLENV -split ':' | Where-Object {$_ -and $_ -notmatch '^IGVC_(ROS_WORKSPACE|ROS_DOMAIN_ID|INSTANCE)(/.*)?$'})+@('IGVC_ROS_WORKSPACE','IGVC_ROS_DOMAIN_ID')+@(if($Instance){'IGVC_INSTANCE'})) -join ':'
        $port=& wsl -d Ubuntu-24.04 -- bash -c "ss -H -ltn sport = :$rosPort"
        if($LASTEXITCODE -ne 0 -or $port){throw "An existing simulation owns TCP $rosPort; stop it first."}
        & wsl -d Ubuntu-24.04 -- bash "$linuxRoot/tools/run_ros.sh" python3 "$linuxRoot/tools/agents/verify_iteration_overlay.py" $linuxRoot $env:IGVC_ROS_WORKSPACE
        if($LASTEXITCODE -ne 0){
            # Parallel instances must not rebuild the shared overlay concurrently.
            if($Instance){throw 'ROS overlay is not verified; build it once before starting instances.'}
            Wsl-Checked @('bash',"$linuxRoot/tools/build_ros.sh")
        }
        if($Batch) {
            # Multi-seed batches: generate each requested layout and keep its world/autonomy pair beside the plan.
            # The default seed-2027 normal layout is regenerated afterwards, as for every session.
            $planPath=(Resolve-Path -LiteralPath $Batch).Path;$plan=Get-Content -Raw -LiteralPath $planPath | ConvertFrom-Json
            foreach($pair in @($plan.trials | Where-Object {$_.seed} | ForEach-Object {"$($_.seed)|$(if($_.difficulty){$_.difficulty}else{'normal'})"} | Sort-Object -Unique)) {
                $seed,$difficulty=$pair -split '\|'
                $target=Join-Path (Split-Path $planPath -Parent) "courses/$seed-$difficulty"
                # A parallel driver prepares layouts once; instances never run the shared generator together.
                if($Instance){if(!(Test-Path -LiteralPath (Join-Path $target 'autonomy.json'))){throw "Layout $pair was not prepared for instance $Instance"};continue}
                Wsl-Checked @('bash',"$linuxRoot/tools/run_ros.sh",'python3',"$linuxRoot/tools/generate_course_variant.py",'--seed',$seed,'--difficulty',$difficulty)
                New-Item -ItemType Directory -Force -Path $target | Out-Null
                foreach($name in 'course.json','autonomy.json'){Copy-Item -LiteralPath (Join-Path $repoRoot "artifacts/courses/seed-$seed/$name") -Destination (Join-Path $target $name)}
            }
        }
        $generated=Join-Path $repoRoot 'artifacts/courses/seed-2027'
        if(!$Instance -or !(Test-Path -LiteralPath (Join-Path $generated 'autonomy.json'))){
            if($Instance){throw 'Generate the default seed-2027 layout once before starting instances.'}
            Wsl-Checked @('bash',"$linuxRoot/tools/run_ros.sh",'python3',"$linuxRoot/tools/generate_course_variant.py",'--seed','2027','--difficulty','normal')
        }
        $generated=Join-Path $repoRoot 'artifacts/courses/seed-2027'
        Copy-Item -LiteralPath (Join-Path $generated 'course.json') -Destination (Join-Path $sessionDirectory 'baseline-course.json')
        Copy-Item -LiteralPath (Join-Path $generated 'course.json') -Destination (Join-Path $sessionDirectory 'course.json')
        Copy-Item -LiteralPath (Join-Path $generated 'autonomy.json') -Destination (Join-Path $sessionDirectory 'autonomy.json')
        foreach($stale in @('status.json','command.json','shutdown.request','ui-smoke.json','sandbox-editor.png','sandbox-navigation.png')) {
            $stalePath=Join-Path $sessionDirectory $stale
            if(Test-Path -LiteralPath $stalePath){Remove-Item -LiteralPath $stalePath}
        }
        $ownsRuntime=$true
        Wsl-Checked @('python3',"$linuxRoot/tools/ros_session.py",'stop','nav')
        Wsl-Checked @('python3',"$linuxRoot/tools/ros_session.py",'start','r3a')
        $course=Join-Path $sessionDirectory 'course.json';$unityLog=Join-Path $sessionDirectory 'unity.log'
        $extra=if($SmokeTest){' --sandbox-smoke'}else{''}
        if($Batch){$extra+=' --sandbox-batch "'+(Resolve-Path -LiteralPath $Batch).Path+'"'}
        $style=if($Hidden){'Hidden'}else{'Normal'}
        $unityPlayer=Start-Process -FilePath $player -ArgumentList "-screen-fullscreen 0 -screen-width $Width -screen-height $Height --line-guard scoring --course-manifest `"$course`" --sandbox-dir `"$sessionDirectory`" -logFile `"$unityLog`"$extra$(if($Instance){" --ros-port $rosPort"})" -WindowStyle $style -PassThru
        $linuxDirectory=(& wsl -d Ubuntu-24.04 -- wslpath -a $sessionDirectory).Trim()
        $supervisorArgs=@('-d','Ubuntu-24.04','--','bash',"$linuxRoot/tools/run_ros.sh",'python3',"$linuxRoot/tools/sandbox_session.py",'--directory',$linuxDirectory,'--mission',"$linuxDirectory/autonomy.json")+@(if(!$Instance){'--rviz'})
        # WSL's option parser treats a quoted "-d" as a Linux command, not a flag.
        $quoted=($supervisorArgs | ForEach-Object {if($_ -match '\s'){'"'+$_+'"'}else{$_}}) -join ' '
        $supervisor=Start-Process -FilePath 'wsl.exe' -ArgumentList $quoted -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $sessionDirectory 'supervisor.log') -RedirectStandardError (Join-Path $sessionDirectory 'supervisor-error.log')
        Write-Output 'Sandbox open. Edit and run from the Unity panel; close Unity to end the session.'
        $deadline=[DateTime]::UtcNow.AddSeconds(80)
        while(!$unityPlayer.HasExited) {
            if($supervisor.HasExited){throw "Sandbox supervisor exited. Inspect $sessionDirectory/supervisor-error.log."}
            if($SmokeTest -and (Test-Path -LiteralPath (Join-Path $sessionDirectory 'ui-smoke.json'))) {
                if(Test-Path -LiteralPath (Join-Path $sessionDirectory 'sandbox-navigation.png')){Write-Output 'Sandbox UI smoke and screenshots complete.';break}
            }
            if($SmokeTest -and [DateTime]::UtcNow -gt $deadline){throw 'Sandbox smoke test timed out.'}
            Start-Sleep -Milliseconds 500
        }
    }
} catch {
    $launchFailure=$_
    Write-Host $_ -ForegroundColor Red
} finally {
    if($supervisor -and !$supervisor.HasExited) {
        Set-Content -LiteralPath (Join-Path $sessionDirectory 'shutdown.request') -Value 'stop'
        if(!$supervisor.WaitForExit(45000)){Write-Warning 'Supervisor cleanup is still pending. Inspect session logs.'}
    }
    if($unityPlayer -and !$unityPlayer.HasExited){Stop-Process -Id $unityPlayer.Id}
    if($ownsRuntime){& powershell -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot/igvc.ps1" stop}
    if($lease){$lease.Dispose()}
}
if($launchFailure) {
    if(!$SmokeTest -and !$Batch){Read-Host 'Press Enter to close' | Out-Null}
    exit 1
}
