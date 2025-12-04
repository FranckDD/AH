; -----------------------------------------------------------------------------
; Glostone-Kare - Inno Setup installer script (complete + auto slideshow)
; Place this file next to your project root and adjust paths if needed.
; -----------------------------------------------------------------------------

[Setup]
AppName=Glostone-Kare
AppVersion=1.0
DefaultDirName={pf}\Glostone-Kare
DefaultGroupName=Glostone-Kare
OutputDir=installer_build
OutputBaseFilename=Glostone-Kare-Setup
Compression=lzma
SolidCompression=yes
SetupIconFile=assets\glostone-kare.ico
UninstallDisplayIcon={app}\Glostone-Kare.exe
ArchitecturesInstallIn64BitMode=x64

; Left-side initial picture (will be changed dynamically by the script)
WizardImageFile=assets\gk_for_installation\gk1.bmp

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Files]
; L'exécutable PyInstaller (vérifie le chemin dist\...)
Source: "dist\Glostone-Kare.exe"; DestDir: "{app}"; Flags: ignoreversion
; Assets généraux (icône, images, config, etc.)
Source: "assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs

; Slides copiées dans {tmp} (utilisées pour le slideshow)
Source: "assets\gk_for_installation\gk1.bmp"; DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "assets\gk_for_installation\gk2.bmp"; DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "assets\gk_for_installation\gk3.bmp"; DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "assets\gk_for_installation\gk4.bmp"; DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "assets\gk_for_installation\gk5.bmp"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Icons]
Name: "{group}\Glostone-Kare"; Filename: "{app}\Glostone-Kare.exe"; WorkingDir: "{app}"; IconFilename: "{app}\assets\glostone-kare.ico"
Name: "{userdesktop}\Glostone-Kare"; Filename: "{app}\Glostone-Kare.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Registry]
; Stocke l'URL de l'API (AH2_API_BASE) comme variable d'environnement utilisateur
Root: HKCU; Subkey: "Environment"; ValueType: string; ValueName: "AH2_API_BASE"; ValueData: "https://web-production-d587.up.railway.app"; Flags: preservestringtype

[Run]
; Option : lancer l'app après l'installation (coché si l'utilisateur le veut via la page finale)
Filename: "{app}\Glostone-Kare.exe"; Description: "Launch Glostone-Kare"; Flags: nowait postinstall skipifsilent unchecked

[UninstallRun]
Filename: "reg"; Parameters: "delete HKCU\Environment /v AH2_API_BASE /f"; Flags: runhidden

[Code]
; -------------------------
; Auto slideshow + wizard pages
; -------------------------
const
  GWL_WNDPROC = -4;
  WM_TIMER = 275;

type
  TWndProc = function(hWnd: Integer; Msg: Integer; wParam: Integer; lParam: Integer): Integer; stdcall;

function SetWindowLongPtr(hWnd: Integer; nIndex: Integer; dwNewLong: Integer): Integer; external 'SetWindowLongPtrW@user32.dll stdcall';
function CallWindowProc(lpPrevWndFunc: Integer; hWnd: Integer; Msg: Integer; wParam: Integer; lParam: Integer): Integer; external 'CallWindowProcW@user32.dll stdcall';
function SetTimer(hWnd: Integer; nIDEvent: Integer; uElapse: Integer; lpTimerFunc: Integer): Integer; external 'SetTimer@user32.dll stdcall';
function KillTimer(hWnd: Integer; uIDEvent: Integer): Integer; external 'KillTimer@user32.dll stdcall';

var
  OldWndProc: Integer;
  TimerID: Integer;
  SlideFiles: array of String;
  SlideCount: Integer;
  SlideIndex: Integer;
  SlideIntervalMs: Integer;

procedure LoadNextSlide();
var
  tries, i: Integer;
begin
  if SlideCount = 0 then Exit;
  tries := GetArrayLength(SlideFiles);
  for i := 0 to tries - 1 do
  begin
    if FileExists(SlideFiles[SlideIndex]) then
    begin
      try
        WizardForm.WizardImage.Picture.LoadFromFile(SlideFiles[SlideIndex]);
      except
        // ignore load errors
      end;
      Inc(SlideIndex);
      if SlideIndex >= GetArrayLength(SlideFiles) then SlideIndex := 0;
      Exit;
    end
    else
    begin
      Inc(SlideIndex);
      if SlideIndex >= GetArrayLength(SlideFiles) then SlideIndex := 0;
    end;
  end;
end;

function WizardWndProc(hWnd, Msg, wParam, lParam: Integer): Integer; stdcall;
begin
  if Msg = WM_TIMER then
  begin
    // timer tick -> change slide
    LoadNextSlide();
  end;
  Result := CallWindowProc(OldWndProc, hWnd, Msg, wParam, lParam);
end;

procedure InitializeWizard();
var
  i: Integer;
begin
  // Intervalle en ms (3s par défaut) - tu peux le changer ici
  SlideIntervalMs := 3000;

  // Prépare tableau des slides (copiées dans {tmp} via [Files])
  SetArrayLength(SlideFiles, 5);
  SlideFiles[0] := ExpandConstant('{tmp}\gk1.bmp');
  SlideFiles[1] := ExpandConstant('{tmp}\gk2.bmp');
  SlideFiles[2] := ExpandConstant('{tmp}\gk3.bmp');
  SlideFiles[3] := ExpandConstant('{tmp}\gk4.bmp');
  SlideFiles[4] := ExpandConstant('{tmp}\gk5.bmp');

  SlideCount := 0;
  for i := 0 to GetArrayLength(SlideFiles)-1 do
    if FileExists(SlideFiles[i]) then Inc(SlideCount);

  SlideIndex := 0;

  // Subclass wizard window to intercept WM_TIMER
  try
    OldWndProc := SetWindowLongPtr(WizardForm.Handle, GWL_WNDPROC, Integer(@WizardWndProc));
    // Crée le timer
    TimerID := SetTimer(WizardForm.Handle, 1, SlideIntervalMs, 0);
  except
    // si l'API n'est pas disponible on ignore et on ne fait pas le slideshow
    OldWndProc := 0;
    TimerID := 0;
  end;

  // Charge immédiatement la première slide si elle existe
  if SlideCount > 0 then
    LoadNextSlide();
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  // Lorsque l'utilisateur navigue manuellement, on s'assure qu'une image est affichée
  if SlideCount > 0 then
    // (LoadNextSlide s'occupera de l'incrémentation par timer)
    WizardForm.WizardImage.Picture.LoadFromFile(SlideFiles[SlideIndex]);
end;

procedure DeinitializeSetup();
begin
  // Stop timer & restore wndproc proprement
  if TimerID <> 0 then KillTimer(WizardForm.Handle, TimerID);
  if OldWndProc <> 0 then
    SetWindowLongPtr(WizardForm.Handle, GWL_WNDPROC, OldWndProc);
end;

; -------------------------
; Fin du script
; -------------------------
