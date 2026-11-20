import select
import sys
import badger2040


def run(page_index, title):
    display = badger2040.Badger2040()
    display.set_update_speed(badger2040.UPDATE_FAST)

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

        display.set_pen(fg)
        y = 38
        for line in pages[page_index][:3]:
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
