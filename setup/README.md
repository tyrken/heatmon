# Setup

Initial setup for your Raspberry Pi (aka RPi) - which can be done over SSH without connecting a keyboard/monitor to it following the steps in [headless/README.md](headless/README.md).

## Installing system requirements

Paste & edit the commands below in a RPi console to setup the system ready for heatmon:

```bash
# Install & setup git (skip if you've already done some of this)
sudo apt update
sudo apt install -y git
git config --global user.name "Your Name"
git config --global user.email "youremail@somedomain.com"

# Clone the repo
git clone https://github.com/tyrken/heatmon.git

# Run the main setup script - this is automated and can take a long time
heatmon/setup/setup.sh
# ... hopefully it will eventually display "Finished."
```

## Monitoring

The setup script install Prometheus to collect & store stats, and Grafana for visualisation.

Note they use a fair amount of memory, but are powerful & you can enable emailed alerts if you edit the grafana override file to point at a valid SMTP server, e.g. from your ISP.

See https://github.com/tyrken/heatmon/wiki/Completing-the-Raspberry-Pi-Setup for full docs.

### Long-term storage

The current approx storage usage is a bit over 0.5 MB per TRV-day (very rough estimate!), but Prometheus is meant
to be run on fast disks - not SD cards like we have on a Raspberry Pi!  This is probably why you'll see Grafana
slow to render graphs when you extend the time range.

Currently `setup.sh` sets Prometheus to retain up to 200 MiB - the limiting factor being the main memory size rather
than likely free disk space, so Linux can keep the files cached in main memory.  You might try increaseing this if
you want - but at your own risk!

* TODO: Try adding Thanos for long-term data in AWS S3...
