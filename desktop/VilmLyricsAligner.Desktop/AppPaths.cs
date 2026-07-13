namespace VilmLyricsAligner.Desktop;

internal static class AppPaths
{
    public static string Root
    {
        get
        {
            string? overridePath = Environment.GetEnvironmentVariable("LYRICS_ALIGNER_APP_ROOT");
            if (!string.IsNullOrWhiteSpace(overridePath))
            {
                return Path.GetFullPath(Environment.ExpandEnvironmentVariables(overridePath));
            }

            if (OperatingSystem.IsMacOS())
            {
                return Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
                    "Library", "Application Support", "Vilm Lyrics Aligner");
            }

            return Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "LyricsAligner");
        }
    }

    public static string Config => Path.Combine(Root, "config.json");
    public static string Preferences => Path.Combine(Root, "desktop-preferences.json");

    public static string FindBundledPayload()
    {
        string besideExecutable = Path.Combine(AppContext.BaseDirectory, "payload");
        if (Directory.Exists(besideExecutable))
        {
            return besideExecutable;
        }

        string macResources = Path.GetFullPath(
            Path.Combine(AppContext.BaseDirectory, "..", "Resources", "payload"));
        return macResources;
    }
}
