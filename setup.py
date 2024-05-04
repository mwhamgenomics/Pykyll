import os
from setuptools import setup, find_packages

requirements_txt = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'requirements.txt')
requirements = [l.strip() for l in open(requirements_txt) if l and not l.startswith('#')]

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'version.txt')) as f:
    __version__ = f.read().strip()

def translate_req(req):
    # this>=0.3.2 -> this(>=0.3.2)
    ops = ('<=', '>=', '==', '<', '>', '!=')
    version = None
    for op in ops:
        if op in req:
            req, version = req.split(op)
            version = op + version

    if version:
        req += '(%s)' % version
    return req

setup(
    name='Pykyll',
    version = __version__,
    packages=find_packages(exclude=('tests',)),
    license='MIT',
    description='A static site builder that does what I want',
    requires=[translate_req(r) for r in requirements],
    install_requires=requirements
)
