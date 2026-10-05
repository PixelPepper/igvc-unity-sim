# Behavior tests for T-0029 trial seed options (Windows PowerShell 5). No lease, simulator or ROS work:
# full-script runs use only invalid configs, which must stop before writing live.json or the lease.
$ErrorActionPreference='Stop'
$agents=$PSScriptRoot
. (Join-Path $agents 'iteration-options.ps1')
$failures=New-Object System.Collections.Generic.List[string]
$passed=0
function Check([bool]$Condition,[string]$Name){
 if($Condition){$script:passed++}else{$script:failures.Add($Name)}
}
function Throws([scriptblock]$Block){try{& $Block;return $false}catch{return $true}}

# Seed validation (as ConvertFrom-Json types it).
$valid=[ordered]@{'{}'=2027;'{"seed":2027}'=2027;'{"seed":2028}'=2028;'{"seed":2029}'=2029;'{"seed":0}'=0;'{"seed":2147483647}'=2147483647}
foreach($json in $valid.Keys){Check ((Get-TrialSeed ($json|ConvertFrom-Json)) -eq $valid[$json]) "valid seed $json"}
foreach($json in @('{"seed":true}','{"seed":false}','{"seed":null}','{"seed":"2028"}','{"seed":2028.5}','{"seed":2028.0}',
                   '{"seed":-1}','{"seed":2147483648}','{"seed":1e3}','{"seed":[2028]}','{"seed":{}}')){
 $cfg=$json|ConvertFrom-Json
 Check (Throws {Get-TrialSeed $cfg}) "invalid seed rejected $json"
}

# Command construction: every seed-dependent consumer follows the selected seed.
$legacy=@('bash','/r/tools/run_ros.sh','python3','/r/tools/sensor_course.py','--mission','/r/artifacts/courses/seed-2027/autonomy.json','--report','/j/run.json','--capture-dir','/j/decisions','--timeout','600','--speed','0.6','--planning-budget','0.5','--path-execution','checked-path')
$base=Get-TrialCommands -Seed 2027 -Workspace 'C:\w' -LinuxRoot '/r' -LinuxJob '/j' -LinuxCoordinator '/c' -BodyClearanceWeight $null -RevalidateActivePath $false -RecordEpisode $false
Check (($base.mission -join '|') -eq ($legacy -join '|')) 'default 2027 mission identical to previous runner'
Check (($base.audit -join '|') -eq ('bash|/r/tools/run_ros.sh|python3|/r/tools/audit_sensor_run.py|--run|/j/run.json|--course|/r/artifacts/courses/seed-2027/course.json|--mission|/r/artifacts/courses/seed-2027/autonomy.json|--output|/j/audit.json')) 'default 2027 audit identical'
foreach($seed in @(2027,2028,2029)){
 foreach($record in @($false,$true)){
  $c=Get-TrialCommands -Seed $seed -Workspace 'C:\w' -LinuxRoot '/r' -LinuxJob '/j' -LinuxCoordinator '/c' -BodyClearanceWeight 0.25 -RevalidateActivePath (!$record) -RecordEpisode $record
  $seedArgs=@($c.mission+$c.audit+@($c.unity_log)|Where-Object{$_ -match 'seed-\d+'})
  Check ($c.start_seed -eq $seed) "start seed $seed record=$record"
  Check (@($seedArgs|Where-Object{$_ -notmatch "seed-$seed[\\/]"}).Count -eq 0 -and $seedArgs.Count -ge 3) "all course paths use seed-$seed record=$record"
  Check ($c.unity_log -eq "C:\w\artifacts\courses\seed-$seed\unity.log") "unity log seed $seed"
  if($record){
   Check (($c.mission -join '|') -eq "bash|/r/tools/run_ros.sh|python3|/c/tools/agents/iteration-mission.py|/r|/j|--seed|$seed") "recording mode passes --seed $seed only"
  } else {
   Check (($c.mission[-3..-1] -join '|') -eq '--body-clearance-weight|0.25|--revalidate-active-path') "normal options preserved seed $seed"
  }
 }
}

