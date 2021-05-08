from spotipy import Spotify
from bs4 import BeautifulSoup
from requests_html import HTMLSession 

import os
from sys import exc_info
from youtube_dl import YoutubeDL
from urllib.request import urlopen
from pathlib import Path

from mutagen.easyid3 import EasyID3, ID3
from mutagen.id3 import APIC as AlbumCover, USLT
from mutagen.id3 import ID3, ID3NoHeaderError

import asyncio

from pyppeteer import errors
import requests

'''
def get_song():
    #CODE 
'''

def get_plalist_tracks(sp: Spotify, url):

    results = sp.playlist_tracks(playlist_id=url)

    urls = []

    tracks = results['items']

    while results['next']:
        results = sp.next(results)
        tracks.extend(results['items'])

    songs = []

    print('appending songs')

    for track in tracks:                                #TAKES A HELL LOT OF TIME
        songs.append(sp.track(track['track']['id']))

    print('songs appended')

    return songs

def search(song, mode):

    maxRetry = 3

    connection_errors = (ConnectionError, TimeoutError, requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout, requests.exceptions.HTTPError, errors.NetworkError, errors.TimeoutError)

    if mode == 'n':
        query = (song['name'] + ' ' + song['artists'][0]['name']).replace(' ','+')
    elif mode =='t':
        query = (song['name'] + ' ' + song['artists'][0]['name'] + ' - Topic').replace(' ','+')
    elif mode == 'a':
        query = (song['name'] + ' ' + song['artists'][0]['name'] + ' (Official Audio)').replace(' ','+')

    if '&' in query:
        query = query.replace('&','%26')

    print(f'Search query: {query}')

    url = f'https://www.youtube.com/results?search_query={query}'

    while True:    
        try:
            #init an HTML session
            session = HTMLSession()

            # get the html content
            response = session.get(url)

            # execute Java-script
            response.html.render(sleep=1)

            # create bs object to parse HTML
            soup = BeautifulSoup(response.html.html, "html.parser")

            links = soup.find_all('a')

            print('getting link')    
            for link in links:
                link = link.get('href')
                try:
                    if(link.find('/watch') != -1):
                        #asyncio.run(session.browser.disconnect())
                        #asyncio.run(session.browser.close())
                        session.close()
                        link =  f'https://www.youtube.com{link}'
                        return link
                        exit()

                except AttributeError:
                    continue

        except connection_errors:
            session.close()
            if maxRetry < 1:
                print('Retry limit reached. Breaking out of loop....')
                break
            else:
                print('\nConnection Timed out. Trying again...\n')
                maxRetry -= 1
                continue

        except SystemExit:
            exit()

        except:
            session.close()
            if maxRetry < 1:
                print('Retry limit reached. Breaking out of loop....')
                break
            else:
                print('\nAn error occured. Trying again...\n')
                maxRetry -= 1
                continue
            
        break                   #break out of while if program succeeds

def download(title, url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192'
        }],
        'outtmpl': '../{}.%(ext)s'.format(title)
    }

    print(ydl_opts['outtmpl'])

    with YoutubeDL(ydl_opts) as ydl:
        
        if not os.path.isfile(f'../{title}.mp3'):
            ydl.download([url])
        
        else:
            print('File already exists not downloading')

def set_meta(sp, song, filename):
    
    for disallowedChar in ['/', '?', '\\', '*', '|', '<', '>','\"',':']:
        if disallowedChar in filename:
            if '\"' in filename:
                filename = filename.replace('\"','\'')
            else:
                filename = filename.replace(disallowedChar, '')

    path = f'../{filename}.mp3'
    print(filename)
    print(os.path.isfile(path))

    maxRetry = 3

    while True:
        try:
            print('Getting metadata.....')
            primaryArtistId = song['artists'][0]['id']
            rawArtistMeta = sp.artist(primaryArtistId)

            albumId = song['album']['id']
            rawAlbumMeta = sp.album(albumId)

            songName = song['name']

            albumName = song['album']['name']

            contributingArtists = []
            for artist in song['artists']:
                contributingArtists.append(artist['name'])

            duration = round(song['duration_ms'] / 1000, ndigits=3)

            trackNumber = song['track_number']

            genre = rawAlbumMeta['genres'] + rawArtistMeta['genres']

            print('embedding meta')
            # embed song details
            # ! we save tags as both ID3 v2.3 and v2.4
            # ! The simple ID3 tags
            try:
                audioFile = EasyID3(path)
            except:
                audioFile = EasyID3()

            # ! song name
            audioFile['title'] = songName
            audioFile['titlesort'] = songName

            # ! track number
            audioFile['tracknumber'] = str(trackNumber)

            # ! disc number
            audioFile['discnumber'] = str(song['disc_number'])

            # ! genres (pretty pointless if you ask me)
            # ! we only apply the first available genre as ID3 v2.3 doesn't support multiple
            # ! genres and ~80% of the world PC's run Windows - an OS with no ID3 v2.4 support
            genres = genre
            if len(genres) > 0:
                audioFile['genre'] = genres[0]

            # ! all involved artists
            audioFile['artist'] = contributingArtists

            # ! album name
            audioFile['album'] = song['album']['name']

            # ! album artist (all of 'em)
            albumArtists = []

            for artist in song['album']['artists']:
                albumArtists.append(artist['name'])

            audioFile['albumartist'] = albumArtists

            # ! album release date (to what ever precision available)
            audioFile['date'] = song['album']['release_date']
            audioFile['originaldate'] = song['album']['release_date']

            # ! save as both ID3 v2.3 & v2.4 as v2.3 isn't fully features and
            # ! windows doesn't support v2.4 until later versions of Win10
            audioFile.save(path,v2_version=3)

            # ! setting the album art
            audioFile = ID3(path)
            rawAlbumArt = urlopen(song['album']['images'][0]['url']).read()
            audioFile['APIC'] = AlbumCover(
                encoding=3,
                mime='image/jpeg',
                type=3,
                desc='Cover',
                data=rawAlbumArt
            )

            audioFile.save(v2_version=3)
        
        except:
            if maxRetry < 1:
                print('Retry limit reached. Breaking out of loop....')
                break
            else:
                print('\nAn error occured. Trying again...\n')
                maxRetry -= 1
                continue

        break

    print('done')

def create_title(song):

    if len(song['artists']) > 1:
        title = song['name'] + ' - ' + song['artists'][0]['name'] + ', ' + song['artists'][1]['name']
    else:
        title = song['name'] + ' - ' + song['artists'][0]['name']

    for disallowedChar in ['/', '?', '\\', '*', '|', '<', '>','\"',':']:
        if disallowedChar in title:
            if '\"' in title:
                title = title.replace('\"','\'')
            elif ':' in title:
                title = title.replace(':','-')
            else:
                title = title.replace(disallowedChar, '')

    return title