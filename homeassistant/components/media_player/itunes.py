"""
homeassistant.components.media_player.itunes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Provides an interface to iTunes-API (https://github.com/maddox/itunes-api)

Configuration:

To use iTunes you will need to add something like the following to
your configuration.yaml file.

media_player:
  platform: itunes
  name: iTunes
  host: http://192.168.1.16
  port: 8181

Variables:

name
*Optional
The name of the device.

url
*Required
URL of your running version of iTunes-API. Example: http://192.168.1.50:8181

"""
import logging

from homeassistant.components.media_player import (
    MediaPlayerDevice, MEDIA_TYPE_MUSIC, SUPPORT_PAUSE, SUPPORT_SEEK,
    SUPPORT_VOLUME_SET, SUPPORT_VOLUME_MUTE, SUPPORT_PREVIOUS_TRACK,
    SUPPORT_NEXT_TRACK)
from homeassistant.const import (
    STATE_IDLE, STATE_PLAYING, STATE_PAUSED)

import requests

_LOGGER = logging.getLogger(__name__)

SUPPORT_ITUNES = SUPPORT_PAUSE | SUPPORT_VOLUME_SET | SUPPORT_VOLUME_MUTE | \
    SUPPORT_PREVIOUS_TRACK | SUPPORT_NEXT_TRACK | SUPPORT_SEEK


class Itunes(object):
    """ itunes-api client. """

    def __init__(self, host, port):
        self.host = host
        self.port = port

    @property
    def _base_url(self):
        """ Returns the base url for endpoints. """
        return self.host + ":" + str(self.port)

    def _request(self, method, path, params=None):
        """ Makes the actual request and returns the parsed response. """
        url = self._base_url + path

        try:
            if method == 'GET':
                response = requests.get(url)
            elif method == "POST":
                response = requests.put(url, params)
            elif method == "PUT":
                response = requests.put(url, params)
            elif method == "DELETE":
                response = requests.delete(url)

            return response.json()
        except requests.exceptions.HTTPError:
            return {'player_state': 'error'}
        except requests.exceptions.RequestException:
            return {'player_state': 'offline'}

    def _command(self, named_command):
        """ Makes a request for a controlling command. """
        return self._request('PUT', '/' + named_command)

    def now_playing(self):
        """ Returns the current state. """
        return self._request('GET', '/now_playing')

    def set_volume(self, level):
        """ Sets the volume and returns the current state, level 0-100. """
        return self._request('PUT', '/volume', {'level': level})

    def set_muted(self, muted):
        """ Mutes and returns the current state, muted True or False. """
        return self._request('PUT', '/mute', {'muted': muted})

    def play(self):
        """ Sets playback to play and returns the current state. """
        return self._command('play')

    def pause(self):
        """ Sets playback to paused and returns the current state. """
        return self._command('pause')

    def next(self):
        """ Skips to the next track and returns the current state. """
        return self._command('next')

    def previous(self):
        """ Skips back and returns the current state. """
        return self._command('previous')

    def artwork_url(self):
        """ Returns a URL of the current track's album art. """
        return self._base_url + '/artwork'

# pylint: disable=unused-argument
# pylint: disable=abstract-method
# pylint: disable=too-many-instance-attributes


def setup_platform(hass, config, add_devices, discovery_info=None):
    """ Sets up the itunes platform. """

    add_devices([
        ItunesDevice(
            config.get('name', 'iTunes'),
            config.get('host'),
            config.get('port')
        )
    ])


class ItunesDevice(MediaPlayerDevice):
    """ Represents a iTunes-API instance. """

    # pylint: disable=too-many-public-methods

    def __init__(self, name, host, port):
        self._name = name
        self._host = host
        self._port = port

        self.client = Itunes(self._host, self._port)

        self.current_volume = None
        self.muted = None
        self.current_title = None
        self.current_album = None
        self.current_artist = None
        self.current_playlist = None
        self.content_id = None

        self.player_state = None

        self.update()

    def update_state(self, state_hash):
        """ Update all the state properties with the passed in dictionary. """
        self.player_state = state_hash.get('player_state', None)

        self.current_volume = state_hash.get('volume', 0)
        self.muted = state_hash.get('muted', None)
        self.current_title = state_hash.get('name', None)
        self.current_album = state_hash.get('album', None)
        self.current_artist = state_hash.get('artist', None)
        self.current_playlist = state_hash.get('playlist', None)
        self.content_id = state_hash.get('id', None)

    @property
    def name(self):
        """ Returns the name of the device. """
        return self._name

    @property
    def state(self):
        """ Returns the state of the device. """

        if self.player_state == 'offline' or self.player_state is None:
            return 'offline'

        if self.player_state == 'error':
            return 'error'

        if self.player_state == 'stopped':
            return STATE_IDLE

        if self.player_state == 'paused':
            return STATE_PAUSED
        else:
            return STATE_PLAYING

    def update(self):
        """ Retrieve latest state. """
        now_playing = self.client.now_playing()
        self.update_state(now_playing)

    @property
    def is_volume_muted(self):
        """ Boolean if volume is currently muted. """
        return self.muted

    @property
    def volume_level(self):
        """ Volume level of the media player (0..1). """
        return self.current_volume/100.0

    @property
    def media_content_id(self):
        """ Content ID of current playing media. """
        return self.content_id

    @property
    def media_content_type(self):
        """ Content type of current playing media. """
        return MEDIA_TYPE_MUSIC

    @property
    def media_image_url(self):
        """ Image url of current playing media. """

        if self.player_state in (STATE_PLAYING, STATE_IDLE, STATE_PAUSED) and \
           self.current_title is not None:
            return self.client.artwork_url()
        else:
            return 'https://cloud.githubusercontent.com/assets/260/9829355' \
                '/33fab972-58cf-11e5-8ea2-2ca74bdaae40.png'

    @property
    def media_title(self):
        """ Title of current playing media. """
        return self.current_title

    @property
    def media_artist(self):
        """ Artist of current playing media. (Music track only) """
        return self.current_artist

    @property
    def media_album_name(self):
        """ Album of current playing media. (Music track only) """
        return self.current_album

    @property
    def supported_media_commands(self):
        """ Flags of media commands that are supported. """
        return SUPPORT_ITUNES

    def set_volume_level(self, volume):
        """ set volume level, range 0..1. """
        response = self.client.set_volume(int(volume * 100))
        self.update_state(response)

    def mute_volume(self, mute):
        """ mute (true) or unmute (false) media player. """
        response = self.client.set_muted(mute)
        self.update_state(response)

    def media_play(self):
        """ media_play media player. """
        response = self.client.play()
        self.update_state(response)

    def media_pause(self):
        """ media_pause media player. """
        response = self.client.pause()
        self.update_state(response)

    def media_next_track(self):
        """ media_next media player. """
        response = self.client.next()
        self.update_state(response)

    def media_previous_track(self):
        """ media_previous media player. """
        response = self.client.previous()
        self.update_state(response)
