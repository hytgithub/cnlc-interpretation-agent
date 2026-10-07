"""SVG多道测井图：深度向下，空值断线，孤立采样点可见。"""
from html import escape
import math

COLORS = ('#0f766e', '#b45309', '#2563eb', '#be123c', '#7c3aed', '#4d7c0f', '#0369a1', '#c2410c')


def render_log_curves(context, tracks, source_label):
    width, height = 88 + 190 * len(tracks) + 24, 740
    left, top, bottom = 88, 102, height - 80
    span = context['bottom_depth_m'] - context['top_depth_m']
    def y(depth):
        return top + (depth - context['top_depth_m']) / span * (bottom - top)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
             '<rect width="100%" height="100%" fill="#ffffff"/>',
             '<g font-family="Arial, sans-serif" fill="#1e293b">',
             f'<text x="20" y="27" font-size="14">{escape(context["well_id"])}</text>',
             '<text x="20" y="64" font-size="11">MD (m)</text>']
    for i in range(7):
        depth = context['top_depth_m'] + span * i / 6
        yy = y(depth)
        parts.extend([f'<line x1="{left}" x2="{width-24}" y1="{yy:.2f}" y2="{yy:.2f}" stroke="#e2e8f0"/>',
                      f'<text x="{left-10}" y="{yy+4:.2f}" text-anchor="end" font-size="10">{depth:.2f}</text>'])
    for index, track in enumerate(tracks):
        x0, usable = left + 190 * index, 166
        values = [v for _, v in track['points'] if v is not None and (track['scale'] != 'log' or v > 0)]
        transform = math.log10 if track['scale'] == 'log' else float
        minimum, maximum = (min(values), max(values)) if values else (0, 1)
        lo, hi = (transform(minimum), transform(maximum)) if values else (0, 1)
        axis_span = hi - lo
        # Opposite finite extremes can have an infinite difference. Normalize
        # only that case, retaining subtraction precision for narrow ranges.
        divisor = max(abs(lo), abs(hi)) if math.isinf(axis_span) else 1
        scaled_lo, scaled_hi = lo / divisor, hi / divisor
        def x(value):
            fraction = .5 if lo == hi else (transform(value) / divisor - scaled_lo) / (scaled_hi - scaled_lo)
            return x0 + 12 + fraction * usable
        parts.extend([f'<text x="{x0+95}" y="55" text-anchor="middle" font-size="13" fill="{COLORS[index]}">{escape(track["curve_name"])}</text>',
                      f'<text x="{x0+95}" y="73" text-anchor="middle" font-size="10">{escape(track["unit"])} · {track["scale"]}</text>',
                      f'<rect x="{x0}" y="{top}" width="190" height="{bottom-top}" fill="none" stroke="#cbd5e1"/>'])
        for j in range(5):
            xx = x0 + 12 + usable * j / 4
            parts.append(f'<line x1="{xx:.2f}" x2="{xx:.2f}" y1="{top}" y2="{bottom}" stroke="#f1f5f9"/>')
            if lo == hi and j != 2:
                continue
            fraction = j / 4
            if lo == hi or j == 0:
                label = minimum
            elif j == 4:
                label = maximum
            elif track['scale'] == 'log':
                label = 10 ** ((1 - fraction) * lo + fraction * hi)
            else:
                label = (1 - fraction) * minimum + fraction * maximum
            parts.append(f'<text x="{xx:.2f}" y="91" text-anchor="middle" font-size="9">{label:.3g}</text>')
        segments, segment = [], []
        for depth, value in track['points']:
            if value is None or (track['scale'] == 'log' and value <= 0):
                if segment:
                    segments.append(segment)
                    segment = []
            else:
                segment.append((x(value), y(depth)))
        if segment:
            segments.append(segment)
        for segment in segments:
            path = ' '.join(f'{"M" if i == 0 else "L"}{xx:.2f},{yy:.2f}' for i, (xx, yy) in enumerate(segment))
            parts.append(f'<path d="{path}" fill="none" stroke="{COLORS[index]}" stroke-width="1.4"/>')
            if len(segment) == 1:
                xx, yy = segment[0]
                parts.append(f'<circle cx="{xx:.2f}" cy="{yy:.2f}" r="2" fill="{COLORS[index]}"/>')
        parts.append(f'<text x="{x0+95}" y="{bottom+22}" text-anchor="middle" font-size="10">N={track["sample_count"]} · null={track["null_count"]}</text>')
    parts.extend([f'<text x="20" y="{height-24}" font-size="9" fill="#64748b">{escape(source_label)}</text>', '</g></svg>'])
    return ''.join(parts), width, height
