import sys
import select
import badger2040

display = badger2040.Badger2040()
display.set_update_speed(badger2040.UPDATE_FAST)

poll = select.poll()
poll.register(sys.stdin, select.POLLIN)

pages = [
    ["Waiting for PC...", "Run pc_sender.py", "on your Mac"],
    ["Waiting for GitHub", "status data...", ""]
]
titles = ["PC DASHBOARD (1/2)", "GITHUB STATUS (2/2)"]
current_page = 0
inverted = False

def draw_dashboard():
    bg = 0 if inverted else 15
    fg = 15 if inverted else 0

    display.set_pen(bg)
    display.clear()

    # Header bar
    display.set_pen(fg)
    display.rectangle(0, 0, 296, 26)
    display.set_pen(bg)
    display.set_font("bitmap8")
    display.text(titles[current_page], 8, 5, scale=2)

    # Body lines for active page
    display.set_pen(fg)
    y = 38
    for line in pages[current_page][:3]:
        display.text(line.strip(), 10, y, 276, scale=2)
        y += 28

    display.update()

draw_dashboard()

while True:
    # Check for incoming serial data from Mac
    if poll.poll(100):
        msg = sys.stdin.readline().strip()
        if msg:
            parts = msg.split("||")
            pages[0] = parts[0].split("|")
            if len(parts) > 1:
                pages[1] = parts[1].split("|")
            draw_dashboard()

    # Switch pages with Up / Down buttons
    if display.pressed(badger2040.BUTTON_DOWN) or display.pressed(badger2040.BUTTON_UP):
        current_page = (current_page + 1) % 2
        draw_dashboard()

    # Toggle dark/light mode with Button A
    if display.pressed(badger2040.BUTTON_A):
        inverted = not inverted
        draw_dashboard()

    # Reboot back to launcher with A + C
    if display.pressed(badger2040.BUTTON_A) and display.pressed(badger2040.BUTTON_C):
        import machine
        machine.reset()
