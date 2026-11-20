# Native iOS build

Open the [IPA workflow](../.github/workflows/build-ipa.yml) for the exact commands, SDK checks and pinned source revision. In [GitHub Actions](https://github.com/Niimahz/Anker-port/actions/workflows/build-ipa.yml), choose **Run workflow** on the intended branch if you have repository write access.

1. The macOS runner selects an Xcode SDK with the required MetalFX API and checks out Madeira at the revision specified in the workflow.
2. It builds archive dependencies for iPhone and applies the Anker branding and SwiftUI integration to the upstream target.
3. The workflow checks the integrated Swift sources, prepares native dependencies and invokes the upstream toolchain.
4. It packages the unsigned app as AnkerPort-unsigned.ipa and runs the repository’s IPA verifier before uploading **AnkerPort-Unsigned-IPA**.

Download the artifact from the completed run and unzip it once. A successful packaging check establishes that the expected payload is present. Device signing, JIT and individual game compatibility still depend on the install and game.

[Architecture](ARCHITECTURE.md) · [IPA verification script](../runtime/tools/verify-ipa.py)
