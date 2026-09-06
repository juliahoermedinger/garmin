from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")


def format_duration(total_seconds: float | None) -> str:
    total_seconds = int(total_seconds or 0)
    hours, rem = divmod(total_seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def format_pace(seconds_per_km: float | None) -> str:
    if not seconds_per_km:
        return "-"
    minutes, seconds = divmod(int(seconds_per_km), 60)
    return f"{minutes}:{seconds:02d}/km"


templates.env.filters["duration"] = format_duration
templates.env.filters["pace"] = format_pace
