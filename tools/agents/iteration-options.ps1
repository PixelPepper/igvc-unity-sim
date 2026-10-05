# Option and command helpers for iteration-live.ps1 (T-0029). Pure functions except
# Test-SeedInputs, which only reads the generated course files; none takes the lease
# or starts a process.

function Test-SeedValue($Value) {
 # A JSON integer in 0..Int32.MaxValue. ConvertFrom-Json yields Int32/Int64 for JSON integers and
 # Decimal/Double (fractions, exponents), Boolean, String, arrays, objects or $null otherwise.
 return ((($Value -is [int]) -or ($Value -is [long])) -and $Value -ge 0 -and $Value -le [int]::MaxValue)
}

function Get-TrialSeed($Cfg) {
 # Absent means the existing seed 2027; anything but a JSON integer in range throws.
 $property=$Cfg.PSObject.Properties['seed']
 if($null -eq $property){return 2027}
 if(!(Test-SeedValue $property.Value)){throw 'seed must be a JSON integer in 0..2147483647'}
 return [int]$property.Value
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

function Read-SeededJson([string]$Path,[int]$Seed) {
 # The whole file must parse as one JSON object whose top-level "seed" is exactly the selected integer.
 # The root is checked in the text itself: ConvertFrom-Json unwraps a one-element root array
 # ([{"seed":N}]) into its object, so the parsed value alone cannot prove an object root.
 $text=Get-Content -LiteralPath $Path -Raw
 if($null -eq $text -or !$text.TrimStart([char]0xFEFF,' ',"`t","`r","`n").StartsWith('{')){throw "$Path root is not a JSON object"}
 try {$json=$text | ConvertFrom-Json}
 catch {throw "$Path is not valid JSON: $($_.Exception.Message)"}
 if($json -isnot [Management.Automation.PSCustomObject]){throw "$Path is not a JSON object"}
 $property=$json.PSObject.Properties['seed']
 if($null -eq $property){throw "$Path has no top-level seed"}
 if(!(Test-SeedValue $property.Value) -or [long]$property.Value -ne $Seed){
  throw "$Path top-level seed $(ConvertTo-Json $property.Value -Compress) is not the integer $Seed"
 }
 return $json
}

function Test-SeedInputs([string]$Workspace,[int]$Seed) {
 # What variant-start generated for this seed must say so: course.json and mission.json are complete
 # JSON objects with that top-level integer seed, and mission.json binds the exact course.json bytes
 # by sha256. autonomy.json (the sanitized mission given to autonomy) carries no seed; it is only
 # recorded by hash, generated alongside these. Throws on any mismatch so a run is never labelled
 # with a seed it did not use.
 $folder=Join-Path $Workspace "artifacts/courses/seed-$Seed"
 $course=Join-Path $folder 'course.json'; $mission=Join-Path $folder 'mission.json'; $autonomy=Join-Path $folder 'autonomy.json'
 foreach($path in @($course,$mission,$autonomy)){if(!(Test-Path -LiteralPath $path)){throw "Seed $Seed input missing: $path"}}
 Read-SeededJson $course $Seed | Out-Null
 $missionJson=Read-SeededJson $mission $Seed
 $courseSha=(Get-FileHash -LiteralPath $course -Algorithm SHA256).Hash.ToLowerInvariant()
 $bound=$missionJson.PSObject.Properties['course_sha256']
 if($null -eq $bound -or $bound.Value -isnot [string] -or $bound.Value -cne $courseSha){
  throw 'mission.json does not bind the generated course.json'
 }
 return @{seed=$Seed;course_sha256=$courseSha
  mission_sha256=(Get-FileHash -LiteralPath $mission -Algorithm SHA256).Hash.ToLowerInvariant()
  autonomy_sha256=(Get-FileHash -LiteralPath $autonomy -Algorithm SHA256).Hash.ToLowerInvariant()}
}
