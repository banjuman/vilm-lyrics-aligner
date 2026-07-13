using Avalonia;
using Avalonia.Controls;
using Avalonia.Layout;
using Avalonia.Media;

namespace VilmLyricsAligner.Desktop;

public sealed class HelpWindow : Window
{
    private const string Cream = "#F2E9D2";
    private const string Card = "#FAF8F2";
    private const string BorderColor = "#C4B69C";
    private const string Green = "#043D20";
    private const string TextColor = "#1A1A1A";
    private const string Dim = "#7A6B55";

    public HelpWindow(string language)
    {
        bool korean = language == "ko";
        Title = korean ? "도움말 · Vilm Lyrics Aligner" : "Help · Vilm Lyrics Aligner";
        Width = 550;
        Height = 620;
        MinWidth = 480;
        MinHeight = 500;
        WindowStartupLocation = WindowStartupLocation.CenterOwner;
        Background = Brush.Parse(Cream);
        FontFamily = new FontFamily("Segoe UI");
        FontSize = 11;

        StackPanel guide = new() { Spacing = 8, HorizontalAlignment = HorizontalAlignment.Stretch };
        guide.Children.Add(Section(
            korean ? "1. 빠른 시작" : "1. Quick start",
            ItemList(
                numbered: true,
                korean
                    ? [
                        "편집본과 타이밍이 같은 영상 또는 음원을 선택합니다.",
                        "전체 가사를 붙여 넣거나 TXT 파일로 불러옵니다.",
                        "전체 파일을 사용하거나 파형에서 필요한 구간을 드래그합니다.",
                        "처음에는 자동 모드를 그대로 두고 SRT 생성을 누릅니다.",
                    ]
                    : [
                        "Choose video or audio with the same timing as your edit.",
                        "Paste the complete lyrics or load a TXT file.",
                        "Use the full file or drag the needed range on the waveform.",
                        "Start with Auto mode, then choose Generate SRT.",
                    ])));

        guide.Children.Add(Section(
            korean ? "2. 자동 모드와 수동(고급) 모드" : "2. Auto and Manual modes",
            Paragraphs(
                korean
                    ? [
                        "자동 모드는 대부분의 곡에 권장됩니다. 줄바꿈을 힌트로 사용하되, 지나치게 긴 줄은 알맞게 나눌 수 있습니다.",
                        "수동(고급) 모드는 비어 있지 않은 가사 한 줄을 자막 하나의 기본 단위로 사용합니다. 최대 글자 수를 넘는 줄만 추가로 나뉩니다.",
                        "최대 표시는 한 자막이 너무 오래 남지 않게 하고, 끝 여운은 노래가 끝난 뒤 자막을 유지하는 시간을 정합니다.",
                    ]
                    : [
                        "Auto mode is recommended for most songs. It treats line breaks as hints and may split an unusually long line.",
                        "Manual (advanced) treats each non-empty lyric line as one intended cue. Only a line over Max characters is split again.",
                        "Max seconds prevents a cue from staying too long. End hold controls how long it remains after the sung phrase.",
                    ])));

        guide.Children.Add(Section(
            korean ? "3. 허밍을 따로 알려주기" : "3. Marking a hum",
            Paragraphs(
                korean
                    ? [
                        "수동 모드에서 화면에 보이지 않을 허밍을 별도 괄호 줄로 적을 수 있습니다.",
                        "예: 첫 가사 / (음) / 다음 가사",
                        "괄호 줄은 정렬 공간만 확보하고 자막에는 표시되지 않습니다.",
                    ]
                    : [
                        "In Manual mode, put a non-displayed hum on its own parenthesized line.",
                        "Example: first lyric / (hmm) / next lyric",
                        "The parenthesized line reserves alignment time but is not shown as a subtitle.",
                    ])));

        StackPanel nle = new() { Spacing = 7 };
        nle.Children.Add(BodyText(korean
            ? "DaVinci Resolve 또는 Premiere에서 SRT를 가져온 뒤 자막 또는 캡션 트랙에 놓습니다."
            : "Import the SRT in DaVinci Resolve or Premiere, then place it on a subtitle or caption track."));
        nle.Children.Add(ItemList(
            numbered: false,
            korean
                ? [
                    "전체 타임라인 참고 파일을 사용했다면 타임라인 시작점에 놓습니다.",
                    "독립된 클립을 사용했다면 그 클립의 시작점에 놓습니다.",
                    "선택 구간의 시간은 선택한 미디어 안의 원래 위치를 유지합니다.",
                    "맨 앞의 아주 짧은 빈 자막은 위치 기준점입니다. 정렬 후 거슬리면 삭제해도 됩니다.",
                    "Resolve Studio 연동 패널은 생성한 자막을 타임라인에 직접 넣습니다.",
                ]
                : [
                    "For a full-timeline reference file, place it at the timeline start.",
                    "For an isolated clip, place it at that clip's start.",
                    "A selected range keeps its original position inside the chosen media.",
                    "The tiny invisible anchor cue at the beginning preserves timing. You may delete it after positioning.",
                    "The Resolve Studio integration places generated subtitles directly on the timeline.",
                ]));
        guide.Children.Add(Section(
            korean ? "4. NLE에 SRT 가져오기" : "4. Importing the SRT into an NLE",
            nle));

        guide.Children.Add(Section(
            korean ? "5. 결과가 어긋날 때" : "5. When timing drifts",
            Paragraphs(
                korean
                    ? [
                        "원문과 실제 공연의 순서가 다르거나 후렴 반복, 절 생략, 애드립이 있으면 이후 자막이 밀릴 수 있습니다. 원문을 실제 순서로 고치거나 필요한 구간만 처리해 주세요.",
                        "Windows는 검증된 CUDA를, Apple Silicon Mac은 Metal을 우선 사용합니다. CPU도 가능하지만 더 오래 걸립니다. 모든 처리는 기기 안에서 진행됩니다.",
                    ]
                    : [
                        "Reordered lyrics, repeated choruses, skipped verses, or ad-libs can shift later cues. Correct the lyrics to the performed order or process only the needed range.",
                        "Windows uses verified CUDA and Apple silicon Macs use Metal when available. CPU is slower but supported. Processing stays on your device.",
                    ])));

        Button close = new()
        {
            Content = korean ? "닫기" : "Close",
            MinWidth = 90,
            Padding = new Thickness(14, 5),
            HorizontalAlignment = HorizontalAlignment.Right,
            Background = Brush.Parse(Cream),
            Foreground = Brush.Parse(Green),
            BorderBrush = Brush.Parse(BorderColor),
            BorderThickness = new Thickness(2),
            FontWeight = FontWeight.Bold,
        };
        close.Click += (_, _) => Close();

        Grid root = new()
        {
            RowDefinitions = new RowDefinitions("Auto,*,Auto"),
            Margin = new Thickness(14),
            RowSpacing = 10,
        };
        TextBlock heading = new()
        {
            Text = korean ? "처음부터 따라 하는 사용법" : "Beginner guide",
            FontSize = 15,
            FontWeight = FontWeight.Bold,
            Foreground = Brush.Parse(TextColor),
            HorizontalAlignment = HorizontalAlignment.Left,
        };
        ScrollViewer scroll = new()
        {
            VerticalScrollBarVisibility = Avalonia.Controls.Primitives.ScrollBarVisibility.Auto,
            HorizontalScrollBarVisibility = Avalonia.Controls.Primitives.ScrollBarVisibility.Disabled,
            HorizontalContentAlignment = HorizontalAlignment.Stretch,
            Content = guide,
        };
        Grid.SetRow(heading, 0);
        Grid.SetRow(scroll, 1);
        Grid.SetRow(close, 2);
        root.Children.Add(heading);
        root.Children.Add(scroll);
        root.Children.Add(close);
        Content = root;
    }

