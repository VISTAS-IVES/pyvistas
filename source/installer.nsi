!include MUI.nsh
!define MUI_ICON "..\resources\images\VISTAS.ico"

OutFile "VISTAS_1_13.exe"
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

	createDirectory "$SMPROGRAMS\VISTAS"
	createShortCut "$SMPROGRAMS\VISTAS\VISTAS.lnk" "$INSTDIR\VISTAS.exe"
	createShortCut "$SMPROGRAMS\VISTAS\Uninstall VISTAS.lnk" "$INSTDIR\uninstall.exe"

	WriteUninstaller "$INSTDIR\uninstall.exe"

SectionEnd

Section "uninstall"

	Delete "$INSTDIR\uninstall.exe"
	Delete "$SMPROGRAMS\VISTAS.lnk"
	RmDir /r $INSTDIR
	
SectionEnd