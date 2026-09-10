param(
    [int[]]$Seeds = @(2027,2028,2029),
    [ValidateSet('easy','normal','hard')][string]$Difficulty = 'normal',
    [ValidateRange(60,600)][int]$TimeoutSeconds = 180,
    [switch]$Visible
)
$ErrorActionPreference='Stop'
$entry=Join-Path $PSScriptRoot 'igvc.ps1'
$root=Split-Path $PSScriptRoot -Parent
$shellPath=(Get-Process -Id $PID).Path
$results=@()
& $entry loop-cancel
# Bounded cancellation above also waits for the previous observer's lock release.
foreach($seed in $Seeds){
    & $entry stop
    & $entry variant-start -Seed $seed -Difficulty $Difficulty -Visible:$Visible
    & $entry nav-start
    $folder=Join-Path $root "artifacts/courses/seed-$seed"
    if(Test-Path -LiteralPath (Join-Path $folder 'run.json')){
        throw 'Variant generation left an old run report; refusing ambiguous evidence'
    }
    $missionProcess=Start-Process -FilePath $shellPath -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$entry`" loop-run" -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $folder 'mission.stdout.log') -RedirectStandardError (Join-Path $folder 'mission.stderr.log')
    $deadline=(Get-Date).AddSeconds($TimeoutSeconds)
    $report=$null
    while((Get-Date) -lt $deadline -and !$missionProcess.HasExited){
        Start-Sleep -Seconds 2
        $reportPath=Join-Path $folder 'run.json'
        if(Test-Path -LiteralPath $reportPath){
            $report=Get-Content -LiteralPath $reportPath -Raw | ConvertFrom-Json
            if($report.status -in @('completed','failed','paused')){break}
        }
    }
    if(!$missionProcess.HasExited -and $report.status -ne 'completed'){
        & $entry loop-cancel
        if(!$missionProcess.WaitForExit(10000)){throw 'Mission did not acknowledge cancellation; suite stopped'}
    }
    if(!$missionProcess.HasExited -and !$missionProcess.WaitForExit(10000)){
        throw 'Completed mission did not exit; suite stopped before switching maps'
    }
    if(Test-Path -LiteralPath (Join-Path $folder 'run.json')){
        & $entry variant-audit -Seed $seed
        $audit=Get-Content -LiteralPath (Join-Path $folder 'validation.json') -Raw | ConvertFrom-Json
        $results+=@{seed=$seed;difficulty=$Difficulty;validation=$audit}
    }else{$results+=@{seed=$seed;difficulty=$Difficulty;error='No run report produced'}}
    $results | ConvertTo-Json -Depth 15 | Set-Content -LiteralPath (Join-Path $root 'artifacts/courses/suite.json')
    Write-Output "Finished seed $seed; evidence in $folder"
}
# Keep the last course visible and stopped for inspection. Every motion action
# above belongs to this suite; no unfinished mission is intentionally left active.
