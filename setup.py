#!/usr/bin/env python
# coding:utf-8

"""
Distutils setup script.
"""

from setuptools import setup

from Service_Transcoding.__meta__ import __version__, __author__, __contact__

setup(
    # -- meta information --------------------------------------------------
    name='Service_Transcoding',
    version=__version__,
    author=__author__,
    author_email=__contact__,

    # -- Package structure -------------------------------------------------
    packages=[
        'Service_Transcoding',
        'Service_Transcoding.ffmpegConverter',
        'Service_Transcoding.Service',
        ],
    install_requires=['celery==3.1.15',
                      'requests==2.6.0',
                      'simplejson==2.0.9',
                      'Sphinx==1.2.2',
                      'nose==1.3.1'],
    zip_safe=False,
    exclude_package_data={'': ['.hg', '.hglf']},

    # -- self - tests --------------------------------------------------------
    test_suite='nose.collector',
    tests_require=['nose'],
    )
