"""Formatting utilities for human-readable display."""


def format_bytes(num_bytes: int) -> str:
    """Format bytes into human-readable string.

    Args:
        num_bytes: Number of bytes

    Returns:
        Formatted string like '1.23 GB'

    Examples:
        >>> format_bytes(0)
        '0 B'
        >>> format_bytes(1536)
        '1.50 KB'
        >>> format_bytes(1073741824)
        '1.00 GB'
    """
    if num_bytes is None:
        return "\u2014"
    if num_bytes == 0:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    unit_index = 0
    size = float(num_bytes)

    while size >= 1024.0 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1

    if unit_index == 0:
        return f"{int(size)} B"
    return f"{size:.2f} {units[unit_index]}"


def format_duration(seconds: float) -> str:
    """Format seconds into human-readable duration.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string like '2h 15m 30s'

    Examples:
        >>> format_duration(0)
        '0s'
        >>> format_duration(65.5)
        '1m 5s'
        >>> format_duration(3665)
        '1h 1m 5s'
    """
    if seconds is None:
        return "\u2014"
    if seconds <= 0:
        return "0s"

    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")

    return " ".join(parts)


def format_percent(value: float, decimals: int = 1) -> str:
    """Format a percentage value.

    Args:
        value: Percentage value (0-100)
        decimals: Number of decimal places

    Returns:
        Formatted string like '85.3%'
    """
    if value is None:
        return "\u2014"
    return f"{value:.{decimals}f}%"


def format_ratio(ratio: float) -> str:
    """Format compression ratio.

    Args:
        ratio: Compression ratio (e.g., 0.85 means 85% of original)

    Returns:
        Formatted string like '6.7:1' or '85.0%'
    """
    if ratio is None:
        return "\u2014"
    if ratio <= 0:
        return "N/A"
    if ratio >= 1.0:
        return "1:1 (no savings)"

    inverse = 1.0 / ratio
    return f"{inverse:.1f}:1"


def format_throughput(mbps: float) -> str:
    """Format throughput in appropriate units.

    Args:
        mbps: Throughput in MB/s

    Returns:
        Formatted string like '125.3 MB/s' or '1.23 GB/s'
    """
    if mbps is None:
        return "\u2014"
    if mbps <= 0:
        return "0 MB/s"
    if mbps >= 1024:
        return f"{mbps / 1024:.2f} GB/s"
    if mbps >= 1:
        return f"{mbps:.1f} MB/s"
    return f"{mbps * 1024:.0f} KB/s"


def status_to_icon(status: str) -> str:
    """Map job status to GTK icon name.

    Args:
        status: Job status string

    Returns:
        GTK icon name
    """
    icons = {
        "completed": "emblem-ok-symbolic",
        "running": "media-playback-start-symbolic",
        "queued": "content-loading-symbolic",
        "failed": "dialog-error-symbolic",
    }
    return icons.get(status, "dialog-question-symbolic")


def status_to_css_class(status: str) -> str:
    """Map job status to CSS class for styling.

    Args:
        status: Job status string

    Returns:
        CSS class name
    """
    classes = {
        "completed": "success",
        "running": "accent",
        "queued": "dim-label",
        "failed": "error",
    }
    return classes.get(status, "")
