# Headless setup

If you want to access & configure the Raspberry Pi via SSH rather than connecting a monitor & keyboard, you can enable
the SSH Server & copy in your WiFi SSID and password so it connects to your network automatically.

1. Create a SD card with your boot image, e.g. using the Imager https://www.raspberrypi.org/documentation/installation/installing-images/. I suggest the choosing **Raspbian Pi OS Lite** if you don't need a desktop.
1. Additionally copy the two non-readme files (`ssh` and `wpa_supplicant.conf`) to the "boot" partition  of the SD card you can see from Windows.  Yes the `ssh` file is meant to be empty & don't add any file extensions to either.
1. Edit the `wpa_supplicant.conf` file now on the SD card to fill in your WiFi SSID and password or encrypted PSK.  Use a non-formating non-renaming editor.
1. Eject the SD card, plug it into the RPi and let it boot - it can take 5 mins for the initial boot to proceed enough for `ssh pi@raspberrypi` to work, with the standard default password of `raspberry`.

I strongly recommend passwordless authentication via your local SSH key:

```sh
# <on your PC/Laptop> Copy your SSH public key to the RPi for future passwordless authentication
ssh-copy-id pi@raspberrypi

# Check it works
ssh pi@raspberrypi

# <on the RPi> Update the standard password, disable password authentication, and rename the host
passwd
sudo sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo raspi-config nonint do_hostname mynewhostname
sudo reboot
```
