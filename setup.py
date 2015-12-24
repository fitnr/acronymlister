from setuptools import setup

with open('requirements.txt') as f:
    requirements = [i.strip() for i in f.readlines()]

setup(
    name='acrobot',

    version='0.1',

    description='acronym bot',

    url='http://twitter.com/acrobot',

    author='Neil Freeman',

    author_email='contact@fakeisthenewreal.org',

    license='All rights reserved',

    packages=[
        'acrobot',
    ],

    entry_points={
        'console_scripts': [
            'acrobot=acrobot.acrobot:main',
        ],
    },

    install_requires=requirements,

)
