# Run interactively. DPAPI encrypts this credential for the current Windows user.
$ErrorActionPreference = 'Stop'
$credentialDir = Join-Path $env:LOCALAPPDATA 'IGVCSim'
New-Item -ItemType Directory -Force $credentialDir | Out-Null
$cursorCredential = Read-Host 'Cursor user API key (hidden)' -AsSecureString
$cursorCredential | ConvertFrom-SecureString | Set-Content -LiteralPath (Join-Path $credentialDir 'cursor-key.dpapi')
Remove-Variable cursorCredential
Write-Output 'Cursor credential saved outside the repository with Windows user encryption.'
