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
volume = -1
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


def fit_to_width(value, max_width, text_size):
    if display.measure_text(value, text_size) <= max_width:
        return value

    truncated = value
    while truncated and display.measure_text(truncated + "~", text_size) > max_width:
        truncated = truncated[:-1]
    return truncated + "~"


def draw():
    display.set_pen(15)
    display.clear()
    display.set_pen(0)
    display.rectangle(0, 0, 296, 24)
    display.set_pen(15)
    display.text("APPLE MUSIC", 8, 4, scale=2)

    display.set_pen(0)
    display.text(fit_line(track), 10, 34, 250, scale=2)
    display.text(fit_to_width(artist, 250, 1.5), 10, 62, 250, scale=1.5)
    display.text(fit_line(playback_state), 10, 81, 250, scale=2)
    display.text("VOL", 274, 30, 20, scale=1)
    display.rectangle(276, 40, 14, 48)
    display.set_pen(15)
    display.rectangle(278, 42, 10, 44)
    if volume >= 0:
        fill_height = int(44 * volume / 100)
        if fill_height:
            display.set_pen(0)
            display.rectangle(280, 86 - fill_height, 6, fill_height)
    display.set_pen(0)
    volume_label = "--%" if volume < 0 else str(volume) + "%"
    volume_label_width = display.measure_text(volume_label, 1)
    display.text(
        volume_label,
        int(283 - volume_label_width / 2),
        91,
        30,
        scale=1,
    )
    for center, label in (
        (41, "A: BACK"),
        (147, "B: PLAY/PAUSE"),
        (253, "C: NEXT"),
    ):
        label_width = display.measure_text(label, 1)
        display.text(
            label,
            int(center - label_width / 2),
            116,
            98,
            scale=1,
        )
    display.update()


def update_from_host(message):
    global track, artist, playback_state, volume
    fields = message.split("|", 4)
    if len(fields) == 5 and fields[0] == "MEDIA":
        try:
            updated_volume = int(fields[4])
        except ValueError:
            updated_volume = -1
        if updated_volume < -1 or updated_volume > 100:
            updated_volume = -1
        updated_status = (
            fields[1] or "Unknown track",
            fields[2],
            fields[3],
            updated_volume,
        )
        if updated_status != (track, artist, playback_state, volume):
            track, artist, playback_state, volume = updated_status
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
