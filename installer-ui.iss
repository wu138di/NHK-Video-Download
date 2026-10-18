var
  UILanguage: Integer;
  WelcomeSubtitle, WelcomeFooter: TNewStaticText;
  LanguageMenu: TPanel;
  LanguageIcon: TBitmapButton;
  LastGuideLanguage: Integer;
  GlassImage, LogoImage, InnerGlass: TBitmapImage;
  LayoutReady, FirstShow, CancelSignalled: Boolean;

function ShowWindow(hWnd: HWND; nCmdShow: Integer): Boolean;
  external 'ShowWindow@user32.dll stdcall';

function Bounded(Value, Minimum, Maximum: Integer): Integer;
begin
  Result := Value;
  if Result < Minimum then Result := Minimum;
  if Result > Maximum then Result := Maximum;
end;

procedure LayoutWizard();
var
  W, H, BodyH, CardW, CardH, X, Y, Padding, IconSize: Integer;
  ContentW, ContentH, NavY, ButtonW, ButtonH, TextSize: Integer;
  Measure: TBitmap;
begin
  if not LayoutReady then Exit;
  W := WizardForm.ClientWidth;
  H := WizardForm.ClientHeight;
  BodyH := H - ScaleY(88);
  WizardForm.OuterNotebook.SetBounds(0, 0, W, BodyH);
  WizardForm.Bevel.Visible := False;
  WizardForm.Bevel1.Visible := False;
  WizardForm.BeveledLabel.Visible := False;
  CardW := Bounded(W - ScaleX(112), ScaleX(500), ScaleX(760));
  CardH := Bounded(BodyH - ScaleY(64), ScaleY(286), ScaleY(440));
  X := (W - CardW) div 2;
  Y := (BodyH - CardH) div 2;
  GlassImage.SetBounds(X, Y, CardW, CardH);
  Padding := ScaleX(40);
  IconSize := Bounded(CardH div 7, ScaleX(44), ScaleX(60));
  LogoImage.SetBounds((W - IconSize) div 2, Y + CardH * 13 div 100, IconSize, IconSize);
  WizardForm.WelcomeLabel1.SetBounds(X + Padding, Y + CardH * 38 div 100,
    CardW - Padding * 2, CardH * 15 div 100);
  TextSize := 28;
  if CardH < ScaleY(360) then TextSize := 24;
  Measure := TBitmap.Create;
  try
    Measure.Canvas.Font.Assign(WizardForm.WelcomeLabel1.Font);
    Measure.Canvas.Font.Size := TextSize;
    while (TextSize > 16) and (Measure.Canvas.TextWidth(WizardForm.WelcomeLabel1.Caption) > CardW - Padding * 2) do begin
      TextSize := TextSize - 1;
      Measure.Canvas.Font.Size := TextSize;
    end;
    WizardForm.WelcomeLabel1.Font.Size := TextSize;
  finally
    Measure.Free;
  end;
  WelcomeSubtitle.SetBounds(X + Padding, Y + CardH * 55 div 100, CardW - Padding * 2, ScaleY(32));
  WelcomeFooter.SetBounds(X + Padding, Y + CardH * 80 div 100, CardW - Padding * 2, ScaleY(48));
  WelcomeSubtitle.Font.Size := 14;
  WelcomeFooter.Font.Size := 10;
  WelcomeFooter.WordWrap := True;
  WelcomeFooter.AdjustHeight;

  ButtonW := ScaleX(116);
  ButtonH := ScaleY(40);
  NavY := H - ScaleY(64);
  WizardForm.BackButton.SetBounds(ScaleX(32), NavY, ButtonW, ButtonH);
  WizardForm.CancelButton.SetBounds(W - ScaleX(32) - ButtonW, NavY, ButtonW, ButtonH);
  WizardForm.NextButton.SetBounds(W - ScaleX(48) - ButtonW * 2, NavY, ButtonW, ButtonH);
  WizardForm.BackButton.Font.Size := 11;
  WizardForm.NextButton.Font.Size := 11;
  WizardForm.CancelButton.Font.Size := 11;
  LanguageIcon.SetBounds(W - ScaleX(72), ScaleY(18), ScaleX(44), ScaleY(44));
  LanguageMenu.SetBounds(W - ScaleX(204), ScaleY(70), ScaleX(172), ScaleY(148));

  ContentW := Bounded(W - ScaleX(160), ScaleX(460), ScaleX(900));
  ContentH := BodyH - ScaleY(166);
  X := (W - ContentW) div 2;
  InnerGlass.SetBounds(X - ScaleX(28), ScaleY(20), ContentW + ScaleX(56), BodyH - ScaleY(32));
  WizardForm.MainPanel.SetBounds(X, ScaleY(40), ContentW, ScaleY(84));
  WizardForm.PageNameLabel.SetBounds(0, 0, ContentW - ScaleX(24), ScaleY(36));
  WizardForm.PageNameLabel.Font.Size := 20;
  WizardForm.PageDescriptionLabel.SetBounds(0, ScaleY(44), ContentW, ScaleY(32));
  WizardForm.PageDescriptionLabel.Font.Size := 10;
  WizardForm.InnerNotebook.SetBounds(X, ScaleY(132), ContentW, ContentH);
  WizardForm.InfoBeforeClickLabel.SetBounds(0, 0, ContentW, ScaleY(28));
  WizardForm.InfoBeforeMemo.SetBounds(0, ScaleY(36), ContentW, ContentH - ScaleY(36));
  WizardForm.InfoBeforeMemo.Font.Size := 11;
  WizardForm.SelectDirBitmapImage.Visible := False;
  WizardForm.SelectDirLabel.SetBounds(0, 0, ContentW, ScaleY(28));
  WizardForm.SelectDirBrowseLabel.SetBounds(0, ScaleY(40), ContentW, ScaleY(28));
  WizardForm.DirEdit.SetBounds(0, ScaleY(80), ContentW - ScaleX(140), ScaleY(36));
  WizardForm.DirBrowseButton.SetBounds(ContentW - ScaleX(124), ScaleY(80), ScaleX(124), ScaleY(36));
  WizardForm.DiskSpaceLabel.SetBounds(0, ScaleY(128), ContentW, ScaleY(40));
  WizardForm.SelectTasksLabel.SetBounds(0, 0, ContentW, ScaleY(36));
  WizardForm.TasksList.SetBounds(0, ScaleY(48), ContentW, ContentH - ScaleY(48));
  WizardForm.ReadyLabel.SetBounds(0, 0, ContentW, ScaleY(44));
  WizardForm.ReadyMemo.SetBounds(0, ScaleY(56), ContentW, ContentH - ScaleY(56));
  WizardForm.StatusLabel.SetBounds(0, ScaleY(24), ContentW, ScaleY(32));
  WizardForm.FilenameLabel.SetBounds(0, ScaleY(68), ContentW, ScaleY(40));
  WizardForm.ProgressGauge.SetBounds(0, ScaleY(124), ContentW, ScaleY(18));
  WizardForm.FinishedHeadingLabel.SetBounds((W - ContentW) div 2, BodyH div 4, ContentW, ScaleY(44));
  WizardForm.FinishedHeadingLabel.Alignment := taCenter;
  WizardForm.FinishedHeadingLabel.Font.Size := 24;
  WizardForm.FinishedLabel.SetBounds((W - ContentW) div 2, BodyH div 4 + ScaleY(64), ContentW, ScaleY(48));
  WizardForm.FinishedLabel.Alignment := taCenter;
  WizardForm.RunList.SetBounds((W - ContentW) div 2, BodyH div 4 + ScaleY(128), ContentW, ScaleY(80));
  LanguageIcon.BringToFront;
  LanguageMenu.BringToFront;
  Log(Format('LAYOUT client=%dx%d; welcome=%d,%d,%d,%d; content=%dx%d; font=%d; lang=%d', [W, H, GlassImage.Left, GlassImage.Top, CardW, CardH, ContentW, ContentH, TextSize, UILanguage]));
