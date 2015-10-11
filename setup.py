import os

from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.rst')) as f:
    README = f.read()

setup(
    name='score.ws',
    version='0.1',
    description='WebSocket server of The SCORE Framework',
    long_description=README,
    author='strg.at',
    author_email='score@strg.at',
    url='http://score-framework.org',
    keywords='score framework web websocket tornado',
    packages=['score.ws'],
    install_requires=[
        'score.init >= 0.2',
    ],
)
