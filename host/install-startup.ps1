# Registers a per-user scheduled task that starts the roundtft monitor at logon,
# hidden (no window), and restarts it if it crashes. Run from any PowerShell:
#     powershell -ExecutionPolicy Bypass -File host\install-startup.ps1
# Re-running it safely replaces an existing task.
$ErrorActionPreference = 'Stop'

$TaskName = 'RoundTFT Monitor'
$vbs      = Join-Path $PSScriptRoot 'monitor-launch.vbs'
if (-not (Test-Path $vbs)) { throw "Missing $vbs" }

# wscript runs the .vbs, which launches the windowless .bat.
$action = New-ScheduledTaskAction -Execute 'wscript.exe' `
    -Argument ('"{0}"' -f $vbs)

# Start at this user's logon.
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

# Run as the interactive user (needed for COM port + ~/.claude/.credentials.json).
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive -RunLevel Limited

# No time limit (it runs forever); auto-restart on failure; OK on battery.
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Seconds 0)

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Principal $principal -Settings $settings `
    -Description 'Streams PC + Claude usage to the roundtft display at logon.' | Out-Null

Start-ScheduledTask -TaskName $TaskName

Write-Host "Installed and started '$TaskName'."
Write-Host "Log: $env:LOCALAPPDATA\roundtft-monitor.log"
Write-Host "Before flashing the board, stop it:  Stop-ScheduledTask -TaskName '$TaskName'"
