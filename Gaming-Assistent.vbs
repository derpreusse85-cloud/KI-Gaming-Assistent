' Startet den Gaming-Assistenten lautlos (kein Konsolenfenster).
' Der Pfad wird aus dem Skriptort abgeleitet - der Ordner darf verschoben werden.
Option Explicit

Dim shell, root, python
Set shell = CreateObject("WScript.Shell")
root = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
python = root & ".venv\Scripts\pythonw.exe"

If Not CreateObject("Scripting.FileSystemObject").FileExists(python) Then
    MsgBox "Umgebung fehlt:" & vbCrLf & python & vbCrLf & vbCrLf & _
           "Bitte zuerst scripts\setup_venv.ps1 ausfuehren.", 16, "Gaming-Assistent"
    WScript.Quit 1
End If

shell.CurrentDirectory = root
' 0 = verstecktes Fenster, False = nicht auf Beenden warten
shell.Run """" & python & """ -m gaming_assistant", 0, False
