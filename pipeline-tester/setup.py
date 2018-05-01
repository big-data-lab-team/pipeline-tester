from setuptools import setup

setup(
    name='pipeline-tester',
    packages=['pipeline-tester'],
    entry_points={},
    install_requires=[
        'django',
        'django-tables2',
        'boutiques',
    ]
)
