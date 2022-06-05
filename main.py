import html
import json
import logging
import os
import random
import requests

logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)

client_id = os.getenv('spotify_client_id')
client_secret = os.getenv('spotify_client_secret')
bearer_token = os.getenv('spotify_bearer_token')
playlist_id = os.getenv('spotify_playlist_id')

if not all([client_id, client_secret, bearer_token, playlist_id]):
    raise EnvironmentError(
        'The environment variables client_id, client_secret, bearer_token, and playlist_id must be set.'
    )

# def get_authorization_token():
#     tokens = requests.post('https://accounts.spotify.com/api/token', data={
#         'grant_type': 'authorization_code',
#         'redirect_uri': 'redirect_uri',
#         'code': code
#     })


def perform_spotify_get_request(url):
    try:
        response = requests.get(
            url,
            headers={'Authorization': f'Bearer {bearer_token}'}
        )
    except requests.exceptions.HTTPError as err:
        logging.error(f'An http error occured: {err}')
        raise
    return response.json()


def get_artist(artist_name):
    artist_data = perform_spotify_get_request(
        f'https://api.spotify.com/v1/search?q={artist_name}&type=artist'
    )

    artists = artist_data['artists']['items']

    if 0 == len(artists):
        logging.warning(f'no artist returned for {artist_name}')
        return {'id': None, 'name': artist_name, 'uri': None}

    artist = get_closest_matching_artist(artist_name, artists)

    return {
        'id': artist['id'],
        'name': artist['name'],
        'uri': artist['uri'],
        'top_tracks': get_artist_top_tracks(artist['id'])
    }

def get_closest_matching_artist(artist_name, artists):
    matched_artist = {}
    if 1 < len(artists):
        logging.warning(f'more than 1 artist returned for {artist_name}')
        artist_name_lower = artist_name.lower()
        for artist in artists:
            spotify_artist_name = artist['name'].lower()
            if(artist_name_lower == spotify_artist_name):
                matched_artist = artist
                break
        if not matched_artist:
            #if we don't find a good match then just pick the first one
            matched_artist = artists[0]

        logging.debug("match artist name: " + matched_artist['name'])
    else:
        matched_artist = artists[0]
    
    return matched_artist


def get_artist_top_tracks(artist_id):
    top_tracks = perform_spotify_get_request(
        f'https://api.spotify.com/v1/artists/{artist_id}/top-tracks?market=US'
    )
    return [{
        'id': track['id'],
        'name': track['name'],
        'uri': track['uri']
    } for track in top_tracks['tracks']] if 'tracks' in top_tracks else []


def add_to_playlist(playlist_id, track_uris):
    try:
        response = requests.post(
            f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks',
            headers={
                'Authorization': f'Bearer {bearer_token}',
                'Content-Type': 'application/json'
            },
            json={
                "uris": track_uris,
                "position": 0
            }
        )
    except requests.exceptions.HTTPError as err:
        logging.error(f'An http error occured: {err}')
        raise


def get_artists_config(config_file_path):
    with open(config_file_path) as f:
        return json.load(f)


def get_artist_config_from_page_data(
    url='https://thefestfl.com/page-data/bands/page-data.json',
    track_sample_size=3
):
    try:
        response = requests.get(url)
    except requests.exceptions.HTTPError as err:
        logging.error(f'An http error occured: {err}')
        raise
    data = response.json()

    arists = data['result']['data']['allFestPerformers']['edges'] if 'result' in data \
        and 'data' in data['result'] \
        and 'allFestPerformers' in data['result']['data'] \
        and 'edges' in data['result']['data']['allFestPerformers'] else []

    return {
        'track_sample_size': track_sample_size,
        'artist_names': [html.unescape(name['node']['title']['rendered']) for name in arists]
    }


def get_artist_track_selection(tracks, sample_size):
    return random.sample(tracks, sample_size) \
        if sample_size < len(tracks) else tracks


if '__main__' == __name__:
    # get artists
    # artists_config = get_artists_config('artists_config_test.json')
    # logging.debug(artists_config)

    artists_config = get_artist_config_from_page_data()
    logging.debug(artists_config)
    sample_size = artists_config['track_sample_size']

    artists_data = [
        get_artist(name) for name in artists_config['artist_names']
    ]

    # get tracks, update playlist
    for artist in artists_data:
        if 'top_tracks' in artist:
            track_uris = [
                track['uri'] for track in get_artist_track_selection(artist['top_tracks'], sample_size)
            ]
            add_to_playlist(playlist_id, track_uris)

    logging.info('playlist loaded')
