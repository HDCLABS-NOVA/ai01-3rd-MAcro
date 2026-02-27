Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

strDir = objFSO.GetParentFolderName(WScript.ScriptFullName)
objShell.CurrentDirectory = strDir

' 이미 실행 중인 서버가 있으면 알림
Set objWMI = GetObject("winmgmts:\\.\root\cimv2")
Set colProcesses = objWMI.ExecQuery("SELECT * FROM Win32_Process WHERE Name='python.exe'")

For Each objProcess In colProcesses
    If InStr(objProcess.CommandLine, "main.py") > 0 Then
        MsgBox "서버가 이미 실행 중입니다." & Chr(13) & "종료하려면 stop_server.vbs를 실행하세요.", 64, "서버 상태"
        WScript.Quit
    End If
Next

' 서버 백그라운드 실행 (터미널 창 없음, 로그는 server.log에 저장)
objShell.Run "cmd /c python main.py > server.log 2>&1", 0, False

WScript.Sleep 2000

' 실행 확인
Set colProcesses2 = objWMI.ExecQuery("SELECT * FROM Win32_Process WHERE Name='python.exe'")
Dim bFound : bFound = False
For Each objProcess In colProcesses2
    If InStr(objProcess.CommandLine, "main.py") > 0 Then
        bFound = True
    End If
Next

If bFound Then
    MsgBox "✅ 서버가 시작되었습니다!" & Chr(13) & "http://localhost:8000" & Chr(13) & Chr(13) & "로그: server.log", 64, "서버 시작"
Else
    MsgBox "❌ 서버 시작 실패. server.log를 확인하세요.", 16, "오류"
End If