    private static Border Section(string title, Control content)
    {
        return new Border
        {
            HorizontalAlignment = HorizontalAlignment.Stretch,
            Background = Brush.Parse(Card),
            BorderBrush = Brush.Parse(BorderColor),
            BorderThickness = new Thickness(2),
            Padding = new Thickness(12, 10),
            Child = new StackPanel
            {
                Spacing = 7,
                Children =
                {
                    new TextBlock
                    {
                        Text = title,
                        FontSize = 13,
                        FontWeight = FontWeight.Bold,
                        Foreground = Brush.Parse(TextColor),
                        HorizontalAlignment = HorizontalAlignment.Left,
                    },
                    content,
                },
            },
        };
    }

    private static StackPanel Paragraphs(IReadOnlyList<string> paragraphs)
    {
        StackPanel panel = new() { Spacing = 7 };
        foreach (string paragraph in paragraphs)
        {
            panel.Children.Add(BodyText(paragraph));
        }
        return panel;
    }

    private static StackPanel ItemList(bool numbered, IReadOnlyList<string> items)
    {
        StackPanel panel = new() { Spacing = 6 };
        for (int index = 0; index < items.Count; index++)
        {
            Grid row = new() { ColumnDefinitions = new ColumnDefinitions("24,*"), ColumnSpacing = 3 };
            row.Children.Add(new TextBlock
            {
                Text = numbered ? $"{index + 1}." : "•",
                FontWeight = FontWeight.Bold,
                Foreground = Brush.Parse(Green),
                TextAlignment = TextAlignment.Right,
                HorizontalAlignment = HorizontalAlignment.Stretch,
            });
            TextBlock text = BodyText(items[index]);
            Grid.SetColumn(text, 1);
            row.Children.Add(text);
            panel.Children.Add(row);
        }
        return panel;
    }

    private static TextBlock BodyText(string text) => new()
    {
        Text = text,
        TextWrapping = TextWrapping.Wrap,
        FontWeight = FontWeight.SemiBold,
        Foreground = Brush.Parse(Dim),
        LineHeight = 18,
        TextAlignment = TextAlignment.Left,
        HorizontalAlignment = HorizontalAlignment.Stretch,
    };
}
