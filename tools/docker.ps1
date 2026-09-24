param(
    [Parameter(Position=0)]
    [ValidateSet('build','start','stop','status','rviz','shell','run','course','guided-course','sensor-audit','audit','prepare-unity','unity-build')]
    [string]$Action='status',
    [int]$Seed=2027,
    [ValidateSet('easy','normal','hard')][string]$Difficulty='normal',
    [string]$Unity='C:\Program Files\Unity\Hub\Editor\6000.3.23f1\Editor\Unity.exe',
    [Parameter(ValueFromRemainingArguments=$true)][string[]]$Command
)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $root
$script:igvcKeeperState=Join-Path $root 'artifacts/session/docker-wsl-keeper.json'
. (Join-Path $PSScriptRoot 'docker-wsl-lifetime.ps1')
function Compose([string[]]$Arguments) {
    & wsl -d Ubuntu-24.04 -u root -- docker compose @Arguments
    if($LASTEXITCODE -ne 0){throw "Docker Compose failed ($LASTEXITCODE)"}
}
function Exec-Ros([string[]]$Arguments) {
    Start-IgvcWslKeeper
    Compose (@('exec','-T','ros','/opt/igvc/docker/entrypoint.sh')+$Arguments)
}
$player=Join-Path $root 'artifacts/build-course/IGVCCourse.exe'
$state=Join-Path $root 'artifacts/session/docker-player.json'
switch($Action){
    'build' { Compose @('build') }
    'status' { Compose @('ps'); Exec-Ros @('ros2','topic','list','--no-daemon') }
    'shell' { Compose @('exec','ros','/opt/igvc/docker/entrypoint.sh','bash') }
    'run' { if(!$Command){throw 'Provide a ROS/container command after run'}; Exec-Ros $Command }
    'prepare-unity' {
        $linuxRoot=(& wsl -d Ubuntu-24.04 -- wslpath -a $root).Trim()
        & wsl -d Ubuntu-24.04 -- bash "$linuxRoot/docker/prepare-unity.sh"
        if($LASTEXITCODE -ne 0){throw 'Unity asset preparation failed'}
    }
    'unity-build' {
        if(!(Test-Path -LiteralPath $Unity)){throw 'Install Unity 6000.3.23f1 with Windows build support or pass -Unity'}
        New-Item -ItemType Directory -Force (Join-Path $root 'artifacts/logs') | Out-Null
        $log=Join-Path $root 'artifacts/logs/docker-unity-build.log'
        $project=Join-Path $root 'unity/IGVCSim'
        $proc=Start-Process -FilePath $Unity -ArgumentList "-batchmode -quit -buildTarget Win64 -projectPath `"$project`" -executeMethod GroundRenderChecks.BuildCourse -logFile `"$log`"" -WindowStyle Hidden -PassThru
        $proc.WaitForExit()
        if($proc.ExitCode -ne 0 -or !(Test-Path -LiteralPath $player)){throw "Unity build failed; inspect $log"}
    }
    'start' {
        if(!(Test-Path -LiteralPath $player)){throw 'Run prepare-unity then unity-build first'}
        if(Get-Process IGVCCourse -ErrorAction SilentlyContinue){throw 'Stop the existing course player first'}
        Start-IgvcWslKeeper
        Compose @('up','-d')
        Compose @('run','--rm','--no-deps','ros','python3','tools/generate_course_variant.py','--seed',"$Seed",'--difficulty',$Difficulty)
        $folder=Join-Path $root "artifacts/courses/seed-$Seed"
        New-Item -ItemType Directory -Force (Split-Path $state) | Out-Null
        $proc=Start-Process -FilePath $player -ArgumentList "--ros-ip 127.0.0.1 --ros-port 10000 --line-guard scoring --course-manifest `"$folder/course.json`" -logFile `"$folder/docker-unity.log`"" -WindowStyle Normal -PassThru
        @{pid=$proc.Id;start=$proc.StartTime.ToUniversalTime().ToString('o');seed=$Seed} | ConvertTo-Json | Set-Content -LiteralPath $state
        Write-Output 'Unity and container started. Run rviz, then course. Startup alone is not an integration test.'
    }
    'rviz' { Start-IgvcWslKeeper; Compose @('exec','ros','/opt/igvc/docker/entrypoint.sh','ros2','run','rviz2','rviz2','-d','/opt/igvc/install/igvc_sim_bridge/share/igvc_sim_bridge/rviz/nav.rviz','--ros-args','-p','use_sim_time:=true') }
    'guided-course' { Exec-Ros @('python3','tools/full_course.py','--mission',"/opt/igvc/artifacts/courses/seed-$Seed/mission.json",'--report',"/opt/igvc/artifacts/courses/seed-$Seed/docker-run.json") }
    'course' { Exec-Ros @('python3','tools/sensor_course.py','--mission',"/opt/igvc/artifacts/courses/seed-$Seed/autonomy.json",'--report',"/opt/igvc/artifacts/courses/seed-$Seed/sensor-run.json") }
    'sensor-audit' { Exec-Ros @('python3','tools/audit_sensor_run.py','--course',"/opt/igvc/artifacts/courses/seed-$Seed/course.json",'--run',"/opt/igvc/artifacts/courses/seed-$Seed/sensor-run.json",'--output',"/opt/igvc/artifacts/courses/seed-$Seed/sensor-audit.json") }
    'audit' { Exec-Ros @('python3','tools/audit_course_variant.py','--course',"/opt/igvc/artifacts/courses/seed-$Seed/course.json",'--run',"/opt/igvc/artifacts/courses/seed-$Seed/docker-run.json") }
    'stop' {
        if(Test-Path -LiteralPath $state){
            $saved=Get-Content -LiteralPath $state -Raw | ConvertFrom-Json
            $proc=Get-Process -Id $saved.pid -ErrorAction SilentlyContinue
            if($proc -and $proc.Path -eq $player -and $proc.StartTime.ToUniversalTime().ToString('o') -eq $saved.start){Stop-Process -Id $proc.Id}
            Remove-Item -LiteralPath $state
        }
        Compose @('down')
        Stop-IgvcWslKeeper
    }
}
