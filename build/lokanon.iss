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
de.HinweisText=Lokanon wird nur für Ihr Benutzerkonto installiert (keine Administratorrechte nötig) und belegt etwa 2,5 GB.%n%nAlle Sprachmodelle sind enthalten. Lokanon arbeitet vollständig offline; es werden keine Daten ins Internet übertragen.%n%nIhre Einstellungen (und, wenn eingeschaltet, Schlüssel und Vorgänge) liegen unter %USERPROFILE%\Lokanon. Dieser Ordner bleibt bei einer Deinstallation erhalten.%n%nHinweis zu Windows SmartScreen: Da der Installer nicht mit einem Zertifikat signiert ist, kann Windows die Meldung „Der Computer wurde durch Windows geschützt“ anzeigen. Klicken Sie dann auf „Weitere Informationen“ und „Trotzdem ausführen“.
de.DesktopIcon=Verknüpfung auf dem Desktop anlegen
de.Vorstellung=Lokanon kennenlernen
de.VorstellungUnter=Während der Installation: die Produktvorstellung und der Film.
de.VorstellungText=Lokanon ersetzt in Mandatsunterlagen alles, was eine Person erkennbar macht, durch Platzhalter – lokal auf diesem PC. Dateien oder einen Ordner ablegen, prüfen, fertig: Zu jeder Datei entsteht eine Kopie im gleichen Format mit dem Zusatz „_anonymisiert“.%n%nSchauen Sie sich die Produktvorstellung oder den Film an, während Lokanon installiert wird. Beides finden Sie später auch im Startmenü und in Lokanon unter Einstellungen → „Lokanon vorstellen“.
de.VorstellungDeck=Produktvorstellung öffnen
de.VorstellungFilm=Film ansehen (2 Min.)
de.VorstellungNachher=Produktvorstellung ansehen

[Tasks]
Name: "desktopicon"; Description: "{cm:DesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Produktvorstellung für die Assistentenseite „Lokanon kennenlernen“ (nur temporär, zuerst im Archiv, damit sie sofort entpackt)
Source: "{#AppDir}\docs\marketing\lokanon-visitenkarte.html"; DestDir: "{tmp}\vorstellung"; Flags: dontcopy
Source: "{#AppDir}\docs\marketing\shots\*"; DestDir: "{tmp}\vorstellung\shots"; Flags: dontcopy
Source: "{#AppDir}\docs\marketing\filme\lokanon-visitenkarte.mp4"; DestDir: "{tmp}\vorstellung"; Flags: dontcopy
Source: "{#AppDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Lokanon"; Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\lokanon.py"""; WorkingDir: "{app}"; IconFilename: "{app}\assets\lokanon.ico"; Comment: "Lokanon – Dokumente lokal anonymisieren"
Name: "{group}\Lokanon – Produktvorstellung"; Filename: "{app}\docs\marketing\lokanon-visitenkarte.html"; Comment: "Lokanon in drei Akten, im Browser, ohne Internet"
Name: "{group}\Lokanon – Film (2 Min.)"; Filename: "{app}\docs\marketing\filme\lokanon-visitenkarte.mp4"; Comment: "Lokanon in zwei Minuten"
Name: "{group}\Lokanon – Filme und Vorstellung"; Filename: "{app}\docs\marketing"; Comment: "Ordner mit Produktvorstellung und Filmen"
Name: "{group}\Lokanon deinstallieren"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Lokanon"; Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\lokanon.py"""; WorkingDir: "{app}"; IconFilename: "{app}\assets\lokanon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\lokanon.py"""; WorkingDir: "{app}"; Description: "Lokanon jetzt starten"; Flags: nowait postinstall skipifsilent
Filename: "{app}\docs\marketing\lokanon-visitenkarte.html"; Description: "{cm:VorstellungNachher}"; Flags: shellexec nowait postinstall skipifsilent

[UninstallDelete]
; Nur Programmdateien; %USERPROFILE%\Lokanon (Vorgänge, Schlüssel, Einstellungen) wird NICHT angefasst
Type: filesandordirs; Name: "{app}\python"
Type: filesandordirs; Name: "{app}\models"
Type: filesandordirs; Name: "{app}\anonymizer"
Type: filesandordirs; Name: "{app}\server"
Type: filesandordirs; Name: "{app}\ui"

[Code]
var
  VorstellungEntpackt: Boolean;

procedure VorstellungEntpacken;
begin
  if not VorstellungEntpackt then
  begin
    ExtractTemporaryFiles('{tmp}\vorstellung\*');
    ExtractTemporaryFiles('{tmp}\vorstellung\shots\*');
    VorstellungEntpackt := True;
  end;
end;

procedure VorstellungOeffnen(Datei: String);
var
  Fehler: Integer;
begin
  try
    VorstellungEntpacken;
    if not ShellExec('open', ExpandConstant('{tmp}\vorstellung\' + Datei), '', '', SW_SHOWNORMAL, ewNoWait, Fehler) then
      MsgBox('Die Datei konnte nicht geöffnet werden. Sie finden sie nach der Installation im Startmenü.', mbInformation, MB_OK);
  except
    MsgBox('Die Produktvorstellung ist nach der Installation im Startmenü verfügbar.', mbInformation, MB_OK);
  end;
end;

procedure DeckKlick(Sender: TObject);
begin
  VorstellungOeffnen('lokanon-visitenkarte.html');
end;

procedure FilmKlick(Sender: TObject);
begin
  VorstellungOeffnen('lokanon-visitenkarte.mp4');
end;

procedure InitializeWizard;
var
  Seite: TOutputMsgWizardPage;
  Kennen: TWizardPage;
  Text: TNewStaticText;
  Deck, Film: TNewButton;
begin
  Seite := CreateOutputMsgPage(wpWelcome, CustomMessage('Hinweis'), 'Bitte lesen Sie diese Hinweise.',
    CustomMessage('HinweisText'));

  Kennen := CreateCustomPage(Seite.ID, CustomMessage('Vorstellung'), CustomMessage('VorstellungUnter'));
  Text := TNewStaticText.Create(Kennen);
  Text.Parent := Kennen.Surface;
  Text.AutoSize := False;
  Text.WordWrap := True;
  Text.Width := Kennen.SurfaceWidth;
  Text.Height := ScaleY(130);
  Text.Caption := CustomMessage('VorstellungText');

  Deck := TNewButton.Create(Kennen);
  Deck.Parent := Kennen.Surface;
  Deck.Caption := CustomMessage('VorstellungDeck');
  Deck.Top := Text.Top + Text.Height + ScaleY(12);
  Deck.Width := ScaleX(190);
  Deck.Height := ScaleY(30);
  Deck.OnClick := @DeckKlick;

  Film := TNewButton.Create(Kennen);
  Film.Parent := Kennen.Surface;
  Film.Caption := CustomMessage('VorstellungFilm');
  Film.Top := Deck.Top;
  Film.Left := Deck.Left + Deck.Width + ScaleX(12);
  Film.Width := ScaleX(190);
  Film.Height := ScaleY(30);
  Film.OnClick := @FilmKlick;
end;
