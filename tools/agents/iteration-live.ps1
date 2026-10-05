param([Parameter(Mandatory=$true)][string]$Config)
$ErrorActionPreference='Stop'
$cfg=Get-Content -LiteralPath $Config -Raw | ConvertFrom-Json
# Optional opt-in (T-0021): absent means off; only a JSON boolean is accepted, before any lease or runtime work.
$revalidateActivePath=$false
if($null -ne $cfg.PSObject.Properties['revalidate_active_path']){
 if($cfg.revalidate_active_path -isnot [bool]){throw 'revalidate_active_path must be a JSON boolean (true or false)'}
 $revalidateActivePath=$cfg.revalidate_active_path
 if($revalidateActivePath -and $cfg.record_episode){throw 'revalidate_active_path is not supported with record_episode'}
}
$job=$cfg.job
$state=@{status='running';stage='waiting_for_lease';role=$cfg.role;started_utc=[DateTime]::UtcNow.ToString('o')}
function Save-State { $state | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $job 'live.json') }
function Stage([string]$Value) { $state.stage=$Value; Save-State }
function Wsl-Step([string]$Name,[string[]]$Arguments,[switch]$AllowFailure) {
 $savedErrorPreference=$ErrorActionPreference
 try {
  # Windows PowerShell wraps native stderr (including successful build warnings)
  # as NativeCommandError; the native exit code, not stderr presence, decides failure.
  $ErrorActionPreference='Continue'
  & wsl -d Ubuntu-24.04 -- @Arguments *> (Join-Path $job ($Name+'.log'))
  $code=$LASTEXITCODE
 } finally {$ErrorActionPreference=$savedErrorPreference}
 if($code -ne 0 -and !$AllowFailure){throw "$Name failed ($code); inspect $Name.log"}
 return $code
}
Save-State
$lease=$null
$ownsRuntime=$false
$shutdownVerified=$false
$leasePath=Join-Path $cfg.coordinator 'artifacts/iterations/live.lock'
try {
 $waitUntil=[DateTime]::UtcNow.AddMinutes(18)
 while(!$lease) {
  try {$lease=[IO.File]::Open($leasePath,[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)}
  catch [IO.IOException] {if([DateTime]::UtcNow -ge $waitUntil){throw 'Simulator lease wait timed out'};Start-Sleep -Seconds 3}
 }
 Stage 'preflight'
 # Never stop an unrelated player to obtain this lease.
 if(@(Get-Process IGVCProbe,R3aDrive,IGVCCourse,IGVCTerrain -ErrorAction SilentlyContinue).Count){throw 'A simulator already exists; refusing to interrupt it'}
 $portCheck=& wsl -d Ubuntu-24.04 -- bash -c 'ss -H -ltn sport = :10000'
 if($portCheck){throw 'TCP10000 is already occupied; refusing to interrupt it'}
 $currentHead=(& git -C $cfg.workspace rev-parse HEAD).Trim()
 if((& git -C $cfg.workspace status --porcelain)){throw 'Commit scoped edits before live trial'}
 $state.commit=$currentHead
 $state.profile_sha256=(Get-FileHash (Join-Path $job 'profile.yaml') -Algorithm SHA256).Hash.ToLowerInvariant()
 $assembly=Join-Path $cfg.workspace 'artifacts/build-course/IGVCCourse_Data/Managed/Assembly-CSharp.dll'
 $state.player_assembly_sha256=(Get-FileHash $assembly -Algorithm SHA256).Hash.ToLowerInvariant()
 $linuxRoot=(& wsl -d Ubuntu-24.04 -- wslpath -a $cfg.workspace).Trim()
 $linuxJob=(& wsl -d Ubuntu-24.04 -- wslpath -a $job).Trim()
 $env:IGVC_ROS_WORKSPACE=$cfg.ros_workspace
 $env:WSLENV=if($env:WSLENV){$env:WSLENV+':IGVC_ROS_WORKSPACE'}else{'IGVC_ROS_WORKSPACE'}
 $linuxCoordinator=(& wsl -d Ubuntu-24.04 -- wslpath -a $cfg.coordinator).Trim()
 Stage 'building_ros'
 Wsl-Step 'build' @('bash',"$linuxCoordinator/tools/agents/iteration-build.sh",$linuxRoot) | Out-Null
 Wsl-Step 'verify-overlay' @('bash',"$linuxRoot/tools/run_ros.sh",'python3',"$linuxCoordinator/tools/agents/verify_iteration_overlay.py",$linuxRoot,$cfg.ros_workspace) | Out-Null
 Stage 'starting_simulator'
 $ownsRuntime=$true
 & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $cfg.workspace 'tools/igvc.ps1') variant-start -Seed 2027 *> (Join-Path $job 'start.log')
 if($LASTEXITCODE -ne 0){throw 'Simulator start failed'}
 Wsl-Step 'nav-start' @('python3',"$linuxRoot/tools/ros_session.py",'start','nav','--params-file',"$linuxJob/profile.yaml") | Out-Null
 Stage 'mission'
 if($cfg.record_episode) {
  $state.mission_exit=Wsl-Step 'mission' @('bash',"$linuxRoot/tools/run_ros.sh",'python3',"$linuxCoordinator/tools/agents/iteration-mission.py",$linuxRoot,$linuxJob) -AllowFailure
 } else {
 $missionArgs=@('bash',"$linuxRoot/tools/run_ros.sh",'python3',"$linuxRoot/tools/sensor_course.py",'--mission',"$linuxRoot/artifacts/courses/seed-2027/autonomy.json",'--report',"$linuxJob/run.json",'--capture-dir',"$linuxJob/decisions",'--timeout','600','--speed','0.6','--planning-budget','0.5','--path-execution','checked-path')
 if($null -ne $cfg.body_clearance_weight){$missionArgs+=@('--body-clearance-weight',[string]$cfg.body_clearance_weight)}
 if($revalidateActivePath){$missionArgs+='--revalidate-active-path'}
 $state.mission_exit=Wsl-Step 'mission' $missionArgs -AllowFailure
 }
 Stage 'audit'
 if(Test-Path -LiteralPath (Join-Path $job 'run.json')) {
  $state.audit_exit=Wsl-Step 'audit' @('bash',"$linuxRoot/tools/run_ros.sh",'python3',"$linuxRoot/tools/audit_sensor_run.py",'--run',"$linuxJob/run.json",'--course',"$linuxRoot/artifacts/courses/seed-2027/course.json",'--mission',"$linuxRoot/artifacts/courses/seed-2027/autonomy.json",'--output',"$linuxJob/audit.json") -AllowFailure
  $result=Get-Content (Join-Path $job 'run.json') -Raw | ConvertFrom-Json
  $state.result=@{status=$result.status;reason=$result.reason;completed_destinations=$result.completed_destinations;elapsed_wall_s=$result.elapsed_wall_s}
 }
 $state.status='completed'
} catch {$state.status='failed';$state.error=$_.Exception.Message}
finally {
 if($ownsRuntime) {
  Stage 'stopping'
  & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $cfg.workspace 'tools/igvc.ps1') stop *> (Join-Path $job 'stop.log')
  $shutdownVerified=($LASTEXITCODE -eq 0)
  if(!$shutdownVerified){$state.status='failed';$state.error='Shutdown did not verify; coordinator must inspect shared runtime'}
  foreach($logName in @('nav-session.log','ros-session.log')) {
   $sourceLog=Join-Path $cfg.workspace ('artifacts/logs/'+$logName)
   try {if(Test-Path -LiteralPath $sourceLog){Copy-Item -LiteralPath $sourceLog -Destination (Join-Path $job $logName)}}
   catch {$state.log_capture_error=$_.Exception.Message}
  }
  try {
   $unityLog=Join-Path $cfg.workspace 'artifacts/courses/seed-2027/unity.log'
   if(Test-Path -LiteralPath $unityLog){Copy-Item -LiteralPath $unityLog -Destination (Join-Path $job 'unity.log')}
  } catch {$state.log_capture_error=$_.Exception.Message}
 }
 $state.shutdown_verified=$shutdownVerified
 $state.stage='finished';$state.finished_utc=[DateTime]::UtcNow.ToString('o');Save-State
 if($ownsRuntime -and !$shutdownVerified -and $lease) {
  # Keep ownership while any ROS command authority may remain. Coordinator must
  # inspect/stop the recorded session before ending this lease-holder process.
  $state.lease_retained_for_manual_cleanup=$true;Save-State
  while($true){Start-Sleep -Seconds 30}
 }
 if($lease){$lease.Dispose()}
}
