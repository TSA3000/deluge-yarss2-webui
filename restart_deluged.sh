#!/bin/bash
# Used to quickly restart the server during development

killall deluged
#cp /home/bro/.config/deluge/core.conf.yarss2 /home/bro/.config/deluge/core.conf
python setup.py bdist_egg
echo "##############################################################################################"
echo "Start deluge server ##########################################################################"
echo "##############################################################################################"
deluged -l ~/deluged.log -L info
#deluged -l ~/deluged.log -L info -c ~/.config/deluge.empty/
