# Badger Bodger
At GitHub events, the Badger 2040 is pre-loaded with data to personalise it to the individual with data taken from their attendee registration barcode. This repo contains the scripts for the badge customization code.  At the event this runs on a Raspberry Pi with a 2D barcode scanner attached, however it can also run on laptop (tested on macOS).  It is assumed that the Badger 2040 is running a stock Badger OS image as flashed from the[Pimoroni](https://pimoroni.com/) Factory in Sheffield. The scripts were tested against [this Badger OS image](https://github.com/pimoroni/badger2040/releases/tag/v0.0.4).

## Badger Modifications
On top of the stock Badger OS image, the following changes are made:
- A GitHub event branded [badge.py](preload/examples/badge.py) that displays the attendee name with a background image and corresponding badge.txt file containing the personalised data
- Separate launcher apps for Mac system stats, GitHub Status, weather, and Apple Music, populated by [pc_sender.py](pc_sender.py) and [media_sender.py](scripts/media_sender.py). Run `python3 pc_sender.py` for the dashboards or `python3 scripts/media_sender.py` for Apple Music, then select the matching app from the launcher. The media sender reconnects if the badge resets, displays the current track, maps A/B/C to previous/play-pause/next, and maps Up/Down to volume. Press A+C to return to the launcher; A alone inverts the dashboard colors.

### Automatic badge sender (macOS)

Install the user LaunchAgent once from the repository root:
```
python3 scripts/install_launch_agent.py
```

The background service starts at login, waits for the badge's USB serial connection, and handles both dashboard updates and Apple Music controls through one connection. It reconnects when the badge is unplugged or reset, so no Terminal window needs to stay open. Do not run `pc_sender.py` or `media_sender.py` separately while this service is active. Logs are written to `~/Library/Logs/BadgerBodger/sender.log`.

To sync the device while the service is active, run:
```
python3 scripts/sync_badge.py
```

This pauses the sender, runs a one-shot deployment, and restarts the sender after `Sync complete; device reset.` The watcher can also be run directly with `python3 scripts/watch_badger.py --once` when the sender service is stopped.

To stop and remove the service:
```
python3 scripts/install_launch_agent.py uninstall
```

## Running on a laptop
Install the latest version of python 3 via homebrew
```
brew install python
```
Install Python prerequisites
```
pip3 install -r scripts/requirements.txt
```
Run the GUI
```
python3 scripts/gui/main.py
```
Or optionally run the manual flashing script
```
python3 scripts/bodge.py
```

### Developing on a Badger 2040

Install the requirements if you have not already, then run this from the repository root:
```
python3 scripts/watch_badger.py
```

Keep the watcher running while you develop. It deploys the contents of `preload/` when a Badger is connected, copies changed or new files, and removes files deleted from `preload/` during that session. Each deployment resets the device so it can load the updated files. Press `Ctrl-C` to stop the watcher.

## Badger Bodger Device
The Badger Bodger itself is a Raspberry Pi with a small display and a 2D barcode scanner attached.

### Scanner Hardware
- Raspberry Pi 4 Model B – 4GB RAM
- 64GB MicroSD Card
- Hyperpixel 4.0 Touchscreen Display [UK](https://shop.pimoroni.com/products/hyperpixel-4?variant=12569485443155)
- [3D printed case](https://www.printables.com/model/121395-case-for-hyperpixel-40-with-raspberrypi-4)
- 2D Barcode Scanner [US](https://amzn.to/3ScbSAK) [UK](https://amzn.to/3Q9JGMd)
- USB-A to USB-C cable
- USB-C Power Supply (multi-region)

### Hardware Construction
The Hyperpixel 4.0 display comes with all the hardware you need to build the unit in combination with the 3D printed case. 

- Install the GPIO pin expansion header onto the Raspberry Pi
- Screw in the PCB standoffs to the back of the Hyperpixel 4.0
- Insert the Raspberry Pi into the 3D printed case (note, a bit of jiggling is required as it's snug fit)
- Connect the Hyperpixel 4.0 to the Raspberry Pi using the GPIO pins and push down gently
- Screw in the Hyperpixel 4.0 and Raspberry Pi to the 3D printed case using the screws provided

## Setting up the Barcode Scanner
By default, most hardware barcode scanners will be configured as a US keyboard HID device and type the characters entered followed by a carrage return.  However, those types of readers will ignore accented and unicode characters encoded as text.  Setting up the scanner to act like a Spanish keyboard changes how it enters accented characters giving the main character followed the the accents which makes it slighty easier to parse out those characters that the badger cannot display with the built in fonts.

For the model of barcode reader we are using (EY-H2) scan the following QR control codes to configure which keyboard setting it should be in.

<img width="400" alt="image" src="https://github.com/user-attachments/assets/4c384939-ca46-4353-b42b-e6cad6a9a875">


### Preparing the SD Card
Note that Raspbian Bookworm was released during the construction of the badge scanners, however it looked like it contained lots of changes to the desktop environment and how python operates that we haven't tested with it yet.  Therefore, when using Raspberry Pi Imager to flash the SD card, used the "Raspberry PI OS (Legacy)" opetion which is located under the "Raspberry Pi OS (other)" section.

In advanced options (the little gear icon), the following options were selected:
- Set hostname to "scannerXX" where XX is the number of the scanner
- Enable SSH using password authentication
- Set the user to `badger` and password to the one stored in the password manager
- Configure Wireless LAN to connect to the appropriate network
- Set the locale to `US/Los Angeles` and keyboard layout to `US`
- Set the options to not eject the card after writing



Once Raspbian is flashed to the SD card, run the following to edit `firstrun.sh` and `config.txt`
```
./prepcard.sh
```

This includes the following just before the last 3 lines of the script (i.e. just before) `rm -f /boot/firstrun.sh`

```
# Create the install.sh script to clone a git repo, then run firstrun.sh in it
mkdir -p /home/badger/.config/autostart
cat << EOF > /home/badger/install.sh
#!/bin/bash
sleep 30
git clone --branch prod https://github.com/badger/badgerbodger.git /home/badger/badgerbodger
chmod +x /home/badger/badgerbodger/firstrun.sh
/bin/bash /home/badger/badgerbodger/firstrun.sh
rm /home/badger/.config/autostart/install.desktop
# rm /home/badger/install.sh
exit 0
EOF

# Run the install.sh script on boot
cat << EOF > /home/badger/.config/autostart/install.desktop
[Desktop Entry]
Name=Install
Exec=/bin/bash /home/badger/install.sh
EOF
chown -R badger:badger /home/badger

```

And then it also edits the config.txt file to add the following to the bottom of the file:
```
# Hyperpixel 4.0
dtoverlay=vc4-kms-dpi-hyperpixel4
```
Then eject the SD card from your laptop, insert it into the Raspberry Pi and boot.  Provided the Raspberry Pi has internet connectivity, within a few minutes the desktop will be displayed and then a few minutes after than the badge scanner GUI will be displayed.
