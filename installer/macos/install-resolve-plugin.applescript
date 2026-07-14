on run argv
    if (count of argv) is not 2 then error "The Resolve plugin and Python package paths are required."
    set sourcePath to item 1 of argv
    set pythonPackagePath to item 2 of argv
    set pluginDirectory to "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Workflow Integration Plugins"
    set pluginPath to pluginDirectory & "/Vilm Lyrics Aligner.py"
    set legacyPath to pluginDirectory & "/LyricsAligner.py"
    set pythonFramework to "/Library/Frameworks/Python.framework/Versions/3.12/Python"
    set installPython to "if [ ! -f " & quoted form of pythonFramework & " ]; then /usr/sbin/installer -pkg " & quoted form of pythonPackagePath & " -target /; fi"
    set installPlugin to "/bin/mkdir -p " & quoted form of pluginDirectory & " && /bin/rm -f " & quoted form of pluginPath & " " & quoted form of legacyPath & " && /bin/cp -X " & quoted form of sourcePath & " " & quoted form of pluginPath
    set commandText to installPython & " && " & installPlugin
    do shell script commandText with administrator privileges
end run
