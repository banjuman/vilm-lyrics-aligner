# Vilm Lyrics Aligner quick guide

## Desktop app

1. Open the video or audio that matches your edit. For a complex NLE timeline, export a lightweight full-timeline reference file first.
2. Paste the complete lyrics, or load a UTF-8 TXT file.
3. Choose **Full file**, or drag over the waveform and choose **Selected range**.
4. Leave **Auto mode** selected for most songs, then choose **Generate SRT**.
5. Import the SRT into your editor. Desktop SRT files include a short invisible cue at zero so NLEs preserve the media-start offset when the subtitle clip is dragged to the timeline start.

Use a full-timeline reference export when subtitle timecodes must match a timeline. Avoid exporting only a marked section unless its timeline start offset is known; a standalone media file normally starts at `00:00:00`.

## DaVinci Resolve Studio

1. Open the target timeline.
2. Open `Workspace > Workflow Integrations > Vilm Lyrics Aligner`.
3. Paste the full lyrics and choose **Generate subtitles**.

For a partial job, set both timeline In and Out marks and select **In/Out range**. You may still paste the full lyrics: the app finds the continuous lyric span heard in that range. Existing subtitle items are preserved.

The direct panel requires Resolve Studio on Windows or macOS. Resolve Free users can use the Desktop app and import its SRT.

## Auto and Manual modes

- **Auto mode** uses line breaks as strong hints, but may split a long or slow line and merge only an obvious display wrap.
- **Manual (advanced)** keeps every non-empty lyric line as its own cue and exposes maximum characters, maximum duration, and end-hold controls.

In Manual mode, place a non-lyrical vocal on its own parenthesized line to reserve its time without displaying it:

```text
First lyric line
(hmm)
Next lyric line
```

Use a short approximation such as `(hmm)`, `(oh)`, or `(ooh)`. Parentheses inside an ordinary lyric line remain visible.

## Processing device

CUDA is preferred on a compatible NVIDIA Windows system. Apple silicon Macs use Apple Metal for Whisper alignment and CPU for vocal separation. CPU remains available as a slower troubleshooting path on both platforms.

## Files and privacy

Processing is local. Temporary decoded audio and vocal stems are deleted after completion or failure. Generated SRT files are saved beside the chosen Desktop output or under `Documents\Lyrics Aligner` for Resolve. Diagnostic JSON is retained locally for up to 30 days and does not replace or upload the supplied lyrics.
