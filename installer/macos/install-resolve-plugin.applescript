on run argv
    if (count of argv) is not 1 then error "The Resolve plugin source path is required."
    set sourcePath to item 1 of argv
    set pluginDirectory to "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Workflow Integration Plugins"
    set pluginPath to pluginDirectory & "/Vilm Lyrics Aligner.py"
    set legacyPath to pluginDirectory & "/LyricsAligner.py"
    set commandText to "/bin/mkdir -p " & quoted form of pluginDirectory & " && /bin/cp -f " & quoted form of sourcePath & " " & quoted form of pluginPath & " && /bin/rm -f " & quoted form of legacyPath
    do shell script commandText with administrator privileges
end run