end;

procedure WizardResized(Sender: TObject);
begin
  LayoutWizard();
end;

procedure WizardShown(Sender: TObject);
begin
  if not FirstShow then begin
    FirstShow := True;
    if not WizardSilent then ShowWindow(WizardForm.Handle, 3);
  end;
  LayoutWizard();
end;

function L(const Chinese, English, Japanese: String): String;
begin
  if UILanguage = 1 then Result := English
  else if UILanguage = 2 then Result := Japanese
  else Result := Chinese;
end;

function IsAppLanguage(LanguageCode: String): Boolean;
begin
  if ActiveLanguage = 'english' then Result := LanguageCode = 'en'
  else if ActiveLanguage = 'japanese' then Result := LanguageCode = 'ja'
  else Result := LanguageCode = 'zh';
end;

function GetAppShortcut(Param: String): String;
begin
  Result := L('NHK 下载器 V2.0', 'NHK Downloader V2.0', 'NHK ダウンローダー V2.0');
end;

function GetCliShortcut(Param: String): String;
begin
  Result := L('NHK 命令行', 'NHK Command Line', 'NHK コマンドライン');
end;

function GetGuideShortcut(Param: String): String;
begin
  Result := L('安装与使用说明', 'Installation and User Guide', 'インストールと使い方');
