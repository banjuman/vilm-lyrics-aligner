using System.Runtime.InteropServices;
using Avalonia;

namespace VilmLyricsAligner.Desktop;

internal static class Program
{
    private const string WindowsAppId = "Vilm.LyricsAligner.Desktop";

    [DllImport("shell32.dll", CharSet = CharSet.Unicode)]
    private static extern int SetCurrentProcessExplicitAppUserModelID(string appId);

    [STAThread]
    public static void Main(string[] args)
    {
        if (OperatingSystem.IsWindows())
        {
            _ = SetCurrentProcessExplicitAppUserModelID(WindowsAppId);
        }
        BuildAvaloniaApp().StartWithClassicDesktopLifetime(args);
    }

    public static AppBuilder BuildAvaloniaApp() =>
        AppBuilder.Configure<App>()
            .UsePlatformDetect()
            .LogToTrace();
}
