import badger2040

display = badger2040.Badger2040()
display.set_update_speed(badger2040.UPDATE_NORMAL)

# Clear screen to white (15)
display.set_pen(15)
display.clear()

# Draw black (0) header bar and text
display.set_pen(0)
display.rectangle(0, 0, 296, 32)

display.set_pen(15)
display.set_font("bitmap8")
display.text("HELLO WORLD", 10, 8, scale=2)

display.set_pen(0)
display.text("Press A, B, or C!", 10, 55, scale=2)
display.update()

while True:
    if display.pressed(badger2040.BUTTON_A):
        display.set_pen(15)
        display.rectangle(10, 90, 276, 30)
        display.set_pen(0)
        display.text("Button A pressed!", 10, 95, scale=2)
        display.update()
    if display.pressed(badger2040.BUTTON_A) and display.pressed(badger2040.BUTTON_C):
        import machine
        machine.reset()