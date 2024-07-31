#!/usr/bin/env python
# This file is part of the sale_printery_budget module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

import io
import os
import re
from configparser import ConfigParser

from setuptools import find_packages, setup

MODULE = 'sale_printery_budget'
PREFIX = 'trytonar'
MODULE2PREFIX = {}


def read(fname):
    content = io.open(
        os.path.join(os.path.dirname(__file__), fname),
        'r', encoding='utf-8').read()
    content = re.sub(
        r'(?m)^\.\. toctree::\r?\n((^$|^\s.*$)\r?\n)*', '', content)
    return content


def get_require_version(name):
    #if name.startswith('trytonar_'):
        #return ''
    if name in LINKS:
        return '%s@%s' % (name, LINKS[name])
    if minor_version % 2:
        require = '%s >= %s.%s.dev0, < %s.%s'
    else:
        require = '%s >= %s.%s, < %s.%s'
    require %= (name, major_version, minor_version,
        major_version, minor_version + 1)
    return require


config = ConfigParser()
config.read_file(open(os.path.join(os.path.dirname(__file__), 'tryton.cfg')))
info = dict(config.items('tryton'))
for key in ('depends', 'extras_depend', 'xml'):
    if key in info:
        info[key] = info[key].strip().splitlines()
version = info.get('version', '0.0.1')
major_version, minor_version, _ = version.split('.', 2)
major_version = int(major_version)
minor_version = int(minor_version)
series = '%s.%s' % (major_version, minor_version)
if minor_version % 2:
    branch = 'master'
else:
    branch = series

download_url = 'https://github.com/tryton-ar/sale_printery_budget/tree/%s.%s' % (
    major_version, minor_version)

LINKS = {}

requires = []
for dep in info.get('depends', []):
    if not re.match(r'(ir|res)(\W|$)', dep):
        module_name = '%s_%s' % (MODULE2PREFIX.get(dep, 'trytond'), dep)
        requires.append(get_require_version(module_name))

requires.append(get_require_version('trytond'))

tests_require = [get_require_version('proteus')]
dependency_links = [
    'https://github.com/tryton-ar/sale_printery_budget/tarball/%s.%s#egg=trytonar_sale_printery_budget-%s.%s' \
        % (major_version, minor_version, major_version, minor_version),
    ]
if minor_version % 2:
    dependency_links.append('https://trydevpi.tryton.org/')

setup(name='%s_%s' % (PREFIX, MODULE),
    version=version,
    description='Tryton module that adds a wizard to Sale for Printery Budget.',
    long_description=read('README.rst'),
    author='tryton-ar',
    url='https://github.com/tryton-ar/sale_printery_budget',
    download_url=download_url,
    package_dir={'trytond.modules.%s' % MODULE: '.'},
    packages=(
        ['trytond.modules.sale_printery_budget']
        + ['trytond.modules.sale_printery_budget.%s' % p for p in find_packages()]
        ),
    package_data={
        'trytond.modules.%s' % MODULE: (info.get('xml', []) + [
            'tryton.cfg', 'view/*.xml', 'locale/*.po', '*.fodt',
            '*.fods', 'icons/*.svg', 'tests/*.rst']),
        },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Plugins',
        'Framework :: Tryton',
        'Intended Audience :: Developers',
        'Intended Audience :: Financial and Insurance Industry',
        'Intended Audience :: Legal Industry',
        'License :: OSI Approved :: '
        'GNU General Public License v3 or later (GPLv3+)',
        'Natural Language :: English',
        'Natural Language :: Spanish',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Office/Business',
        'Topic :: Office/Business :: Financial :: Accounting',
        ],
    license='GPL-3',
    python_requires='>=3.9',
    install_requires=requires,
    dependency_links=dependency_links,
    zip_safe=False,
    extras_require={
        'test': tests_require,
        },
    entry_points="""
    [trytond.modules]
    %s = trytond.modules.%s
    """ % (MODULE, MODULE),
    )
