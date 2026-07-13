using Avalonia;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Media;

namespace VilmLyricsAligner.Desktop;

public sealed class WaveformSelectionChangedEventArgs(double start, double end) : EventArgs
{
    public double Start { get; } = start;
    public double End { get; } = end;
}

public sealed class WaveformControl : Control
{
    private IReadOnlyList<double> _peaks = [];
    private double? _dragOrigin;

    public double Duration { get; private set; }
    public double RangeStart { get; private set; }
    public double RangeEnd { get; private set; }
    public bool SelectionEnabled { get; set; }

    public event EventHandler<WaveformSelectionChangedEventArgs>? SelectionChanged;

    public WaveformControl()
    {
        ClipToBounds = true;
        Cursor = new Cursor(StandardCursorType.Cross);
    }

    public void SetWaveform(double duration, IReadOnlyList<double> peaks)
    {
        Duration = Math.Max(0, duration);
        RangeStart = 0;
        RangeEnd = Duration;
        _peaks = peaks;
        InvalidateVisual();
    }

    public void UseFullRange()
    {
        SelectionEnabled = false;
        RangeStart = 0;
        RangeEnd = Duration;
        InvalidateVisual();
    }

    public override void Render(DrawingContext context)
    {
        base.Render(context);
        var bounds = Bounds;
        context.FillRectangle(new SolidColorBrush(Color.Parse("#20251F")), bounds);
        if (_peaks.Count == 0 || bounds.Width <= 1 || bounds.Height <= 1)
        {
            return;
        }

        double center = bounds.Height / 2;
        double step = bounds.Width / _peaks.Count;
        var waveformPen = new Pen(new SolidColorBrush(Color.Parse("#D8CFAE")), 1);
        for (int index = 0; index < _peaks.Count; index++)
        {
            double x = index * step;
            double amplitude = Math.Max(1, _peaks[index] * bounds.Height * 0.43);
            context.DrawLine(waveformPen, new Point(x, center - amplitude), new Point(x, center + amplitude));
        }

        if (!SelectionEnabled || Duration <= 0)
        {
            return;
        }
        double left = RangeStart / Duration * bounds.Width;
        double right = RangeEnd / Duration * bounds.Width;
        var shade = new SolidColorBrush(Color.FromArgb(155, 8, 12, 9));
        context.FillRectangle(shade, new Rect(0, 0, Math.Max(0, left), bounds.Height));
        context.FillRectangle(shade, new Rect(right, 0, Math.Max(0, bounds.Width - right), bounds.Height));
        var marker = new Pen(new SolidColorBrush(Color.Parse("#F6C522")), 2);
        context.DrawLine(marker, new Point(left, 0), new Point(left, bounds.Height));
        context.DrawLine(marker, new Point(right, 0), new Point(right, bounds.Height));
    }

    protected override void OnPointerPressed(PointerPressedEventArgs e)
    {
        base.OnPointerPressed(e);
        if (Duration <= 0)
        {
            return;
        }
        SelectionEnabled = true;
        _dragOrigin = PositionToSeconds(e.GetPosition(this).X);
        RangeStart = _dragOrigin.Value;
        RangeEnd = _dragOrigin.Value;
        e.Pointer.Capture(this);
        e.Handled = true;
        InvalidateVisual();
    }

    protected override void OnPointerMoved(PointerEventArgs e)
    {
        base.OnPointerMoved(e);
        if (_dragOrigin is null)
        {
            return;
        }
        double current = PositionToSeconds(e.GetPosition(this).X);
        RangeStart = Math.Min(_dragOrigin.Value, current);
        RangeEnd = Math.Max(_dragOrigin.Value, current);
        SelectionChanged?.Invoke(this, new WaveformSelectionChangedEventArgs(RangeStart, RangeEnd));
        e.Handled = true;
        InvalidateVisual();
    }

    protected override void OnPointerReleased(PointerReleasedEventArgs e)
    {
        base.OnPointerReleased(e);
        if (_dragOrigin is null)
        {
            return;
        }
        double current = PositionToSeconds(e.GetPosition(this).X);
        RangeStart = Math.Min(_dragOrigin.Value, current);
        RangeEnd = Math.Max(_dragOrigin.Value, current);
        _dragOrigin = null;
        e.Pointer.Capture(null);
        SelectionChanged?.Invoke(this, new WaveformSelectionChangedEventArgs(RangeStart, RangeEnd));
        e.Handled = true;
        InvalidateVisual();
    }

    private double PositionToSeconds(double x) =>
        Math.Clamp(x / Math.Max(1, Bounds.Width) * Duration, 0, Duration);
}
