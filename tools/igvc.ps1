param(
    [Parameter(Position=0)]
    [ValidateSet('doctor','build','start','stop','status','test','rviz','robot-build','robot-view','robot-stop','robot-rviz','drive-build','drive-start','terrain-build','terrain-start','terrain-turn-test','course-ramp-test','course-build','course-start','variant-generate','variant-start','variant-audit','nav-start','nav-stop','perception-start','perception-stop','nav-goal','nav-cancel','gps-list','gps-run','loop-run','loop-status','loop-resume','loop-cancel')]
    [string]$Action = 'status',
    [int]$Duration = 600,
    [switch]$Visible,
    [switch]$Resume,
    [switch]$RigidTerrain,
    [int]$Seed = 2027,
    [ValidateSet('easy','normal','hard')][string]$Difficulty = 'normal',
    [double]$X = 2,
    [double]$Y = 0,
    [double]$Yaw = 0,
    [string]$Mission = '',
    [string]$Unity = 'C:\Program Files\Unity\Hub\Editor\6000.3.23f1\Editor\Unity.exe'
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent
$project = Join-Path $repoRoot 'unity/IGVCSim'
$player = Join-Path $repoRoot 'artifacts/build/IGVCProbe.exe'
$logs = Join-Path $repoRoot 'artifacts/logs'
New-Item -ItemType Directory -Force $logs | Out-Null
$linuxRoot = (& wsl -d Ubuntu-24.04 -- wslpath -a $repoRoot).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Ubuntu-24.04 is unavailable' }
function Run-Ros([string[]]$RosArgs) {
    & wsl -d Ubuntu-24.04 -- bash "$linuxRoot/tools/run_ros.sh" @RosArgs
    if ($LASTEXITCODE -ne 0) { throw "ROS command failed ($LASTEXITCODE)" }
}
function Session([string]$Operation, [string]$Mode = 'probe') {
    & wsl -d Ubuntu-24.04 -- python3 "$linuxRoot/tools/ros_session.py" $Operation $Mode
    if ($LASTEXITCODE -ne 0) { throw "ROS session $Operation failed" }
}
function Players {
    $drivePath = (Join-Path $repoRoot 'artifacts/build-drive/R3aDrive.exe').Replace('\','/')
    $coursePath = (Join-Path $repoRoot 'artifacts/build-course/IGVCCourse.exe').Replace('\','/')
    $terrainPath = (Join-Path $repoRoot 'artifacts/build-terrain/IGVCTerrain.exe').Replace('\','/')
    Get-Process IGVCProbe,R3aDrive,IGVCCourse,IGVCTerrain -ErrorAction SilentlyContinue | Where-Object {
        $_.Path -and $_.Path.Replace('\','/') -in @($player.Replace('\','/'), $drivePath, $coursePath, $terrainPath)
    }
}
function RobotPlayers {
    $robotPath = (Join-Path $repoRoot 'artifacts/build-robot/R3aInspection.exe').Replace('\','/')
    Get-Process R3aInspection -ErrorAction SilentlyContinue | Where-Object {
        $_.Path -and $_.Path.Replace('\','/') -eq $robotPath
    }
}
function SessionMode {
    $statePath = Join-Path $repoRoot 'artifacts/session/ros.json'
    if (Test-Path $statePath) {
        $state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
        if ($state.mode -eq 'r3a') { return 'r3a' }
    }
    return 'probe'
}
function GpsMissionPath {
    if ([string]::IsNullOrWhiteSpace($Mission)) {
        return "$linuxRoot/ros2/src/igvc_gps/config/waypoints.json"
    }
    # Absolute POSIX paths already name files in the selected WSL distribution.
    if ($Mission.StartsWith('/')) { return $Mission }
    $windowsMission = (Resolve-Path -LiteralPath $Mission).ProviderPath
    $converted = & wsl -d Ubuntu-24.04 -- wslpath -a -u $windowsMission
    if ($LASTEXITCODE -ne 0) { throw "Cannot convert mission path: $Mission" }
    return $converted.Trim()
}
switch ($Action) {
    'terrain-build' {
        if (@(Players).Count -gt 0) { throw 'Stop the simulator before building' }
        & wsl -d Ubuntu-24.04 -- bash "$linuxRoot/tools/build_ros.sh"
        if ($LASTEXITCODE -ne 0) { throw 'ROS build failed' }
        $terrainLog=Join-Path $logs 'terrain-body-unity-build.log'
        $process=Start-Process -FilePath $Unity -ArgumentList "-batchmode -quit -buildTarget Win64 -projectPath `"$project`" -executeMethod TerrainBenchBuild.Build -logFile `"$terrainLog`"" -WindowStyle Hidden -PassThru
        $process.WaitForExit()
        if ($process.ExitCode -ne 0) { throw 'Terrain bench build failed' }
    }
    'terrain-start' {
        if (@(Players).Count -gt 0) { throw 'Stop the current simulator first' }
        $terrainPlayer=Join-Path $repoRoot 'artifacts/build-terrain/IGVCTerrain.exe'
        if (!(Test-Path -LiteralPath $terrainPlayer)) { throw 'Run terrain-build first' }
        @{profile='terrain-bench';caster_suspension=(!$RigidTerrain)} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $repoRoot 'artifacts/session/course-variant.json')
        Session 'start' 'r3a'
        $terrainLog=Join-Path $logs 'terrain-body-player.log'
        $style=if($Visible){'Normal'}else{'Hidden'}
        $casterMode=if($RigidTerrain){'off'}else{'on'}
        Start-Process -FilePath $terrainPlayer -ArgumentList "-logFile `"$terrainLog`" --caster-suspension $casterMode" -WindowStyle $style | Out-Null
        Write-Output 'Experimental support bench started; manual test only, no full-course mission.'
    }
    'terrain-turn-test' {
        $profilePath=Join-Path $repoRoot 'artifacts/session/course-variant.json'
        if (!(Test-Path -LiteralPath $profilePath) -or @(Players).Count -ne 1) { throw 'Start a fresh suspension terrain bench first' }
        $profile=Get-Content -LiteralPath $profilePath -Raw | ConvertFrom-Json
        if ($profile.profile -ne 'terrain-bench' -or $profile.caster_suspension -ne $true) { throw 'Use terrain-start without -RigidTerrain for the turning test' }
        Run-Ros @('python3',"$linuxRoot/tools/verify_caster_turning.py")
    }
    'variant-generate' {
        if (@(Players).Count -gt 0) { throw 'Stop the current simulation before regenerating course manifests' }
        Run-Ros @('python3',"$linuxRoot/tools/generate_course_variant.py",'--seed',[string]$Seed,'--difficulty',$Difficulty)
    }
    'course-ramp-test' {
        $profilePath=Join-Path $repoRoot 'artifacts/session/course-variant.json'
        if (!(Test-Path -LiteralPath $profilePath) -or @(Players).Count -ne 1) { throw 'Start a fresh ramp variant first' }
        $profile=Get-Content -LiteralPath $profilePath -Raw | ConvertFrom-Json
        if ($null -eq $profile.seed) { throw 'The ramp test requires a seeded course' }
        $reportName='course-ramp-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.json'
        Run-Ros @('python3',"$linuxRoot/tools/verify_course_ramp.py",'--report',"$linuxRoot/artifacts/checks/$reportName")
    }
    'variant-start' {
        if (@(Players).Count -gt 0) { throw 'Stop the current simulation before selecting a variant' }
        $variantPlayer=Join-Path $repoRoot 'artifacts/build-course/IGVCCourse.exe'
        if (!(Test-Path -LiteralPath $variantPlayer)) { throw 'Run course-build first' }
        Run-Ros @('python3',"$linuxRoot/tools/generate_course_variant.py",'--seed',[string]$Seed,'--difficulty',$Difficulty)
        $variantFolder=Join-Path $repoRoot "artifacts/courses/seed-$Seed"
        @{seed=$Seed; difficulty=$Difficulty; folder=$variantFolder} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $repoRoot 'artifacts/session/course-variant.json')
        Session 'start' 'r3a'
        $variantManifest=Join-Path $variantFolder 'course.json'
        $variantLog=Join-Path $variantFolder 'unity.log'
        $windowStyle=if($Visible){'Normal'}else{'Hidden'}
        Start-Process -FilePath $variantPlayer -ArgumentList "--course-manifest `"$variantManifest`" -logFile `"$variantLog`"" -WindowStyle $windowStyle | Out-Null
        Write-Output "Variant $Seed started with ramp and suspension. course-ramp-test runs a bounded manual crossing from this fresh start. Autonomous ramp perception remains experimental."
    }
    'variant-audit' {
        Run-Ros @('python3',"$linuxRoot/tools/audit_course_variant.py",'--course',"$linuxRoot/artifacts/courses/seed-$Seed/course.json",'--run',"$linuxRoot/artifacts/courses/seed-$Seed/run.json")
    }
    'loop-run' {
        $loopArgs = @('python3',"$linuxRoot/tools/full_course.py")
        $activePath=Join-Path $repoRoot 'artifacts/session/course-variant.json'
        if (![string]::IsNullOrWhiteSpace($Mission)) { $loopArgs += @('--mission',(GpsMissionPath)) }
        elseif (Test-Path -LiteralPath $activePath) {
            $activeVariant=Get-Content -LiteralPath $activePath -Raw | ConvertFrom-Json
            if ($activeVariant.profile -eq 'terrain-bench') { throw 'Terrain bench has no AutoNav mission; use the bounded manual terrain verifier' }
            if ($null -ne $activeVariant.seed) { $loopArgs += @('--mission',"$linuxRoot/artifacts/courses/seed-$($activeVariant.seed)/mission.json",'--report',"$linuxRoot/artifacts/courses/seed-$($activeVariant.seed)/run.json") }
        }
        if ($Resume) { $loopArgs += '--resume' }
        Run-Ros $loopArgs
    }
    'loop-status' {
        $reportPath=Join-Path $repoRoot 'artifacts/checks/full-course-live.json'
        $activePath=Join-Path $repoRoot 'artifacts/session/course-variant.json'
        if(Test-Path -LiteralPath $activePath){$activeVariant=Get-Content -LiteralPath $activePath -Raw | ConvertFrom-Json;if($null -ne $activeVariant.seed){$reportPath=Join-Path $activeVariant.folder 'run.json'}}
        $report = Get-Content -LiteralPath $reportPath -Raw | ConvertFrom-Json
        $report | Select-Object status,completed_waypoints,total_waypoints,active_waypoint,pose,audit_error
        $report.audit | Select-Object progress_m,total_arc_m,traveled_m,ordered_waypoints_visited,complete
    }
    'loop-resume' { Run-Ros @('ros2','service','call','/mission/resume','std_srvs/srv/Trigger','{}') }
    'loop-cancel' { Run-Ros @('python3',"$linuxRoot/tools/cancel_mission.py") }
    'gps-list' { Run-Ros @('python3',"$linuxRoot/tools/gps_mission.py",'list',(GpsMissionPath)) }
    'gps-run' { Run-Ros @('python3',"$linuxRoot/tools/gps_mission.py",'run',(GpsMissionPath)) }
    'nav-start' { Session 'start' 'nav' }
    'perception-start' { Session 'start' 'perception' }
    'perception-stop' { Session 'stop' 'perception' }
    'nav-cancel' { Run-Ros @('python3',"$linuxRoot/tools/nav_control.py",'cancel') }
    'nav-stop' {
        try { Run-Ros @('python3',"$linuxRoot/tools/nav_control.py",'cancel') }
        finally { Session 'stop' 'nav' }
    }
    'nav-goal' {
        $culture = [Globalization.CultureInfo]::InvariantCulture
        Run-Ros @('python3',"$linuxRoot/tools/nav_control.py",'goal',$X.ToString($culture),$Y.ToString($culture),$Yaw.ToString($culture))
    }
    'course-build' {
        if (!(Test-Path $Unity)) { throw "Unity editor not found: $Unity" }
        if (@(Players).Count -gt 0) { throw 'Stop the simulator before rebuilding' }
        & wsl -d Ubuntu-24.04 -- python3 "$linuxRoot/tools/import_sooner_course.py"
        if ($LASTEXITCODE -ne 0) { throw 'Course staging failed' }
        & wsl -d Ubuntu-24.04 -- bash "$linuxRoot/tools/build_ros.sh"
        if ($LASTEXITCODE -ne 0) { throw 'ROS build failed' }
        $buildLog = Join-Path $logs 'sooner-course-build.log'
        $arguments = "-batchmode -quit -buildTarget Win64 -projectPath `"$project`" -executeMethod GroundRenderChecks.BuildCourse -logFile `"$buildLog`""
        $process = Start-Process -FilePath $Unity -ArgumentList $arguments -WindowStyle Hidden -PassThru
        $process.WaitForExit()
        if ($process.ExitCode -ne 0) { throw "Course build failed; inspect $buildLog" }
        Write-Output 'Built artifacts/build-course/IGVCCourse.exe'
    }
    'course-start' {
        $coursePlayer = Join-Path $repoRoot 'artifacts/build-course/IGVCCourse.exe'
        if (!(Test-Path $coursePlayer)) { throw 'Run course-build first' }
        if (@(Players).Count -gt 0) { throw 'A workspace simulator is already running; stop it before switching' }
        @{profile='reference'} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $repoRoot 'artifacts/session/course-variant.json')
        Session 'start' 'r3a'
        $playerLog = Join-Path $logs 'sooner-course-player.log'
        $windowStyle = if ($Visible) { 'Normal' } else { 'Hidden' }
        Start-Process -FilePath $coursePlayer -ArgumentList "-logFile `"$playerLog`"" -WindowStyle $windowStyle | Out-Null
        Write-Output 'Sooner AutoNav course with R3-a started. stop/status/rviz apply; test-pad wall checks do not apply.'
    }
    'drive-build' {
        if (!(Test-Path $Unity)) { throw "Unity editor not found: $Unity" }
        if (@(Players).Count -gt 0) { throw 'Stop the simulator before rebuilding' }
        & wsl -d Ubuntu-24.04 -- bash "$linuxRoot/tools/build_ros.sh"
        if ($LASTEXITCODE -ne 0) { throw 'ROS build failed' }
        $buildLog = Join-Path $logs 'r3a-drive-build.log'
        $arguments = "-batchmode -quit -buildTarget Win64 -projectPath `"$project`" -executeMethod R3aDriveBuild.Build -logFile `"$buildLog`""
        $process = Start-Process -FilePath $Unity -ArgumentList $arguments -WindowStyle Hidden -PassThru
        $process.WaitForExit()
        if ($process.ExitCode -ne 0) { throw "R3-a drive build failed; inspect $buildLog" }
        Write-Output 'Built artifacts/build-drive/R3aDrive.exe'
    }
    'drive-start' {
        $drivePlayer = Join-Path $repoRoot 'artifacts/build-drive/R3aDrive.exe'
        if (!(Test-Path $drivePlayer)) { throw 'Run drive-build first' }
        if (@(Players).Count -gt 0) { throw 'A workspace simulator is already running; stop it before switching' }
        Session 'start' 'r3a'
        $playerLog = Join-Path $logs 'r3a-drive-player.log'
        $windowStyle = if ($Visible) { 'Normal' } else { 'Hidden' }
        Start-Process -FilePath $drivePlayer -ArgumentList "-logFile `"$playerLog`"" -WindowStyle $windowStyle | Out-Null
        Write-Output 'R3-a ideal-motion simulator started. stop/status/test/rviz apply to this session.'
    }
    'robot-build' {
        if (!(Test-Path $Unity)) { throw "Unity editor not found: $Unity" }
        & wsl -d Ubuntu-24.04 -- bash "$linuxRoot/tools/build_ros.sh"
        if ($LASTEXITCODE -ne 0) { throw 'ROS description build failed' }
        $robotBuildLog = Join-Path $logs 'robot-build.log'
        $arguments = "-batchmode -quit -buildTarget Win64 -projectPath `"$project`" -executeMethod RobotInspectionBuild.Build -logFile `"$robotBuildLog`""
        $process = Start-Process -FilePath $Unity -ArgumentList $arguments -WindowStyle Hidden -PassThru
        $process.WaitForExit()
        if ($process.ExitCode -ne 0) { throw "Robot inspection build failed; inspect $robotBuildLog" }
        Write-Output 'Built artifacts/build-robot/R3aInspection.exe'
    }
    'robot-view' {
        if (@(RobotPlayers).Count -gt 0) { throw 'This workspace robot viewer is already running. Use robot-stop first.' }
        $robotPlayer = Join-Path $repoRoot 'artifacts/build-robot/R3aInspection.exe'
        if (!(Test-Path $robotPlayer)) { throw 'Run robot-build first' }
        $robotLog = Join-Path $logs 'robot-player.log'
        $windowStyle = if ($Visible) { 'Normal' } else { 'Hidden' }
        Start-Process -FilePath $robotPlayer -ArgumentList "-logFile `"$robotLog`"" -WindowStyle $windowStyle | Out-Null
    }
    'robot-rviz' {
        $previousDomain = $env:IGVC_ROS_DOMAIN_ID
        $previousWslEnv = $env:WSLENV
        try {
            # Static joint publisher must never compete with the transport probe on domain 42.
            $env:IGVC_ROS_DOMAIN_ID = '43'
            $env:WSLENV = (@($previousWslEnv, 'IGVC_ROS_DOMAIN_ID') | Where-Object { $_ }) -join ':'
            Run-Ros @('ros2','launch','igvc_description','display.launch.py','gui:=false')
        } finally { $env:IGVC_ROS_DOMAIN_ID = $previousDomain; $env:WSLENV = $previousWslEnv }
    }
    'robot-stop' { RobotPlayers | Stop-Process }
    'doctor' {
        Write-Output "Unity editor present: $(Test-Path $Unity)"
        Write-Output "Player built: $(Test-Path $player)"
        & wsl -l -v
        Run-Ros @('ros2','pkg','prefix','igvc_sim_bridge')
        Run-Ros @('ros2','pkg','prefix','rviz2')
        Run-Ros @('ros2','pkg','prefix','nav2_bringup')
    }
    'build' {
        if (!(Test-Path $Unity)) { throw "Unity editor not found: $Unity" }
        & wsl -d Ubuntu-24.04 -- bash "$linuxRoot/tools/build_ros.sh"
        if ($LASTEXITCODE -ne 0) { throw 'ROS build failed' }
        foreach ($method in @('ProbeChecks.Run','ProbeBuild.Build')) {
            $buildLog = Join-Path $logs "$method.log"
            $arguments = "-batchmode -quit -buildTarget Win64 -projectPath `"$project`" -executeMethod $method -logFile `"$buildLog`""
            $process = Start-Process -FilePath $Unity -ArgumentList $arguments -WindowStyle Hidden -PassThru
            $process.WaitForExit() # Wait for Editor, not persistent licensing descendants.
            if ($process.ExitCode -ne 0) { throw "Unity $method failed; inspect $buildLog" }
        }
        Write-Output "Built $player"
    }
    'start' {
        if (!(Test-Path $player)) { throw 'Run build first' }
        if (@(Players).Count -gt 0) { throw 'This workspace player is already running. Use status or stop.' }
        Session 'start'
        $playerLog = Join-Path $logs 'player.log'
        $windowStyle = if ($Visible) { 'Normal' } else { 'Hidden' }
        Start-Process -FilePath $player -ArgumentList "-logFile `"$playerLog`"" -WindowStyle $windowStyle | Out-Null
        Write-Output 'Probe started. Use status, rviz, and the WSL commands in docs/RUNBOOK.md.'
    }
    'stop' {
        Players | Stop-Process
        Session 'stop' 'nav'
        Session 'stop'
        Session 'stop' 'perception'
    }
    'status' {
        Session 'status'
        $ownedPlayers = @(Players)
        Write-Output "Unity players for this workspace: $($ownedPlayers.Count)"
        $ownedPlayers | Select-Object Id,Path
        Run-Ros @('ros2','topic','list','--no-daemon')
    }
    'test' {
        if (@(Players | Where-Object { $_.ProcessName -eq 'IGVCCourse' }).Count -gt 0) {
            throw 'The test command checks calibration-wall geometry. Stop the course and use drive-start for that suite.'
        }
        $mode = SessionMode
        Run-Ros @('ros2','run','igvc_sim_bridge','verify_probe','--mode',$mode,'--duration',"$Duration",'--report',"$linuxRoot/artifacts/checks/live-$mode.json")
    }
    'rviz' {
        $mode = SessionMode
        if (Test-Path (Join-Path $repoRoot 'artifacts/session/nav.json')) { $mode = 'nav' }
        Run-Ros @('rviz2','-d',"$linuxRoot/ros2/src/igvc_sim_bridge/rviz/$mode.rviz",'--ros-args','-p','use_sim_time:=true')
    }
}
