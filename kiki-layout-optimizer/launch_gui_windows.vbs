' Open the local GUI without displaying a PowerShell/command window.
Dim fso, shell, project, python, launcher
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
project = fso.GetParentFolderName(WScript.ScriptFullName)
python = project & "\.venv\Scripts\pythonw.exe"
If Not fso.FileExists(python) Then
  MsgBox "KiKi: Python environment missing. Run install_windows.bat once.", 48, "KiKi Models"
Else
  launcher = """" & python & """ -m kiki_layout.gui"
  shell.CurrentDirectory = project
  shell.Run launcher, 1, False
End If
