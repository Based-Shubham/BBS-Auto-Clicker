Set objShell = CreateObject("Shell.Application")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

' Explicitly cd /d into the script directory so Admin UAC doesn't default to System32
cmdLine = "/c cd /d """ & scriptDir & """ && uv run python main.py > run_log.txt 2>&1"

objShell.ShellExecute "cmd.exe", cmdLine, "", "runas", 0
