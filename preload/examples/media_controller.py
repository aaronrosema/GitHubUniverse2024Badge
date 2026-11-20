import select
import sys
import time

import badger2040


STATUS_INTERVAL = 2000

display = badger2040.Badger2040()
display.set_update_speed(badger2040.UPDATE_FAST)
display.set_font("bitmap8")

poll = select.poll()
poll.register(sys.stdin, select.POLLIN)

track = "Waiting for Apple Music"
artist = ""
playback_state = ""
previous_a = False
previous_b = False
previous_c = False
previous_up = False
previous_down = False


def send_command(command):
    sys.stdout.write(command + "\n")


def fit_line(value, limit=23):
    if len(value) > limit:
        return value[:limit - 1] + "~"
    return value


def draw():
    display.set_pen(15)
    display.clear()
    display.set_pen(0)
    display.rectangle(0, 0, 296, 24)
    display.set_pen(15)
    display.text("APPLE MUSIC", 8, 4, scale=2)

    display.set_pen(0)
    display.text(fit_line(track), 10, 34, 276, scale=2)
    display.text(fit_line(artist, 40), 10, 62, 276, scale=1)
    display.text(fit_line(playback_state), 10, 81, 276, scale=2)
    display.text("A: BACK   B: PLAY/PAUSE   C: NEXT", 8, 101, 280, scale=1)
    display.update()


def update_from_host(message):
    global track, artist, playback_state
    fields = message.split("|", 3)
    if len(fields) == 4 and fields[0] == "MEDIA":
        updated_status = (
            fields[1] or "Unknown track",
            fields[2],
            fields[3],
        )
        if updated_status != (track, artist, playback_state):
            track, artist, playback_state = updated_status
            draw()


draw()
last_request = time.ticks_ms() - STATUS_INTERVAL

while True:
    display.keepalive()
    now = time.ticks_ms()
    if time.ticks_diff(now, last_request) >= STATUS_INTERVAL:
        send_command("MEDIA:GET")
        last_request = now

    if poll.poll(100):
        update_from_host(sys.stdin.readline().strip())

    pressed_a = display.pressed(badger2040.BUTTON_A)
    pressed_b = display.pressed(badger2040.BUTTON_B)
    pressed_c = display.pressed(badger2040.BUTTON_C)
    pressed_up = display.pressed(badger2040.BUTTON_UP)
    pressed_down = display.pressed(badger2040.BUTTON_DOWN)

    if pressed_a and pressed_c:
        import machine
        machine.reset()
    if pressed_a and not previous_a:
        send_command("MEDIA:PREVIOUS")
    if pressed_b and not previous_b:
        send_command("MEDIA:PLAY_PAUSE")
    if pressed_c and not previous_c:
        send_command("MEDIA:NEXT")
    if pressed_up and not previous_up:
        send_command("MEDIA:VOLUME_UP")
    if pressed_down and not previous_down:
        send_command("MEDIA:VOLUME_DOWN")

    previous_a = pressed_a
    previous_b = pressed_b
    previous_c = pressed_c
    previous_up = pressed_up
    previous_down = pressed_down
