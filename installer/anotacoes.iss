; Instalador do programa (Inno Setup 6). Gerado pelo GitHub Actions: iscc /DAppVersao=2.12.0 installer\anotacoes.iss
; Instala só para o usuário atual (sem pedir administrador), cria os atalhos e um desinstalador.
; Os DADOS ficam em %LOCALAPPDATA%\AnotacoesHospitalares, fora desta pasta: atualizar,
; reinstalar ou desinstalar o programa não os apaga.
#ifndef AppVersao
  #define AppVersao "0.0.0"
#endif

[Setup]
AppId={{6E1F0B52-3C2D-4F8A-9B7E-5A4D8C2E7F31}
AppName=Anotações
AppVersion={#AppVersao}
AppPublisher=Anotações
DefaultDirName={localappdata}\Programs\Anotacoes
DefaultGroupName=Anotações
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=Anotacoes-Instalador
SetupIconFile=..\assets\icone.ico
UninstallDisplayIcon={app}\Anotacoes.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar um atalho na Área de Trabalho"; GroupDescription: "Atalhos:"

[Files]
Source: "..\dist\Anotacoes.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Anotações"; Filename: "{app}\Anotacoes.exe"
Name: "{autodesktop}\Anotações"; Filename: "{app}\Anotacoes.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Anotacoes.exe"; Description: "Abrir o programa agora"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Restos da atualização automática (a pasta de dados NÃO é tocada).
Type: files; Name: "{app}\Anotacoes.exe.anterior"
Type: files; Name: "{app}\AnotacoesHospitalares.novo.exe"
Type: files; Name: "{app}\atualizacao.log"
