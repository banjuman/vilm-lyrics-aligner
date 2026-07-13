using Avalonia;
using Avalonia.Controls;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Markup.Xaml;

namespace VilmLyricsAligner.Desktop;

public sealed partial class App : Application
{
    public override void Initialize() => AvaloniaXamlLoader.Load(this);

    public override void OnFrameworkInitializationCompleted()
    {
        if (ApplicationLifetime is IClassicDesktopStyleApplicationLifetime desktop)
        {
            try
            {
                desktop.MainWindow = new MainWindow(EngineRuntime.Load());
            }
            catch (Exception exception) when (OperatingSystem.IsMacOS())
            {
                desktop.ShutdownMode = ShutdownMode.OnExplicitShutdown;
                var setup = new SetupWindow(
                    () =>
                    {
                        var main = new MainWindow(EngineRuntime.Load());
                        desktop.MainWindow = main;
                        desktop.ShutdownMode = ShutdownMode.OnMainWindowClose;
                        main.Show();
                    },
                    exception.Message);
                desktop.MainWindow = setup;
            }
        }
        base.OnFrameworkInitializationCompleted();
    }
}
