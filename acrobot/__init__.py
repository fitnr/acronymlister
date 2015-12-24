#!/usr/bin/env python3
import re
import logging
import sqlite3
import urllib
import requests

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
WIKI_SYNTAX = r"^(=|'''|\{\{|$)"
WIKI_SPLIT = r'[\*\n]'
WIKI_LINK = r'\[\[([^|]+?)(?=[\]|])'


def format_line(line):
    '''
    From a line on a disambiguation page, return a link (possibly None) and a description
    '''
    # todo: remove external links
    match = re.match(WIKI_LINK, line)
    link = match.groups()[0] if match else None
    desc_sans_link = re.sub(r"(?<=\[\[)[^|]+\|", '', line)
    description = re.sub(r"(\[\[|\]\]|'')", "", desc_sans_link)

    return link, description


def get_page_content(json):
    pages = list(json['query']['pages'].values())
    return pages[0]['revisions'][0]['*']


class Acrobot(object):

    fmt = '{description}\nhttps://{lang}.wikipedia.org/wiki/{link}/'

    last_link = None

    def __init__(self, database, log=None, lang=None):
        self.lang = lang or WIKI
        self.headers = {'user-agent': 'Acrobot/{}'.format(self.lang)}
        self.log = log or logging
        self.conn = sqlite3.connect(database)

    @property
    def api(self):
        return "https://{}.wikipedia.org/w/api.php".format(self.lang)

    def compose(self):

        self.last_link, description = self.next_page()
        self.log.info('composing %s', description)
        link = urllib.parse.quote(self.last_link.replace(' ', '_'))
        status = self.fmt.format(description=description, lang=self.lang, link=link),

        update = self.get_page_geo(self.last_link)
        update.update(status=status)
        return update

    def next_page(self):
        '''
        Pick the next page.
        Check off unused acronyms if need be
        '''
        c = self.conn.execute("SELECT link, description FROM acronyms WHERE tweeted != 1 LIMIT 1")
        row = c.fetchone()

        if row is None:
            name = self.next_combo()
            self.get_acronyms(name)
            return self.next_page()

        return row

    def next_combo(self):
        self.checkoff_last_combination()
        name = self.get_next_combination()
        return self.get_acronyms(name)

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
            content = re.sub(r"\[\[Category:[^\]]+\]\]", "", content)

            rawlines = re.split(WIKI_SPLIT, content)
            lines = [g.strip() for g in rawlines if not re.match(WIKI_SYNTAX, g) and '(disambiguation)' not in g]

        except KeyError:
            # empty: make page as tweeted and move to the next one
            self.log.info('No pages for %s' % combination)
            name = self.next_combo()
            return self.get_acronyms(name)

        # not empty: send to database and you're done

        # values = list of (combination, page, description)
        values = [format_line(x) for x in lines]
        insert = "INSERT INTO acronyms VALUES ('{}', ?, ?, 0)".format(combination)

        curs = self.conn.cursor()
        curs.executemany(insert, values)
        self.conn.commit()

    def checkoff_last_combination(self):
        curs = self.conn.cursor()
        curs.execute('SELECT name FROM combinations WHERE tweeted=0 LIMIT 1')
        row = curs.fetchone()
        self.log.debug('checking off %s', row)
        curs.execute("UPDATE combinations SET tweeted=0 WHERE name=?", row)
        self.conn.commit()

    def get_next_combination(self):
        c = self.conn.cursor().execute("SELECT name FROM combinations WHERE tweeted!=1 LIMIT 1")
        return c.fetchone()[0]

    def checkoff_page(self):
        self.conn.cursor().execute('UPDATE acronyms SET tweeted = 1 WHERE link=?', (self.last_link,))
        self.conn.commit()

    def get_page_geo(self, page):
        '''
        Get the lat/lon of a Wikipedia page, if it exists
        '''
        self.log.debug('getting location of %s', page)

        params = {
            'format': 'json',
            'action': 'query',
            'titles': page,
            'rvprop': 'content',
            'prop': 'revisions',
            "redirects": True
        }

        r = requests.get(self.api, params=params, headers=self.headers)
        json = r.json()

        try:
            content = get_page_content(json)

            if '{{coord' not in content:
                raise ValueError

            # Example coord
            # {{Coord|42|22|28|N|71|07|01|W|region:US_type:edu|display=title}}
            match = re.search(r'(?<={{Coord\|)([^}]+)(?=}})', content)

            group = match.groups()[0]

            direction_check = ('N' in group, 'S' in group, 's' in group, 'n' in group)

        except (AttributeError, KeyError, ValueError):
            self.log.debug('Error getting geo for page %s' % page)
            return {"lat": None, "long": None}

        if any(direction_check):
            # It's mins, secs
            fragments = re.split(r'[NSnsWEwe]', group, 2)
            latitude = piped_to_decimal(fragments[0])
            longitude = piped_to_decimal(fragments[1])

        else:
            # it's decimal
            z = group.split('|')
            latitude, longitude = float(z[0]), float(z[1])

        return {"lat": latitude, "long": longitude}


def piped_to_decimal(pipecoord):
    '''Turn xx|zz|yy| into xx.foo'''
    atoms = pipecoord.strip('|').split('|')
    coord = 0
    for i, e in enumerate(atoms):
        coord += float(e) / pow(60, i)
    return coord
