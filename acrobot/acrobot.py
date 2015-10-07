from pprint import pprint
import requests

'''
page options:
    * lists of links: AAA, AAB, etc

    * redirect to a real page: #REDIRECT [[John F. Kennedy]]
        * If a redirect, might have a disam page: 'JFK (disambiguation)'

    * something else?

list item options:
    * acronym is exactly inside link: [[Asian Athletics Association]]
    * multiple links on the line
    * quoted acronym: ''AAA'', a Japanese manga by [[Haruka Fukushima]]
    * A description: [[Morse code]] for "aerial attacker", used in conjunction with SOS'
    * A link with a display name: [[JFK (Clone High)|JFK (''Clone High'')]]
'''
# [[XML2PDF|XML2PDF Formatting Engine Server]] from [http://www.alt-soft.com/ AltSoft] has near 100% support for the XSL-FO 1.1

 # '* Sometimes it refers to both languages considered together, or to the working group that develops both languages',
 # '* Sometimes, especially in the Microsoft world, it refers to a now-obsolete variant of XSLT developed and shipped by Microsoft as part of [[MSXML]] before the W3C specification was finalized',

ENDPOINT = 'https://en.wikipedia.org/w/api.php'

TITLE = 'XSL'

def get(title):
    params = {
        'format': 'json',
        'action': 'query',
        'titles': title,
        'rvprop': 'content',
        'prop': 'revisions|categories',
        'clcategories': ['Category:Disambiguation pages']
    }

    r = requests.get(ENDPOINT, params)

    pages = r.json().get('query').get('pages')
    key = pages.keys()[0]

    try:
        return pages[key]['revisions'][0]['*']

    except KeyError:
        print('No way: no pages for ' + title)
        return ''

def yuck(pages):
    return [y for y in pages if len(y) > 0 and y[0] == '*']

def main():
    page = get(TITLE)

    pages = yuck(page.split('\n'))

    # Check if 

    if len(pages) > 0:
        pprint(pages)

    else:
        page = get(TITLE + ' (disambiguation)')
        pages = yuck(page.split('\n'))
        pprint(pages)

if __name__ == '__main__':
    main()
