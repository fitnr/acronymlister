#!/usr/bin/env python3
import re
import logging
import sqlite3
import urllib
import requests
from twitter_bot_utils import helpers

__version__ = '0.1'

'''
list item options:
    * acronym is exactly inside link: [[Asian Athletics Association]]
    * multiple links on the line
    * acronym: ''AAA'', a Japanese manga by [[Haruka Fukushima]]
    * A description: [[Morse code]] for "aerial attacker", used in conjunction with SOS'
    * A link with a display name: [[JFK (Clone High)|JFK (''Clone High'')]]
    * Wikilink with external link in desc: [[XML2PDF|XML2PDF Formatting Engine Server]] from [http://www.alt-soft.com/ AltSoft] has near 100% support for the XSL-FO 1.1
'''

WIKI = 'en'
DISAMB_CAT = 'Category:Disambiguation pages'
WIKI_SYNTAX = r"^(=|'''|\{\{|In [^:]+:|\w+ may refer to:|$)"
WIKI_SPLIT = r'[\*\n]'
WIKI_LINK = r'\[\[([^|]+?)(?=[\]|])'


def format_line(line):
    '''
    From a line on a disambiguation page, return a link (possibly None) and a description
    Will return the first link it finds.
    '''
    match = re.search(WIKI_LINK, line)
    link = match.groups()[0] if match else ''
    desc_sans_link = re.sub(r"(?<=\[\[)[^|]+\|", '', line)
    description = re.sub(r"(\[\[|\]\]|'')", "", desc_sans_link)

    return link, description


def get_page_content(json):
    pages = list(json['query']['pages'].values())
    return pages[0]['revisions'][0]['*']


class Acrobot(object):

    link = ''
    kml = 'https://tools.wmflabs.org/kmlexport/'

    def __init__(self, database, log=None, twitter=None, lang=None):
        self.lang = lang or WIKI
        self.headers = {'user-agent': 'Acrobot/{}'.format(self.lang)}
        self.log = log or logging
        self.conn = sqlite3.connect(database)
        self.twitter = twitter

    @property
    def api(self):
        return "https://{}.wikipedia.org/w/api.php".format(self.lang)

    def compose(self):
        acronym, self.link, description = self.next_page()
        self.log.info('composing %s - %s', self.link, description)

        if acronym not in description and len(description) < 140:
            description = '{} is {}'.format(acronym, description)

        update = self.get_page_geo(self.link)

        update['status'] = helpers.shorten(description, ellipsis=True)

        self.log.debug('%s', update)

        return update

    def next_page(self):
        '''
        Pick the next page.
        Check off unused acronyms if need be
        '''
        c = self.conn.execute("SELECT acronym, link, description FROM acronyms WHERE tweeted != 1 LIMIT 1")
        row = c.fetchone()

        if row is None:
            self.log.debug("Couldn't find a row, checking off another")
            name = self.checkoff_get_next_combination()
            self.get_acronyms(name)
            self.follow(name)
            return self.next_page()

        return row

    def get_acronyms(self, combination):
        '''
        Visit wikipedia and download acronyms from a particular letter combination
        Get the acronyms for a letter combination and populate the acronyms DB
        '''
        self.log.debug('getting acronyms for %s', combination)

        params = {
            'format': 'json',
            'action': 'query',
            'titles': '{} (disambiguation)'.format(combination),
            'rvprop': 'content',
            'prop': 'revisions|categories',
            'clcategories': [DISAMB_CAT],
            "redirects": True
        }

        r = requests.get(self.api, params=params, headers=self.headers)
        json = r.json()

        try:
            content = get_page_content(json)

            self.log.debug("Got %d chars of content for %s", len(content), combination)

            content = re.sub(r"\[\[Category:[^\]]+\]\]", "", content)

            rawlines = re.split(WIKI_SPLIT, content)
            lines = [g.strip() for g in rawlines if not re.match(WIKI_SYNTAX, g) and '(disambiguation)' not in g]

        except KeyError:
            # empty: make page as tweeted and move to the next one
            self.log.info('No pages for %s' % combination)
            name = self.checkoff_get_next_combination()
            return self.get_acronyms(name)

        # not empty: send to database and you're done

        # values = list of (combination, page, description)
        values = [format_line(x) for x in lines]
        insert = "INSERT INTO acronyms VALUES ('{}', ?, ?, 0)".format(combination)

        curs = self.conn.cursor()
        curs.executemany(insert, values)
        self.conn.commit()

    def follow(self, screen_name):
        if not self.twitter:
            return
        try:
            self.twitter.create_friendship(screen_name=screen_name)
            self.log.info('Following @%s', screen_name)
        except Exception as e:
            self.log.info('Error following @%s: %s', screen_name, e)
            pass

    def checkoff_get_next_combination(self):
        checkoff = """UPDATE combinations SET tweeted = 1 WHERE name=(
            SELECT name FROM combinations WHERE tweeted != 1 LIMIT 1
        )"""
        curs = self.conn.cursor()
        self.log.debug('checking off a row')
        curs.execute(checkoff)
        self.conn.commit()

        curs.execute("SELECT name FROM combinations WHERE tweeted != 1 LIMIT 1")
        result = curs.fetchone()
        self.log.info('Next combination: %s', result)

        return result[0]

    def checkoff_page(self):
        self.conn.cursor().execute('UPDATE acronyms SET tweeted = 1 WHERE link=?', (self.link,))
        self.conn.commit()

    def get_page_geo(self, page):
        '''
        Get the lat/lon of a Wikipedia page, if it exists.
        Uses the kmlexport WMF labs utility and janky regex parsing
        '''
        self.log.debug('getting location of %s', page)

        r = requests.get(self.kml, params={'article': page}, headers=self.headers)

        if 'No geocoded items found' in r.text:
            return {"lat": None, "long": None}

        try:
            coord_pat = r'(?<=<coordinates>)(-?[\d.]+),(-?[\d.]+),?0?(?=</coordinates>)'
            match = re.search(coord_pat, r.text)
            x, y = match.groups()
            x, y = float(x), float(y)

        except (AttributeError, KeyError, ValueError) as e:
            self.log.error('Error finding geo on %s', page)
            self.log.error('%s', e)
            x, y = None, None

        return {"lat": y, "long": x}
