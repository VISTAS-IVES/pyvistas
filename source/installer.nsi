!include MUI.nsh
!define MUI_ICON "..\resources\images\VISTAS.ico"

OutFile "VISTAS_1_19_0.exe"
InstallDir $PROGRAMFILES64\VISTAS
Name VISTAS

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "English"

Section

	SetOutPath $INSTDIR
	File /r "build\exe.win-amd64-3.5\"

	createShortCut "$SMPROGRAMS\VISTAS.lnk" "$INSTDIR\VISTAS.exe"

	WriteUninstaller "$INSTDIR\uninstall.exe"

	WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\VISTAS" "DisplayName" "VISTAS"
	WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\VISTAS" "DisplayIcon" "$\"$INSTDIR\resources\images\vistas.ico$\""
	WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\VISTAS" "Publisher" "Conservation Biology Institute"
	WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\VISTAS" "URLInfoAbout" "https://github.com/VISTAS-IVES/pyvistas"
	WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\VISTAS" "UninstallString" "$\"$INSTDIR\uninstall.exe$\""

SectionEnd

Section "uninstall"

	Delete "$INSTDIR\uninstall.exe"
	Delete "$SMPROGRAMS\VISTAS.lnk"
	RmDir /r $INSTDIR

	DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\VISTAS"
	
SectionEnd

Function .onInit
	ReadRegStr $R0 HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\VISTAS" "UninstallString"
	StrCmp $R0 "" done

	MessageBox MB_OKCANCEL|MB_ICONEXCLAMATION "Click `OK` to uninstall the old version of VISTAS" IDOK uninstall
  	Abort

uninstall:	
	ClearErrors
	Exec $INSTDIR\uninstall.exe

done:
FunctionEnd
