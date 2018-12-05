import io
from setuptools import setup, find_packages

main_ns = {}
exec(open('dash/version.py').read(), main_ns)  # pylint: disable=exec-used

setup(
    name='dj-plotly-dash',
    version=main_ns['__version__'],
    author='Sergei Pikhovkin',
    author_email='s@pikhovkin.ru',
    packages=find_packages(exclude=['tests*']),
    license='MIT',
    description=('A Python framework for building reactive web-apps. '
                 'Developed by Plotly.'),
    long_description=io.open('README.md', encoding='utf-8').read(),
    long_description_content_type='text/markdown',
    install_requires=[
        'Django>=1.9,<2.2',
        'plotly>=2.0.8',
        # 'dash_renderer>=0.14.1',
    ],
    url='https://github.com/pikhovkin/dj-plotly-dash',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 1.9',
        'Framework :: Django :: 1.10',
        'Framework :: Django :: 1.11',
        'Framework :: Django :: 2.0',
        'Framework :: Django :: 2.1',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'Intended Audience :: Financial and Insurance Industry',
        'Intended Audience :: Healthcare Industry',
        'Intended Audience :: Manufacturing',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Database :: Front-Ends',
        'Topic :: Office/Business :: Financial :: Spreadsheet',
        'Topic :: Scientific/Engineering :: Visualization',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Widget Sets'
    ]
)
