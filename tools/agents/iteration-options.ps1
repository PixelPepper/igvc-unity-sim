# Option and command helpers for iteration-live.ps1 (T-0029). Pure functions except
# Test-SeedInputs, which only reads the generated course files; none takes the lease
# or starts a process.

function Get-TrialSeed($Cfg) {
 # Absent means the existing seed 2027. Only a JSON integer in 0..Int32.MaxValue is accepted:
 # ConvertFrom-Json yields Int32/Int64 for integers and Decimal/Double/Boolean/String/null otherwise.
 $property=$Cfg.PSObject.Properties['seed']
 if($null -eq $property){return 2027}
 $value=$property.Value
 if(!(($value -is [int]) -or ($value -is [long])) -or $value -lt 0 -or $value -gt [int]::MaxValue){
  throw 'seed must be a JSON integer in 0..2147483647'
 }
 return [int]$value
}

function Get-TrialCommands {
 # Every seed-dependent argument of the trial, built in one place from the selected seed.
 param([int]$Seed,[string]$Workspace,[string]$LinuxRoot,[string]$LinuxJob,[string]$LinuxCoordinator,
       $BodyClearanceWeight,[bool]$RevalidateActivePath,[bool]$RecordEpisode)
 $course="$LinuxRoot/artifacts/courses/seed-$Seed"
 if($RecordEpisode) {
  $mission=@('bash',"$LinuxRoot/tools/run_ros.sh",'python3',"$LinuxCoordinator/tools/agents/iteration-mission.py",$LinuxRoot,$LinuxJob,'--seed',[string]$Seed)
 } else {
  $mission=@('bash',"$LinuxRoot/tools/run_ros.sh",'python3',"$LinuxRoot/tools/sensor_course.py",'--mission',"$course/autonomy.json",'--report',"$LinuxJob/run.json",'--capture-dir',"$LinuxJob/decisions",'--timeout','600','--speed','0.6','--planning-budget','0.5','--path-execution','checked-path')
  if($null -ne $BodyClearanceWeight){$mission+=@('--body-clearance-weight',[string]$BodyClearanceWeight)}
  if($RevalidateActivePath){$mission+='--revalidate-active-path'}
 }
 return @{
  start_seed=$Seed
  mission=$mission
  audit=@('bash',"$LinuxRoot/tools/run_ros.sh",'python3',"$LinuxRoot/tools/audit_sensor_run.py",'--run',"$LinuxJob/run.json",'--course',"$course/course.json",'--mission',"$course/autonomy.json",'--output',"$LinuxJob/audit.json")
  unity_log=(Join-Path $Workspace "artifacts/courses/seed-$Seed/unity.log")
 }
}

function Test-SeedInputs([string]$Workspace,[int]$Seed) {
 # The files variant-start generated for this seed must say so: course.json and mission.json carry
 # the seed, and mission.json binds course.json by sha256. Returns their identity for live.json;
 # throws on any mismatch so a run is never labelled with a seed it did not use.
 $folder=Join-Path $Workspace "artifacts/courses/seed-$Seed"
 $course=Join-Path $folder 'course.json'; $mission=Join-Path $folder 'mission.json'; $autonomy=Join-Path $folder 'autonomy.json'
 foreach($path in @($course,$mission,$autonomy)){if(!(Test-Path -LiteralPath $path)){throw "Seed $Seed input missing: $path"}}
 $missionJson=Get-Content -LiteralPath $mission -Raw | ConvertFrom-Json
 $courseHead=Get-Content -LiteralPath $course -TotalCount 40 | Out-String
 $courseSeed=if($courseHead -match '"seed"\s*:\s*(-?\d+)'){[long]$Matches[1]}else{$null}
 $courseSha=(Get-FileHash -LiteralPath $course -Algorithm SHA256).Hash.ToLowerInvariant()
 if($courseSeed -ne $Seed){throw "course.json seed $courseSeed does not match selected seed $Seed"}
 if($missionJson.seed -ne $Seed){throw "mission.json seed $($missionJson.seed) does not match selected seed $Seed"}
 if($missionJson.course_sha256 -ne $courseSha){throw 'mission.json does not bind the generated course.json'}
 return @{seed=$Seed;course_sha256=$courseSha
  mission_sha256=(Get-FileHash -LiteralPath $mission -Algorithm SHA256).Hash.ToLowerInvariant()
  autonomy_sha256=(Get-FileHash -LiteralPath $autonomy -Algorithm SHA256).Hash.ToLowerInvariant()}
}
