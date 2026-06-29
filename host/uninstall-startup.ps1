# Removes the roundtft monitor autostart task.
#     powershell -ExecutionPolicy Bypass -File host\uninstall-startup.ps1
$ErrorActionPreference = 'Stop'
$TaskName = 'RoundTFT Monitor'
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Stop-ScheduledTask  -TaskName $TaskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Removed '$TaskName'."
} else {
    Write-Host "'$TaskName' not found; nothing to do."
}
