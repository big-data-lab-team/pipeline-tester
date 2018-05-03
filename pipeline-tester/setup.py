from setuptools import setup

DEPS = ['django',
        'django-tables2',
        'boutiques==0.5.9']

setup(
    name='pipeline-tester',
    packages=['pipeline-tester'],
    entry_points={},
    install_requires=DEPS,
    setup_requires=DEPS
)
