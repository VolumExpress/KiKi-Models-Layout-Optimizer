Option Explicit
Dim ai, scriptFile
If WScript.Arguments.Count <> 1 Then
  WScript.StdErr.WriteLine "Usage: cscript //nologo run_action_windows.vbs path-to-jsx"
  WScript.Quit 2
End If
scriptFile = WScript.Arguments(0)
On Error Resume Next
Set ai = GetObject(, "Illustrator.Application")
If Err.Number <> 0 Or (ai Is Nothing) Then
  WScript.StdErr.WriteLine "Cannot connect to a running Adobe Illustrator. " & Err.Description
  WScript.Quit 3
End If
Err.Clear
ai.DoJavaScriptFile scriptFile
If Err.Number <> 0 Then
  WScript.StdErr.WriteLine "Illustrator automation error: " & Err.Description
  WScript.Quit 4
End If
WScript.Quit 0
