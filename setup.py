from setuptools import setup, find_packages

setup(
    name='geo_indicators',
    version='0.1',
    description='A Python package for geographic indicators and climate modelling',
    author='Franziskakis F. and Werner N.',
    author_email='florian.franziskakis@unige.ch, niklas.werner@eaps.ethz.ch',
    license='GPLv3',
    packages=find_packages(),
    install_requires=[
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Scientific/Engineering :: GIS',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.12',
    ],
    python_requires='>=3.12',
    keywords='geography indicators climate visualization spatial-analysis',
)
