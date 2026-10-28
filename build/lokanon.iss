; Lokanon – Inno Setup 6 Skript. Wird von build\build.py --installer aufgerufen:
;   ISCC.exe /DAppVersion=1.0.0 /DAppDir=C:\Users\david\Lokanon\build\app /DOutDir=C:\Users\david\Lokanon\build\out build\lokanon.iss
; Ohne Defines gelten die Standardwerte unten (Bundle unter %USERPROFILE%\Lokanon\build\app).

#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif
#ifndef AppDir
  #define AppDir GetEnv("USERPROFILE") + "\Lokanon\build\app"
#endif
#ifndef OutDir
  #define OutDir GetEnv("USERPROFILE") + "\Lokanon\build\out"
#endif

[Setup]
AppId={{7D2E4C1A-5B0F-4E8A-9C3D-2A1B3C4D5E6F}
AppName=Lokanon
AppVersion={#AppVersion}
AppVerName=Lokanon {#AppVersion}
AppPublisher=Lokanon
DefaultDirName={localappdata}\Programs\Lokanon
DefaultGroupName=Lokanon
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#OutDir}
OutputBaseFilename=Lokanon-Setup-{#AppVersion}
SetupIconFile={#AppDir}\assets\lokanon.ico
UninstallDisplayIcon={app}\assets\lokanon.ico
UninstallDisplayName=Lokanon
; LZMA2/ultra64 braucht bei 2,5 GB sehr lange und viel RAM; normal reicht (Modelle sind kaum komprimierbar)
Compression=lzma2/normal
SolidCompression=yes
LZMAUseSeparateProcess=yes
LZMANumBlockThreads=4
DiskSpanning=no
WizardStyle=modern
ShowLanguageDialog=no
CloseApplications=yes
RestartApplications=no
MinVersion=10.0

[Languages]
Name: "de"; MessagesFile: "compiler:Languages\German.isl"

[CustomMessages]
de.Hinweis=Hinweise vor der Installation
de.HinweisText=Lokanon wird nur für Ihr Benutzerkonto installiert (keine Administratorrechte nötig) und belegt etwa 2,5 GB.%n%nAlle Sprachmodelle sind enthalten. Lokanon arbeitet vollständig offline; es werden keine Daten ins Internet übertragen.%n%nIhre Vorgänge, Schlüssel und Einstellungen liegen unter %USERPROFILE%\Lokanon. Dieser Ordner bleibt bei einer Deinstallation erhalten.%n%nHinweis zu Windows SmartScreen: Da der Installer nicht mit einem Zertifikat signiert ist, kann Windows die Meldung „Der Computer wurde durch Windows geschützt“ anzeigen. Klicken Sie dann auf „Weitere Informationen“ und „Trotzdem ausführen“.
de.DesktopIcon=Verknüpfung auf dem Desktop anlegen

[Tasks]
Name: "desktopicon"; Description: "{cm:DesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#AppDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Lokanon"; Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\lokanon.py"""; WorkingDir: "{app}"; IconFilename: "{app}\assets\lokanon.ico"; Comment: "Lokanon – Dokumente lokal anonymisieren"
Name: "{group}\Lokanon deinstallieren"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Lokanon"; Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\lokanon.py"""; WorkingDir: "{app}"; IconFilename: "{app}\assets\lokanon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\lokanon.py"""; WorkingDir: "{app}"; Description: "Lokanon jetzt starten"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Nur Programmdateien; %USERPROFILE%\Lokanon (Vorgänge, Schlüssel, Einstellungen) wird NICHT angefasst
Type: filesandordirs; Name: "{app}\python"
Type: filesandordirs; Name: "{app}\models"
Type: filesandordirs; Name: "{app}\anonymizer"
Type: filesandordirs; Name: "{app}\server"
Type: filesandordirs; Name: "{app}\ui"

[Code]
procedure InitializeWizard;
var
  Seite: TOutputMsgWizardPage;
begin
  Seite := CreateOutputMsgPage(wpWelcome, CustomMessage('Hinweis'), 'Bitte lesen Sie diese Hinweise.',
    CustomMessage('HinweisText'));
end;