end;

function GetGuideFilename(Param: String): String;
begin
  Result := L('使用说明.txt', 'UserGuide.en.txt', '使い方.ja.txt');
end;

function GetUninstallShortcut(Param: String): String;
begin
  Result := L('卸载 NHK 下载器', 'Uninstall NHK Downloader', 'NHK ダウンローダーをアンインストール');
end;

function GetLaunchCaption(Param: String): String;
begin
  Result := L('启动 NHK 下载器', 'Launch NHK Downloader', 'NHK ダウンローダーを起動');
end;

procedure ApplyLanguage();
var
  PageName, PageDescription, FontName: String;
begin
  FontName := L('Microsoft YaHei UI', 'Segoe UI', 'Yu Gothic UI');
  WizardForm.Caption := L('安装 - NHK 下载器 V2.0', 'Setup - NHK Downloader V2.0', 'NHK ダウンローダー V2.0 セットアップ');
  WizardForm.WelcomeLabel1.Caption := L('NHK 下载器 V2.0', 'NHK Downloader V2.0', 'NHK ダウンローダー V2.0');
  WizardForm.WelcomeLabel1.Font.Name := FontName;
  WelcomeSubtitle.Caption := L('安装向导', 'Setup', 'セットアップ');
  WelcomeSubtitle.Font.Name := FontName;
  WelcomeFooter.Caption := L('由 wu138di 制作', 'Made by wu138di', '制作：wu138di') + #13#10 +
    L('请勿用于非法用途', 'Do not use for illegal purposes.', '違法な用途に使用しないでください。');
  WelcomeFooter.Font.Name := FontName;
  WizardForm.WelcomeLabel2.Visible := False;
  WizardForm.BackButton.Caption := L('上一步', 'Back', '戻る');
  WizardForm.NextButton.Caption := L('下一步', 'Next', '次へ');
  WizardForm.CancelButton.Caption := L('取消', 'Cancel', 'キャンセル');
  WizardForm.DirBrowseButton.Caption := L('浏览…', 'Browse…', '参照…');
  WizardForm.GroupBrowseButton.Caption := L('浏览…', 'Browse…', '参照…');
  WizardForm.InfoBeforeClickLabel.Caption := L('阅读后点击“下一步”继续。', 'Click Next to continue after reading.', '内容を確認して「次へ」をクリックしてください。');
  WizardForm.SelectDirLabel.Caption := L('选择程序的安装位置。', 'Choose where to install the application.', 'アプリのインストール先を選択してください。');
  WizardForm.SelectDirBrowseLabel.Caption := L('如需更改位置，请点击“浏览”。', 'Click Browse to choose another folder.', '保存先を変更する場合は「参照」をクリックしてください。');
  WizardForm.DiskSpaceLabel.Caption := L('安装程序将自动检查可用磁盘空间。', 'Available disk space is checked automatically.', '空き容量はインストーラーが自動的に確認します。');
  WizardForm.SelectTasksLabel.Caption := L('选择需要创建的快捷方式。', 'Choose additional shortcuts.', '作成するショートカットを選択してください。');
  WizardForm.ReadyLabel.Caption := L('确认安装位置，然后点击“安装”。', 'Review the destination, then click Install.', 'インストール先を確認し、「インストール」をクリックしてください。');
  if WizardForm.TasksList.Items.Count > 0 then
    WizardForm.TasksList.ItemCaption[0] := L('快捷方式', 'Shortcuts', 'ショートカット');
  if WizardForm.TasksList.Items.Count > 1 then
    WizardForm.TasksList.ItemCaption[1] := L('创建桌面快捷方式', 'Create a desktop shortcut', 'デスクトップにショートカットを作成');
  if WizardForm.RunList.Items.Count > 0 then
    WizardForm.RunList.ItemCaption[0] := L('启动 NHK 下载器', 'Launch NHK Downloader', 'NHK ダウンローダーを起動');
  PageName := '';
  PageDescription := '';
  case WizardForm.CurPageID of
    wpInfoBefore:
      begin
        PageName := L('使用说明', 'User guide', '使い方');
        PageDescription := L('NHK 下载器 V2.0 安装与使用说明', 'NHK Downloader V2.0 installation and user guide', 'NHK ダウンローダー V2.0 のインストールと使い方');
      end;
    wpSelectDir:
      begin
        PageName := L('安装位置', 'Installation folder', 'インストール先');
        PageDescription := L('选择文件夹，或保留默认位置。', 'Choose a folder or keep the default.', 'フォルダーを選ぶか、既定の場所を使用します。');
      end;
    wpSelectTasks:
      begin
        PageName := L('快捷方式', 'Shortcuts', 'ショートカット');
        PageDescription := L('按需选择，不影响程序功能。', 'Optional shortcuts for quick access.', '必要に応じて選択してください。');
      end;
    wpReady:
      begin
        PageName := L('准备安装', 'Ready to install', 'インストールの準備完了');
        PageDescription := L('即将安装图形界面、命令行与内置组件。', 'GUI, command line, and bundled components.', 'GUI、コマンドライン、内蔵コンポーネントをインストールします。');
        WizardForm.NextButton.Caption := L('安装', 'Install', 'インストール');
        WizardForm.ReadyMemo.Lines.Text := L('安装位置：', 'Destination:', 'インストール先：') + #13#10 + WizardForm.DirEdit.Text;
      end;
    wpPreparing:
      begin
        PageName := L('正在准备', 'Preparing', '準備中');
        PageDescription := L('正在检查安装环境。', 'Checking the installation environment.', 'インストール環境を確認しています。');
      end;
    wpInstalling:
      begin
        PageName := L('正在安装', 'Installing', 'インストール中');
        PageDescription := L('正在安装所需文件，请稍候。', 'Installing application files. Please wait.', '必要なファイルをインストールしています。');
        WizardForm.StatusLabel.Caption := L('正在安装…', 'Installing…', 'インストール中…');
      end;
    wpFinished:
      begin
        WizardForm.FinishedHeadingLabel.Caption := L('安装完成', 'Installation complete', 'インストール完了');
        WizardForm.FinishedLabel.Caption := L('NHK 下载器已安装完成。', 'NHK Downloader has been installed.', 'NHK ダウンローダーのインストールが完了しました。');
        WizardForm.NextButton.Caption := L('完成', 'Finish', '完了');
      end;
  end;
  if PageName <> '' then WizardForm.PageNameLabel.Caption := PageName;
  if PageDescription <> '' then WizardForm.PageDescriptionLabel.Caption := PageDescription;
  WizardForm.PageNameLabel.Font.Name := FontName;
  WizardForm.PageDescriptionLabel.Font.Name := FontName;
  WizardForm.InfoBeforeClickLabel.Font.Name := FontName;
  WizardForm.InfoBeforeMemo.Font.Name := FontName;
  if LastGuideLanguage <> UILanguage then begin
    WizardForm.InfoBeforeMemo.Lines.LoadFromFile(ExpandConstant('{tmp}\') + L('guide-zh.txt', 'guide-en.txt', 'guide-ja.txt'));
    LastGuideLanguage := UILanguage;
  end;
  LanguageIcon.BringToFront;
  LayoutWizard();
end;

#ifdef LAYOUTTEST
procedure RequireInside(Control: TControl; W, H: Integer; Name: String);
begin
  if (Control.Left < 0) or (Control.Top < 0) or
    (Control.Left + Control.Width > W) or (Control.Top + Control.Height > H) then
    RaiseException('LAYOUT TEST FAILED: ' + Name);
end;

procedure TestLayoutSize(W, H: Integer);
var
  Lang: Integer;
  Measure: TBitmap;
  SavedDirectory: String;
begin
  WizardForm.ClientWidth := W;
  WizardForm.ClientHeight := H;
  SavedDirectory := 'D:\NHK Layout Test\custom-output';
  WizardForm.DirEdit.Text := SavedDirectory;
  for Lang := 0 to 2 do begin
    UILanguage := Lang;
    ApplyLanguage();
    RequireInside(GlassImage, WizardForm.WelcomePage.ClientWidth, WizardForm.WelcomePage.ClientHeight, 'card');
    RequireInside(WizardForm.WelcomeLabel1, WizardForm.WelcomePage.ClientWidth, WizardForm.WelcomePage.ClientHeight, 'title');
    RequireInside(WelcomeFooter, WizardForm.WelcomePage.ClientWidth, WizardForm.WelcomePage.ClientHeight, 'footer');
    RequireInside(WizardForm.NextButton, WizardForm.ClientWidth, WizardForm.ClientHeight, 'next');
    RequireInside(WizardForm.CancelButton, WizardForm.ClientWidth, WizardForm.ClientHeight, 'cancel');
    RequireInside(LanguageIcon, WizardForm.ClientWidth, WizardForm.ClientHeight, 'globe');
    RequireInside(WizardForm.InfoBeforeMemo, WizardForm.InfoBeforePage.ClientWidth, WizardForm.InfoBeforePage.ClientHeight, 'guide');
    RequireInside(WizardForm.DirEdit, WizardForm.SelectDirPage.ClientWidth, WizardForm.SelectDirPage.ClientHeight, 'directory');
    RequireInside(WizardForm.DiskSpaceLabel, WizardForm.SelectDirPage.ClientWidth, WizardForm.SelectDirPage.ClientHeight, 'disk-space');
    RequireInside(WizardForm.ReadyMemo, WizardForm.ReadyPage.ClientWidth, WizardForm.ReadyPage.ClientHeight, 'ready');
    Measure := TBitmap.Create;
    try
      Measure.Canvas.Font.Assign(WizardForm.WelcomeLabel1.Font);
      if Measure.Canvas.TextWidth(WizardForm.WelcomeLabel1.Caption) > WizardForm.WelcomeLabel1.Width then
        RaiseException('LAYOUT TEST FAILED: title text exceeds width');
    finally
      Measure.Free;
    end;
    if WizardForm.DirEdit.Text <> SavedDirectory then RaiseException('Directory changed during language switch');
    Log(Format('LAYOUT_TEST_PASS size=%dx%d language=%d; title-fits; controls-inside; directory-preserved', [WizardForm.ClientWidth, WizardForm.ClientHeight, Lang]));
  end;
end;
#endif

procedure BrowseDirectory(Sender: TObject);
var
  Directory: String;
begin
  Directory := WizardForm.DirEdit.Text;
  if BrowseForFolder(L('选择安装文件夹', 'Choose installation folder', 'インストール先を選択'), Directory, True) then
    WizardForm.DirEdit.Text := Directory;
end;

procedure SelectChinese(Sender: TObject);
begin
  UILanguage := 0;
  LastGuideLanguage := -1;
  LanguageMenu.Visible := False;
  ApplyLanguage();
end;

procedure SelectEnglish(Sender: TObject);
begin
  UILanguage := 1;
  LanguageMenu.Visible := False;
  ApplyLanguage();
end;

procedure SelectJapanese(Sender: TObject);
begin
  UILanguage := 2;
  LanguageMenu.Visible := False;
  ApplyLanguage();
end;

procedure ToggleLanguages(Sender: TObject);
begin
  LanguageMenu.Visible := not LanguageMenu.Visible;
  if LanguageMenu.Visible then LanguageMenu.BringToFront;
end;

procedure InitializeWizard();
var
  MenuButton: TNewButton;
  CardLeft, CardTop, CardWidth: Integer;
begin
  UILanguage := 0;
  if ActiveLanguage = 'english' then UILanguage := 1;
  if ActiveLanguage = 'japanese' then UILanguage := 2;
  CardWidth := ScaleX(420);
  CardLeft := (WizardForm.WelcomePage.ClientWidth - CardWidth) div 2;
  CardTop := ScaleY(20);
  ExtractTemporaryFile('installer-glass.png');
  ExtractTemporaryFile('app-icon.ico');
  ExtractTemporaryFile('language.png');
  ExtractTemporaryFile('guide-zh.txt');
  ExtractTemporaryFile('guide-en.txt');
  ExtractTemporaryFile('guide-ja.txt');
  WizardForm.DirBrowseButton.OnClick := @BrowseDirectory;
  GlassImage := TBitmapImage.Create(WizardForm);
  GlassImage.Parent := WizardForm.WelcomePage;
  GlassImage.Left := CardLeft;
  GlassImage.Top := CardTop;
  GlassImage.Width := CardWidth;
  GlassImage.Height := ScaleY(310);
  GlassImage.Stretch := True;
  GlassImage.BackColor := clNone;
  GlassImage.PngImage.LoadFromFile(ExpandConstant('{tmp}\installer-glass.png'));
  InnerGlass := TBitmapImage.Create(WizardForm);
  InnerGlass.Parent := WizardForm.InnerPage;
  InnerGlass.Stretch := True;
  InnerGlass.BackColor := clNone;
  InnerGlass.PngImage.LoadFromFile(ExpandConstant('{tmp}\installer-glass.png'));
  InnerGlass.SendToBack;
  WizardForm.MainPanel.Align := alNone;
  WizardForm.InnerNotebook.Align := alNone;
  LogoImage := TBitmapImage.Create(WizardForm);
  LogoImage.Parent := WizardForm.WelcomePage;
  LogoImage.Left := CardLeft + (CardWidth - ScaleX(48)) div 2;
  LogoImage.Top := CardTop + ScaleY(34);
  LogoImage.Width := ScaleX(48);
  LogoImage.Height := ScaleY(48);
  LogoImage.Stretch := True;
  LogoImage.BackColor := clNone;
  InitializeBitmapImageFromIcon(LogoImage, ExpandConstant('{tmp}\app-icon.ico'), clNone, [48, 64, 96]);
  WizardForm.WelcomeLabel1.Parent := WizardForm.WelcomePage;
  WizardForm.WelcomeLabel1.Left := CardLeft + ScaleX(24);
  WizardForm.WelcomeLabel1.Top := CardTop + ScaleY(100);
  WizardForm.WelcomeLabel1.Width := CardWidth - ScaleX(48);
  WizardForm.WelcomeLabel1.Height := ScaleY(42);
  WizardForm.WelcomeLabel1.Alignment := taCenter;
  WizardForm.WelcomeLabel1.AutoSize := False;
  WizardForm.WelcomeLabel1.WordWrap := False;
  WizardForm.WelcomeLabel1.Font.Color := $002F2530;
  WelcomeSubtitle := TNewStaticText.Create(WizardForm);
  WelcomeSubtitle.Parent := WizardForm.WelcomePage;
  WelcomeSubtitle.Left := CardLeft + ScaleX(24);
  WelcomeSubtitle.Top := CardTop + ScaleY(155);
  WelcomeSubtitle.Width := CardWidth - ScaleX(48);
  WelcomeSubtitle.Height := ScaleY(25);
  WelcomeSubtitle.AutoSize := False;
  WelcomeSubtitle.Alignment := taCenter;
  WelcomeSubtitle.Font.Size := 13;
  WelcomeSubtitle.Font.Color := $006A5D6A;
  WizardForm.WelcomeLabel2.Visible := False;
  WelcomeFooter := TNewStaticText.Create(WizardForm);
  WelcomeFooter.Parent := WizardForm.WelcomePage;
  WelcomeFooter.Left := CardLeft + ScaleX(24);
  WelcomeFooter.Top := CardTop + ScaleY(242);
  WelcomeFooter.Width := CardWidth - ScaleX(48);
  WelcomeFooter.Height := ScaleY(44);
  WelcomeFooter.AutoSize := False;
  WelcomeFooter.Alignment := taCenter;
  WelcomeFooter.Font.Size := 9;
  WelcomeFooter.Font.Color := $00857887;
  LanguageIcon := TBitmapButton.Create(WizardForm);
  LanguageIcon.Parent := WizardForm;
  LanguageIcon.Left := WizardForm.ClientWidth - ScaleX(44);
  LanguageIcon.Top := ScaleY(12);
  LanguageIcon.Width := ScaleX(26);
  LanguageIcon.Height := ScaleY(26);
  LanguageIcon.Anchors := [akTop, akRight];
  LanguageIcon.BackColor := clNone;
  LanguageIcon.Stretch := True;
  LanguageIcon.PngImage.LoadFromFile(ExpandConstant('{tmp}\language.png'));
  LanguageIcon.Cursor := crHandPoint;
  LanguageIcon.TabStop := False;
  LanguageIcon.OnClick := @ToggleLanguages;
  LanguageMenu := TPanel.Create(WizardForm);
  LanguageMenu.Parent := WizardForm;
  LanguageMenu.Left := WizardForm.ClientWidth - ScaleX(158);
  LanguageMenu.Top := ScaleY(44);
  LanguageMenu.Width := ScaleX(140);
  LanguageMenu.Height := ScaleY(122);
  LanguageMenu.Anchors := [akTop, akRight];
  LanguageMenu.BevelOuter := bvNone;
  LanguageMenu.Color := clWhite;
  MenuButton := TNewButton.Create(WizardForm);
  MenuButton.Parent := LanguageMenu;
  MenuButton.SetBounds(ScaleX(8), ScaleY(8), ScaleX(156), ScaleY(40));
  MenuButton.Caption := '简体中文';
  MenuButton.OnClick := @SelectChinese;
  MenuButton := TNewButton.Create(WizardForm);
  MenuButton.Parent := LanguageMenu;
  MenuButton.SetBounds(ScaleX(8), ScaleY(54), ScaleX(156), ScaleY(40));
  MenuButton.Caption := 'English';
  MenuButton.OnClick := @SelectEnglish;
  MenuButton := TNewButton.Create(WizardForm);
  MenuButton.Parent := LanguageMenu;
  MenuButton.SetBounds(ScaleX(8), ScaleY(100), ScaleX(156), ScaleY(40));
  MenuButton.Caption := '日本語';
  MenuButton.OnClick := @SelectJapanese;
  LanguageMenu.Visible := False;
  WizardForm.BorderStyle := bsSizeable;
  WizardForm.BorderIcons := [biSystemMenu, biMinimize, biMaximize];
  WizardForm.Constraints.MaxWidth := 0;
  WizardForm.Constraints.MaxHeight := 0;
  WizardForm.Constraints.MinWidth := ScaleX(680);
  WizardForm.Constraints.MinHeight := ScaleY(460);
  WizardForm.ClientWidth := ScaleX(960);
  WizardForm.ClientHeight := ScaleY(620);
  WizardForm.OnResize := @WizardResized;
  WizardForm.OnShow := @WizardShown;
  LayoutReady := True;
  ApplyLanguage();
#ifdef LAYOUTTEST
  TestLayoutSize(ScaleX(680), ScaleY(460));
  TestLayoutSize(ScaleX(960), ScaleY(620));
  TestLayoutSize(2560, 1566);
  Log('LAYOUT_TEST_ALL_PASS 3 sizes x 3 languages');
  Abort;
#endif
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  LanguageMenu.Visible := False;
  ApplyLanguage();
end;

procedure CurInstallProgressChanged(CurProgress, MaxProgress: Integer);
begin
  LanguageIcon.Enabled := True;
  WizardForm.StatusLabel.Caption := L('正在安装…', 'Installing…', 'インストール中…');
  if (not CancelSignalled) and (ExpandConstant('{param:CANCELFILE|}') <> '') then
    if FileExists(ExpandConstant('{param:CANCELFILE|}')) then begin
      CancelSignalled := True;
      { Inno's normal cancellation path requires a visible wizard, including
        in very-silent mode. Keep it off-screen and request normal rollback. }
      WizardForm.CenterOnShow := False;
      WizardForm.Left := -32000;
      WizardForm.Top := -32000;
      WizardForm.CancelButton.Enabled := True;
      WizardForm.Show;
      WizardForm.Close;
      WizardForm.Hide;
    end;
end;

procedure CancelButtonClick(CurPageID: Integer; var Cancel, Confirm: Boolean);
begin
  Confirm := False;
  if CurPageID = wpInstalling then
    if WizardSilent then Cancel := True
    else Cancel := MsgBox(L('要停止安装吗？', 'Stop the installation?', 'インストールを中止しますか？'), mbConfirmation, MB_YESNO) = IDYES;
end;

{ Remove legacy root notices only after a successful installation. }
procedure RemoveLegacyNotice(RelativePath, NewName, ExpectedHash: String);
var OldFile, NewFile: String;
begin
  OldFile := ExpandConstant('{app}\') + RelativePath;
  NewFile := ExpandConstant('{app}\_internal\Additional Tools\') + NewName;
  if FileExists(OldFile) and FileExists(NewFile) then begin
    if CompareText(GetSHA256OfFile(OldFile), ExpectedHash) = 0 then begin
      if DeleteFile(OldFile) then Log('Removed legacy notice: ' + RelativePath)
      else Log('Legacy notice retained: ' + RelativePath);
    end else Log('User-modified notice preserved: ' + RelativePath);
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssDone then begin
    RemoveLegacyNotice('licenses\FFmpeg-GPL.txt', 'License-03.txt', '8ceb4b9ee5adedde47b31e975c1d90c73ad27b6b165a1dcd80c7c545eb65b903');
    RemoveLegacyNotice('licenses\N_m3u8DL-RE-LICENSE.txt', 'License-01.txt', '99c39a1a78cd3d844f336576c18645e7334d2d5034713e961973591149536081');
    RemoveLegacyNotice('licenses\Shaka-Packager-LICENSE.txt', 'License-02.txt', '0eea5a66a8505f758fdc8710637c5b4f5f1b18b29d0f248d6e95a3cdfc8fb599');
    RemoveLegacyNotice('third-party-notices.txt', 'Notices.txt', '067486f2330d33eb4696a6bcf61cbfc9924afc88d026754587ff69016048a364');
    RemoveLegacyNotice('组件说明.txt', 'Information.txt', 'd0f729a31a681abefb307f4b82b58eb1dcddcc8a3e49d18446e3d977180c3c29');
    RemoveDir(ExpandConstant('{app}\licenses'));
  end;
end;
