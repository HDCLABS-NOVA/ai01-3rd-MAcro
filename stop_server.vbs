Set objWMI = GetObject("winmgmts:\\.\root\cimv2")
Set colProcesses = objWMI.ExecQuery("SELECT * FROM Win32_Process WHERE Name='python.exe'")

Dim bFound : bFound = False
For Each objProcess In colProcesses
    If InStr(objProcess.CommandLine, "main.py") > 0 Then
        objProcess.Terminate
        bFound = True
    End If
Next

If bFound Then
    MsgBox "✅ 서버가 종료되었습니다.", 64, "서버 종료"
Else
    MsgBox "실행 중인 서버가 없습니다.", 64, "서버 상태"
End If
