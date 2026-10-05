$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent
$desktop = [Environment]::GetFolderPath('Desktop')
$shortcutPath = Join-Path $desktop 'IGVC Latest Run + RViz.lnk'
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$shortcut.Arguments = '-NoProfile -ExecutionPolicy Bypass -File "' + (Join-Path $PSScriptRoot 'latest-run.ps1') + '"'
$shortcut.WorkingDirectory = $repoRoot
$shortcut.Description = 'Open Unity and RViz using the successful 6/6 profile. Press Enter to start the lap.'
$shortcut.WindowStyle = 1
$shortcut.IconLocation = (Join-Path $repoRoot 'artifacts/build-course/IGVCCourse.exe') + ',0'
$shortcut.Save()
Write-Output "Created: $shortcutPath"
