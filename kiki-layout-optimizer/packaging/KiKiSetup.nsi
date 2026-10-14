; KiKi optional Windows GUI installer; source and scripts remain independently distributable.
!include "MUI2.nsh"
!include "LogicLib.nsh"
!ifndef PAYLOAD
  !error "Define /DPAYLOAD=<absolute path to Windows portable folder>"
!endif
!ifndef OUTPUT
  !define OUTPUT "KiKi-v0.7.2-Windows-Setup.exe"
!endif
Name "KiKi Models Layout Optimizer v0.7.2"
OutFile "${OUTPUT}"
InstallDir "$LOCALAPPDATA\KiKiModels\LayoutOptimizer"
RequestExecutionLevel user
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"
Var installExit
Section "Install"
  SetOutPath "$INSTDIR"
  File /r "${PAYLOAD}\*.*"
  ; The PowerShell script verifies SHA-256 and installs the CEP extension.
  ; Unsigned Adobe developer-mode preference remains disabled until opt-in.
  nsExec::ExecToLog 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$INSTDIR\installers\windows\install.ps1" -SkipCopy'
  Pop $installExit
  ${If} $installExit != 0
    MessageBox MB_ICONSTOP "KiKi installation failed integrity verification or CEP setup. Inspect the portable package."
    Abort
  ${EndIf}
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\KiKiLayoutOptimizer" "DisplayName" "KiKi Models Layout Optimizer"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\KiKiLayoutOptimizer" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\KiKiLayoutOptimizer" "DisplayVersion" "0.7.2"
SectionEnd
Section "Uninstall"
  ; Remove only KiKi-owned runtime and CEP; workspace/presets remain untouched.
  nsExec::ExecToLog 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$INSTDIR\installers\windows\uninstall.ps1"'
  Pop $installExit
  ${If} $installExit != 0
    MessageBox MB_ICONEXCLAMATION "Could not complete KiKi uninstall. Check installation folder manually."
    Abort
  ${EndIf}
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\KiKiLayoutOptimizer"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"
SectionEnd
