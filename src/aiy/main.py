#!/usr/bin/env python3
# Copyright 2017 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Run a recognizer using the Google Assistant Library.

The Google Assistant Library has direct access to the audio API, so this Python
code doesn't need to record audio. Hot word detection "OK, Google" is supported.

It is available for Raspberry Pi 2/3 only; Pi Zero is not supported.
"""

import logging
import platform
import subprocess
import sys

import aiy.assistant.auth_helpers
from aiy.assistant.library import Assistant
import aiy.audio
import aiy.voicehat
from google.assistant.library.event import EventType

import vlc

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
)


def power_off_pi():
    aiy.audio.say('Good bye!')
    subprocess.call('sudo shutdown now', shell=True)


def reboot_pi():
    aiy.audio.say('See you in a bit!')
    subprocess.call('sudo reboot', shell=True)


def say_ip():
    ip_address = subprocess.check_output("hostname -I | cut -d' ' -f1", shell=True)
    aiy.audio.say('My IP address is %s' % ip_address.decode('utf-8'))

def volume(change):

    """Changes the volume and says the new level."""

    GET_VOLUME = r'amixer get Master | grep "Front Left:" | sed "s/.*\[\([0-9]\+\)%\].*/\1/"'
    SET_VOLUME = 'amixer -q set Master %d%%'

    res = subprocess.check_output(GET_VOLUME, shell=True).strip()
    try:
        logging.info("volume: %s", res)
        vol = int(res) + change
        vol = max(0, min(100, vol))
        subprocess.call(SET_VOLUME % vol, shell=True)
        aiy.audio.say('Volume at %d %%.' % vol)
    except (ValueError, subprocess.CalledProcessError):
        logging.exception("Error using amixer to adjust volume.")


def volume_up():
    volume(10)


def volume_down():
    volume(-10)


def radio_off():
    try:
        player.stop()
    except NameError as e:
        logging.info("Player isn't playing")


def get_station(station_name):
    stations = {
        'classic rock': 'http://aacplus-ac-128.timlradio.co.uk/',
        'sixties': 'http://aacplus-a6-128.timlradio.co.uk/',
        'seventies': 'http://aacplus-a7-128.timlradio.co.uk/',
        'eighties': 'http://aacplus-a8-128.timlradio.co.uk/',
        'ninties': 'http://aacplus-a9-128.timlradio.co.uk/',
        'cool FM': 'http://icy-e-bl-09-boh.sharp-stream.com:8000/coolfm.mp3',
        'belfast': 'http://edge-audio-03-gos2.sharp-stream.com:80/qr967.mp3',
        'kerrang': 'http://icy-e-bl-05-cr.sharp-stream.com:8000/kerrang.mp3',
        '1': 'http://a.files.bbci.co.uk/media/live/manifesto/audio/simulcast/hls/uk/sbr_high/ak/bbc_radio_one.m3u8',
        'one': 'http://a.files.bbci.co.uk/media/live/manifesto/audio/simulcast/hls/uk/sbr_high/ak/bbc_radio_one.m3u8',
        '2': 'http://a.files.bbci.co.uk/media/live/manifesto/audio/simulcast/hls/uk/sbr_high/ak/bbc_radio_two.m3u8',
        '3': 'http://a.files.bbci.co.uk/media/live/manifesto/audio/simulcast/hls/uk/sbr_high/ak/bbc_radio_three.m3u8',
        '4': 'http://a.files.bbci.co.uk/media/live/manifesto/audio/simulcast/hls/uk/sbr_high/ak/bbc_radio_fourfm.m3u8',
        '5': 'http://a.files.bbci.co.uk/media/live/manifesto/audio/simulcast/hls/uk/sbr_high/ak/bbc_radio_five_live.m3u8',
        '5 sports': 'http://a.files.bbci.co.uk/media/live/manifesto/audio/simulcast/hls/uk/sbr_high/ak/bbc_radio_five_live_sports_extra.m3u8',
        '6': 'http://a.files.bbci.co.uk/media/live/manifesto/audio/simulcast/hls/uk/sbr_high/ak/bbc_6music.m3u8',
        '1xtra': 'http://a.files.bbci.co.uk/media/live/manifesto/audio/simulcast/hls/uk/sbr_high/ak/bbc_radio_1xtra.m3u8',
        '4 extra': 'http://a.files.bbci.co.uk/media/live/manifesto/audio/simulcast/hls/uk/sbr_high/ak/bbc_radio_four_extra.m3u8',
        'nottingham': 'http://a.files.bbci.co.uk/media/live/manifesto/audio/simulcast/hls/uk/sbr_high/ak/bbc_radio_nottingham.m3u8',
        'planet rock': 'http://icy-e-bz-08-boh.sharp-stream.com/planetrock.mp3',
                }
    return stations[station_name]


def radio(text):
    logging.info("Radio command received: %s ", text)
    station_name = (text.replace('radio', '', 1)).strip()
    if station_name == "off":
        logging.info("Switching radio off")
        radio_off()
        return
    try:
        station = get_station(station_name)
    except KeyError as e:
        logging.error("Error finding station %s", station_name)
        # Set a default station here
        station = 'http://aacplus-ac-128.timlradio.co.uk/'
    logging.info("Playing radio: %s ", station)
    instance = vlc.Instance()
    global player
    player = instance.media_player_new()
    media = instance.media_new(station)
    player.set_media(media)
    player.play()


def process_event(assistant, event):
    status_ui = aiy.voicehat.get_status_ui()
    if event.type == EventType.ON_START_FINISHED:
        status_ui.status('ready')
        if sys.stdout.isatty():
            print('Say "OK, Google" then speak, or press Ctrl+C to quit...')

    elif event.type == EventType.ON_CONVERSATION_TURN_STARTED:
        status_ui.status('listening')

    elif event.type == EventType.ON_RECOGNIZING_SPEECH_FINISHED and event.args:
        print('You said:', event.args['text'])
        text = event.args['text'].lower()
        if text == 'power off':
            assistant.stop_conversation()
            power_off_pi()
        elif text == 'reboot':
            assistant.stop_conversation()
            reboot_pi()
        elif text == 'ip address':
            assistant.stop_conversation()
            say_ip()
        elif text == 'volume up':
            assistant.stop_conversation()
            volume_up()
        elif text == 'volume down':
            assistant.stop_conversation()
            volume_down()
        elif 'radio' in text:
            assistant.stop_conversation()
            radio(text)

    elif event.type == EventType.ON_END_OF_UTTERANCE:
        status_ui.status('thinking')

    elif event.type == EventType.ON_CONVERSATION_TURN_FINISHED:
        status_ui.status('ready')

    elif event.type == EventType.ON_ASSISTANT_ERROR and event.args and event.args['is_fatal']:
        sys.exit(1)



    
    
    elif event.type == EventType.ON_END_OF_UTTERANCE:
        status_ui.status('thinking')

    elif (event.type == EventType.ON_CONVERSATION_TURN_FINISHED
          or event.type == EventType.ON_CONVERSATION_TURN_TIMEOUT
          or event.type == EventType.ON_NO_RESPONSE):
        status_ui.status('ready')

    elif event.type == EventType.ON_ASSISTANT_ERROR and event.args and event.args['is_fatal']:
        sys.exit(1)

def _on_button_pressed():
    radio_off()

def main():
    if platform.machine() == 'armv6l':
        print('Cannot run hotword demo on Pi Zero!')
        exit(-1)

    credentials = aiy.assistant.auth_helpers.get_assistant_credentials()
    with Assistant(credentials) as assistant:
        for event in assistant.start():
            process_event(assistant, event)


if __name__ == '__main__':
    main()
