import select
import sys
import badger2040

try:
    import pngdec
except ImportError:
    pngdec = None


ICON_SEARCH_DIRS = (
    "/examples/weather_icons",
    "weather_icons",
    "examples/weather_icons",
    "preload/examples/weather_icons",
    "/images/weather",
    "images/weather",
    "preload/images/weather",
)

COND_TO_CODE = {
    "clear sky": 0,
    "mainly clear": 1,
    "partly cloudy": 2,
    "overcast": 3,
    "foggy": 45,
    "fog": 45,
    "rime fog": 48,
    "light drizzle": 51,
    "drizzle": 53,
    "dense drizzle": 55,
    "light rain": 61,
    "rain": 63,
    "heavy rain": 65,
    "light snow": 71,
    "snow": 73,
    "heavy snow": 75,
    "snow grains": 77,
    "rain showers": 80,
    "mod. showers": 81,
    "moderate showers": 81,
    "heavy showers": 82,
    "snow showers": 85,
    "heavy snow shw": 86,
    "heavy snow showers": 86,
    "thunderstorm": 95,
}


def resolve_weather_icon(page_lines):
    code = None
    if len(page_lines) > 3:
        val = page_lines[3].strip()
        if val and val != "-1":
            try:
                code = int(val)
            except ValueError:
                code = val

    if code is None and len(page_lines) > 1:
        line = page_lines[1].strip()
        if line.lower().startswith("cond:"):
            cond_text = line[5:].strip().lower()
            code = COND_TO_CODE.get(cond_text)

    candidates = []
    if code is not None:
        candidates.append(f"{code}.png")
    candidates.append("default.png")

    for directory in ICON_SEARCH_DIRS:
        for filename in candidates:
            path = f"{directory}/{filename}"
            try:
                with open(path, "rb"):
                    return path
            except OSError:
                continue
    return None


def run(page_index, title):
    display = badger2040.Badger2040()
    display.set_update_speed(badger2040.UPDATE_FAST)

    png = None
    if pngdec is not None:
        try:
            png = pngdec.PNG(display.display)
        except Exception:
            png = None

    poll = select.poll()
    poll.register(sys.stdin, select.POLLIN)

    pages = [
        ["Waiting for Mac", "system stats...", ""],
        ["Waiting for GitHub", "status data...", ""],
        ["Waiting for", "weather data...", ""],
    ]
    inverted = False

    def draw():
        bg = 0 if inverted else 15
        fg = 15 if inverted else 0

        display.set_pen(bg)
        display.clear()
        display.set_pen(fg)
        display.rectangle(0, 0, 296, 26)
        display.set_pen(bg)
        display.set_font("bitmap8")
        display.text(title, 8, 5, scale=2)

        raw_lines = pages[page_index]
        icon_path = resolve_weather_icon(raw_lines) if page_index == 2 else None

        if page_index == 2 and icon_path and png:
            # Weather page with condition icon
            lines = []
            if len(raw_lines) >= 3 and raw_lines[0].startswith("Temp: ") and " (Feels " in raw_lines[0]:
                parts = raw_lines[0].split(" (Feels ")
                lines.append(parts[0])
                lines.append("Feels: " + parts[1].rstrip(")"))
                lines.append(raw_lines[1])
                lines.append(raw_lines[2])
            else:
                lines = [l.strip() for l in raw_lines[:3] if l.strip()]

            display.set_pen(fg)
            y = 33 if len(lines) > 3 else 38
            step = 22 if len(lines) > 3 else 28
            for line in lines:
                display.text(line.strip(), 10, y, 215, scale=2)
                y += step

            icon_x, icon_y = 232, 50
            if inverted:
                display.set_pen(15)
                display.rectangle(icon_x - 2, icon_y - 2, 56, 56)
            try:
                png.open_file(icon_path)
                png.decode(icon_x, icon_y)
            except OSError:
                pass
        else:
            display.set_pen(fg)
            y = 38
            for line in raw_lines[:3]:
                display.text(line.strip(), 10, y, 276, scale=2)
                y += 28

        display.update()

    draw()

    while True:
        display.keepalive()

        if poll.poll(100):
            message = sys.stdin.readline().strip()
            if message:
                sections = message.split("||")
                if page_index < len(sections):
                    pages[page_index] = sections[page_index].split("|")
                    draw()

        if display.pressed(badger2040.BUTTON_A):
            if display.pressed(badger2040.BUTTON_C):
                import machine
                machine.reset()
            inverted = not inverted
            draw()
