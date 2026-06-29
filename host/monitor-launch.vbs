' Launches run-monitor-hidden.bat completely hidden (window style 0) so the
' scheduled task starts the monitor with no flash of a console window.
Set fso = CreateObject("Scripting.FileSystemObject")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = dir
sh.Run """" & dir & "\run-monitor-hidden.bat""", 0, False