# Generated-input identity.
$tmp=Join-Path ([IO.Path]::GetTempPath()) ('t0029-'+[guid]::NewGuid())
function Make-Inputs([int]$Folder,[int]$CourseSeed,[int]$MissionSeed,[switch]$BadHash,[switch]$NoAutonomy){
 $dir=Join-Path $tmp "artifacts/courses/seed-$Folder"; New-Item -ItemType Directory -Force $dir | Out-Null
 $course=Join-Path $dir 'course.json'
 Set-Content -LiteralPath $course -Value "{`n  `"schema_version`": 1,`n  `"seed`": $CourseSeed,`n  `"centerline`": []`n}" -Encoding Ascii
 $sha=(Get-FileHash -LiteralPath $course -Algorithm SHA256).Hash.ToLowerInvariant()
 if($BadHash){$sha='0'*64}
 Set-Content -LiteralPath (Join-Path $dir 'mission.json') -Value "{`"seed`": $MissionSeed, `"course_sha256`": `"$sha`"}" -Encoding Ascii
 $autonomy=Join-Path $dir 'autonomy.json'
 if($NoAutonomy){Remove-Item -LiteralPath $autonomy -ErrorAction SilentlyContinue}else{Set-Content -LiteralPath $autonomy -Value '{"goals": []}' -Encoding Ascii}
}
try {
 Make-Inputs 2028 2028 2028
 $identity=Test-SeedInputs $tmp 2028
 Check ($identity.seed -eq 2028 -and $identity.course_sha256.Length -eq 64 -and $identity.autonomy_sha256.Length -eq 64) 'matching 2028 inputs accepted with hashes'
 Make-Inputs 2029 2027 2029; Check (Throws {Test-SeedInputs $tmp 2029}) 'course seed mismatch rejected'
 Make-Inputs 2029 2029 2027; Check (Throws {Test-SeedInputs $tmp 2029}) 'mission seed mismatch rejected'
 Make-Inputs 2029 2029 2029 -BadHash; Check (Throws {Test-SeedInputs $tmp 2029}) 'unbound course rejected'
 Make-Inputs 2029 2029 2029 -NoAutonomy; Check (Throws {Test-SeedInputs $tmp 2029}) 'missing autonomy rejected'
 Check (Throws {Test-SeedInputs $tmp 2031}) 'missing seed folder rejected'

 # Full runner: invalid options stop before live.json or the lease exist.
 $cases=[ordered]@{
  'seed string'='"seed":"2028"'; 'seed negative'='"seed":-1'; 'seed bool'='"seed":true'; 'seed fraction'='"seed":2028.5'
  'revalidate string'='"revalidate_active_path":"true"'; 'revalidate with record'='"revalidate_active_path":true,"record_episode":true'
 }
 foreach($name in $cases.Keys){
  $job=Join-Path $tmp ('job-'+($name -replace ' ','-')); $coordinator=Join-Path $tmp ('coord-'+($name -replace ' ','-'))
  New-Item -ItemType Directory -Force $job,(Join-Path $coordinator 'artifacts/iterations') | Out-Null
  $config=Join-Path $job 'config.json'
  $jobJson=$job.Replace('\','\\'); $coordJson=$coordinator.Replace('\','\\')
  Set-Content -LiteralPath $config -Value "{`"job`":`"$jobJson`",`"coordinator`":`"$coordJson`",`"workspace`":`"$coordJson`",`"role`":`"t`",$($cases[$name])}" -Encoding Ascii
  # PowerShell 5 turns redirected native stderr into errors; the exit code decides here.
  $ErrorActionPreference='Continue'
  $output=& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $agents 'iteration-live.ps1') -Config $config 2>&1 | Out-String
  $code=$LASTEXITCODE
  $ErrorActionPreference='Stop'
  Check ($code -ne 0) "runner exits non-zero: $name"
  Check (!(Test-Path (Join-Path $job 'live.json'))) "no live.json: $name"
  Check (!(Test-Path (Join-Path $coordinator 'artifacts/iterations/live.lock'))) "no lease file: $name"
  Check ($output -match 'seed must be|revalidate_active_path') "reason reported: $name"
 }
} finally {Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue}

"passed=$passed failed=$($failures.Count)"
foreach($f in $failures){"FAIL: $f"}
if($failures.Count){exit 1}
exit 0
