import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MACOS = ROOT / "installer" / "macos"


class MacOSPackagingTests(unittest.TestCase):
    def test_build_is_apple_silicon_only_and_self_contained(self):
        source = (MACOS / "build-macos.sh").read_text(encoding="utf-8")
        self.assertIn('"$(uname -m)" == "arm64"', source)
        self.assertIn("-r osx-arm64", source)
        self.assertIn("--self-contained true", source)
        self.assertIn("VilmLyricsAligner-1.0.0-apple-silicon.dmg", source)

    def test_runtime_is_private_and_mps_capable(self):
        source = (MACOS / "install-runtime.sh").read_text(encoding="utf-8")
        self.assertIn('expected_suffix="/Library/Application Support/Vilm Lyrics Aligner"', source)
        self.assertIn('"torch==$TORCH_VERSION"', source)
        self.assertIn("torch.backends.mps.is_available()", source)
        self.assertIn('backend="$("$python_exe" -c', source)
        self.assertIn("PYTORCH_ENABLE_MPS_FALLBACK=1", source)

    def test_resolve_plugin_uses_official_system_folder(self):
        source = (MACOS / "install-resolve-plugin.applescript").read_text(encoding="utf-8")
        self.assertIn(
            "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Workflow Integration Plugins",
            source,
        )
        self.assertIn("/Library/Frameworks/Python.framework/Versions/3.12/Python", source)
        self.assertIn("/usr/sbin/installer -pkg", source)
        self.assertIn("/bin/cp -X", source)
        self.assertIn("with administrator privileges", source)

    def test_resolve_python_package_is_pinned_and_verified(self):
        build = (MACOS / "build-macos.sh").read_text(encoding="utf-8")
        runtime = (MACOS / "install-runtime.sh").read_text(encoding="utf-8")
        expected_hash = "8373e58da4ea146b3eb1c1f9834f19a319440b6b679b06050b1f9ee3237aa8e4"
        self.assertIn("python-3.12.10-macos11.pkg", build)
        self.assertIn("https://www.python.org/ftp/python/3.12.10/", build)
        self.assertIn(expected_hash, build)
        self.assertIn("pkgutil --check-signature", build)
        self.assertIn(expected_hash, runtime)
        self.assertIn('osascript "$helper" "$plugin" "$resolve_python_pkg"', runtime)
        self.assertIn('progress 98 "Verifying DaVinci Resolve Studio integration', runtime)
        self.assertIn('python3.12"', runtime)
        self.assertIn('/usr/bin/cmp -s "$plugin" "$resolve_plugin"', runtime)

    def test_bundle_declares_macos_14_minimum(self):
        plist = (MACOS / "Info.plist").read_text(encoding="utf-8")
        self.assertIn("com.voiceandfilm.vilmlyricsaligner", plist)
        self.assertIn("LSMinimumSystemVersion", plist)
        self.assertIn("14.0", plist)


if __name__ == "__main__":
    unittest.main()
