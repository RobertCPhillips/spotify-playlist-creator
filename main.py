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
    matched_artist = get_closest_matching_artist(artist_name, artists)

    if matched_artist is None:
        logging.warning(f'no matching artist found for {artist_name}')
        return {'id': None, 'name': artist_name, 'uri': None}

    logging.debug("match artist name: " + matched_artist['name'])

    return {
        'id': matched_artist['id'],
        'name': matched_artist['name'],
        'uri': matched_artist['uri'],
        'top_tracks': get_artist_top_tracks(matched_artist['id'])
    }


def get_closest_matching_artist(artist_name, artists):
    def has_expected_genre(genres):
        logging.info(f'checking {artist_name} with genres {genres}')
        return any(('ska' == genre or 'punk' in genre for genre in genres))

    def has_matching_name(spotify_name):
        logging.info(f'checking artist name {artist_name} with spotify name {spotify_name}')
        artist_name_std = artist_name.lower().replace('the ', '')
        spotify_name_std = spotify_name.lower().replace('the ', '')
        return artist_name_std == spotify_name_std

    return next((
        artist for artist in artists
        if has_matching_name(artist['name']) and has_expected_genre(artist['genres'])
    ), None)


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
    # logging.debug(artists_config)
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
            # add_to_playlist(playlist_id, track_uris)

    logging.info('playlist loaded')
