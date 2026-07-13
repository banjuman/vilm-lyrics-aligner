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
        self.assertIn("PYTORCH_ENABLE_MPS_FALLBACK=1", source)

    def test_resolve_plugin_uses_official_system_folder(self):
        source = (MACOS / "install-resolve-plugin.applescript").read_text(encoding="utf-8")
        self.assertIn(
            "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Workflow Integration Plugins",
            source,
        )
        self.assertIn("with administrator privileges", source)

    def test_bundle_declares_macos_14_minimum(self):
        plist = (MACOS / "Info.plist").read_text(encoding="utf-8")
        self.assertIn("com.voiceandfilm.vilmlyricsaligner", plist)
        self.assertIn("LSMinimumSystemVersion", plist)
        self.assertIn("14.0", plist)


if __name__ == "__main__":
    unittest.main()
