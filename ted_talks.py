#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import time

import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient


class Container(object):
    """Container is to store info in its instance"""
    pass


def get_html(url):
    header = {'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) \
            AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.109 Safari/537.36'}
    html = requests.get(url, headers=header).content

    count = 0
    while not html:
        # attempt 20 times in 3 * 20 seconds to get html. to avoid server's refusing connection
        time.sleep(3)
        html = requests.get(url, headers=header).content
        count += 1
        if count == 20:
            return
    return html


def crawl(url):
    print('now crawling ' + url)
    html = get_html(url)
    lectures, next_url = get_lectures(html)
    for data in cleaned_data(lectures):
        yield data

    while next_url:
        print('now crawling ' + next_url)
        html = get_html(next_url)
        lectures, next_url = get_lectures(html)
        for data in cleaned_data(lectures):
            yield data


def get_lectures(html):
    host = 'https://www.ted.com'
    soup = BeautifulSoup(html, 'html.parser')
    content = soup.find('div', {'class': 'row row-sm-4up row-lg-6up row-skinny'})
    next_url = None
    try:
        next_url = soup.findAll('a', {'class': "pagination__next pagination__flipper pagination__link"})
        next_url = host + next_url[0].get('href', None)
    except IndexError as e:
        print(e)
    lectures = content.findAll('div', {'class': "media media--sm-v"})
    return lectures, next_url


def get_content(url):
    """get author info and subtitle-url from detailed page by calling get_subtitle
    :param url: the lecture info url
    """
    host = 'https://www.ted.com'
    html = get_html(url)

    soup = BeautifulSoup(html, 'html.parser')
    desc = soup.find('p', {'class': "talk-description"}).contents[0].strip()
    location = soup.find('div', {'class': "player-hero__meta"}).strong.contents[0].strip()
    filmed_time = soup.find('div', {'class': "player-hero__meta"}).findAll('span')[1].contents[-1].strip()
    subtitle_url = host + soup.find('div', {'class': "talk-more"}).a.get('href', '')
    subtitle = get_subtitle(subtitle_url)
    author = soup.find('div', {'class': "talk-speaker__details media__message"})
    author_info = {'name': author.find('div', {'class': "talk-speaker__name h10"}).a.contents[0].strip(),
                   'url': host + author.find('div', {'class': "talk-speaker__name h10"}).a.get('href', ''),
                   'position': author.find('div', {'class': "talk-speaker__description"}).contents[0].strip(),
                   'desc': author.find('div', {'class': "talk-speaker__bio"}).contents[0].strip()}
    return author_info, desc, subtitle, location, filmed_time


def cleaned_data(lectures):
    host = 'https://www.ted.com'
    container = Container()

    for lecture in lectures:
        lecture_content = lecture.find('div', {'class': "media__message"})
        lecture_image = lecture.find('div', {'class': "media__image media__image--thumb talk-link__image"})

        container.title = lecture_content.a.contents[0].strip()
        container.author = lecture_content.find('h4', {'class': "h12 talk-link__speaker"}).contents[0].strip()
        container.post_time = lecture_content.find('span', {'class': 'meta__item'}).span.contents[0].strip()
        rated = lecture_content.find('span', {'class': 'meta__row'}).span.contents[0].strip()
        container.rated = rated.replace(' ', '').split(',')

        container.lecture_url = host + lecture_image.a.get('href', '')
        container.image_url = lecture_image.find('img', {'class': "thumb__image"}).get('src', '')
        container.duration = lecture_image.find('span', {'class': "thumb__duration"}).contents[0].strip()

        try:
            author_info, lecture_desc, subtitle, location, filmed_time = get_content(container.lecture_url)
            container.author_info = author_info
            container.lecture_desc = lecture_desc
            container.subtitle = subtitle
            container.location = location
            container.filmed_time = filmed_time
        except Exception as e:
            print(e)
            print('no author %s info at %s' % (container.author, container.lecture_url))

        yield container.__dict__


def get_subtitle(url):
    """get subtitle
    :param url: the url contains subtitle
    """
    html = get_html(url)

    soup = BeautifulSoup(html, 'html.parser')
    lines = soup.find('div', {'class': "col-lg-7 col-lg-offset-1"}).findAll('span')
    subtitle = ''
    for line in lines:
        subtitle += line.contents[0]
    subtitle = '.\n'.join([i.replace('\n', '').strip() for i in subtitle.split('.')])
    return subtitle


def save_data_in_file(data):
    with open('data.json', 'w') as f:
        json.dump(data, f)


def save_data_in_database(data):
    try:
        client = MongoClient("mongodb://localhost:27017")
        db = client.ted
        if type(data) == list:
            for row in data:
                db.talks.insert(row)
        else:
            db.talks.insert(data)
        client.close()
    except Exception as e:
        print(e)
        print("connection error")


def main():
    start_url = 'https://www.ted.com/talks?page=1'
    res = crawl(start_url)
    data = []
    lec_id = 0

    for lecture in res:
        lecture['_id'] = lec_id
        lec_id += 1
        data.append(lecture)
        # save_data_in_database(lecture)

        print('\t' + lecture.get('title'))
    save_data_in_file(data)

if __name__ == '__main__':
    main()
