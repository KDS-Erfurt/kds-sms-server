!include "MUI.nsh"
!include "LogicLib.nsh"
!include "WinMessages.nsh"

Name "KDS SMS-Server"
!define INSTALLATION_NAME "KDS SMS-Server"
!define PROGRAM_FOLDER_NAME "SMS-Server"
!define SETTINGS_BACKUP_FILE "C:\KDS\sms_server\settings.json.backup"
OutFile "installer\installer.exe"
InstallDir "$PROGRAMFILES\KDS\${PROGRAM_FOLDER_NAME}"

!insertmacro MUI_PAGE_LICENSE "LICENSE"
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "german"


Var title
Var static
Var version
Var build_number
Var author
Var author_email
Var url
Var description

Function .onInit
  InitPluginsDir
  File /oname=$PLUGINSDIR\static.ini "static.ini"
  
  ReadINIStr $0 $INSTDIR\winamp.ini winamp outname

  ReadINIStr $title "$PLUGINSDIR\static.ini" "static" "title"
  ReadINIStr $static "$PLUGINSDIR\static.ini" "static" "static"
  ReadINIStr $version "$PLUGINSDIR\static.ini" "static" "version"
  ReadINIStr $build_number "$PLUGINSDIR\static.ini" "static" "build_number"
  ReadINIStr $author "$PLUGINSDIR\static.ini" "static" "author"
  ReadINIStr $author_email "$PLUGINSDIR\static.ini" "static" "author_email"
  ReadINIStr $url "$PLUGINSDIR\static.ini" "static" "url"
  ReadINIStr $description "$PLUGINSDIR\static.ini" "static" "description"
  
  SendMessage $HWNDPARENT ${WM_SETTEXT} 0 "STR:Your text"

  ${If} ${FileExists} "$INSTDIR\uninstall.exe"

    MessageBox MB_YESNO "Der KDS SMS-Servers ist bereits installtiert. Möchten Sie ein Update durchführen?" IDYES true IDNO false
    true:
      ExecWait '"$INSTDIR\uninstall.exe" /S _=$INSTDIR'
      Sleep 5000
    false:
      Abort

  ${EndIf}
FunctionEnd

Function un.isEmptyDir
  # Stack ->                    # Stack: <directory>
  Exch $0                       # Stack: $0
  Push $1                       # Stack: $1, $0
  FindFirst $0 $1 "$0\*.*"
  strcmp $1 "." 0 _notempty
    FindNext $0 $1
    strcmp $1 ".." 0 _notempty
      ClearErrors
      FindNext $0 $1
      IfErrors 0 _notempty
        FindClose $0
        Pop $1                  # Stack: $0
        StrCpy $0 1
        Exch $0                 # Stack: 1 (true)
        goto _end
     _notempty:
       FindClose $0
       ClearErrors
       Pop $1                   # Stack: $0
       StrCpy $0 0
       Exch $0                  # Stack: 0 (false)
  _end:
FunctionEnd


Section ""
  SetOutPath $INSTDIR
  File /r "dist\sms_server\*"
  WriteUninstaller "$INSTDIR\uninstall.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${INSTALLATION_NAME}" "DisplayName" "$title"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${INSTALLATION_NAME}" "DisplayVersion" "$version"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${INSTALLATION_NAME}" "DisplayIcon" "$INSTDIR\sms_server.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${INSTALLATION_NAME}" "Publisher" "$author"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${INSTALLATION_NAME}" "UninstallString" '"$INSTDIR\uninstall.exe"'
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${INSTALLATION_NAME}" "QuietUninstallString" '"$INSTDIR\uninstall.exe /S"'
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${INSTALLATION_NAME}" "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${INSTALLATION_NAME}" "NoRepair" 1
  
  ${If} ${FileExists} "${SETTINGS_BACKUP_FILE}"
    MessageBox MB_YESNO "Möchten Sie die zuvor gesicherte Konfigurationsdatei wiederherstellen?" IDYES true IDNO
    true:
      CopyFiles "${SETTINGS_BACKUP_FILE}" "$INSTDIR\settings.json"
  ${EndIf}
SectionEnd

Section "SMS-Server Dienst"
  ExecWait "$INSTDIR\sms_server_service.exe install"
SectionEnd

Section "Start Menü Icons"
  CreateDirectory "$SMPROGRAMS\KDS"
  CreateDirectory "$SMPROGRAMS\KDS\${PROGRAM_FOLDER_NAME}"
  CreateShortCut "$SMPROGRAMS\KDS\${PROGRAM_FOLDER_NAME}\Uninstall.lnk" "$INSTDIR\uninstall.exe" "" "$INSTDIR\uninstall.exe" 0
  CreateShortCut "$SMPROGRAMS\KDS\${PROGRAM_FOLDER_NAME}\SMS-Server.lnk" "$INSTDIR\sms_server.exe" "" "$INSTDIR\sms_server.exe" 0
SectionEnd

Section "Uninstall"
  ${If} ${FileExists} "$INSTDIR\settings.json"
    MessageBox MB_YESNO "Möchten Sie die Konfigurationsdatei sichern?" IDYES true IDNO
    true:
      CopyFiles "$INSTDIR\settings.json" "${SETTINGS_BACKUP_FILE}"
  ${EndIf}

  Delete "$SMPROGRAMS\KDS\${PROGRAM_FOLDER_NAME}\*"
  RMDir "$SMPROGRAMS\KDS\${PROGRAM_FOLDER_NAME}"
  
  Push "$SMPROGRAMS\KDS"
  Call un.isEmptyDir

  ExecWait "$INSTDIR\sms_server_service.exe stop"
  ExecWait "$INSTDIR\sms_server_service.exe remove"

  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${INSTALLATION_NAME}"
  
  RMDir /R /REBOOTOK "$INSTDIR"
SectionEnd