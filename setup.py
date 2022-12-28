import io
from setuptools import setup, find_packages

main_ns = {}
exec(open('dash/version.py').read(), main_ns)  # pylint: disable=exec-used


def read_req_file(req_type):
    with open("requires-{}.txt".format(req_type)) as fp:
        requires = (line.strip() for line in fp)
        return [req for req in requires if req and not req.startswith("#")]


general_requires = [
    'Django>=2.0,<4',
    'plotly>=4.14.1,<5',
    'future',
]

setup(
    name='dj-plotly-dash',
    version=main_ns['__version__'],
    author='Sergei Pikhovkin',
    author_email='s@pikhovkin.ru',
    packages=find_packages(exclude=['tests*']),
    include_package_data=True,
    license='MIT',
    description=('A Python framework for building reactive web-apps. '
                 'Developed by Plotly.'),
    long_description=io.open('README.md', encoding='utf-8').read(),
    long_description_content_type='text/markdown',
    install_requires=[],
    python_requires=">=2.7, !=3.0.*, !=3.1.*, !=3.2.*",
    extras_require={
        'all': general_requires + ['dash_renderer==1.8.3'],
        'no-dash-renderer': general_requires
    },
    entry_points={
        "console_scripts": [
            "dash-generate-components = "
            "dash.development.component_generator:cli",
            "renderer = dash.development.build_process:renderer",
        ],
    },
    url='https://github.com/pikhovkin/dj-plotly-dash',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Dash',
        'Framework :: Django',
        'Framework :: Django :: 2.0',
        'Framework :: Django :: 2.1',
        'Framework :: Django :: 2.2',
        'Framework :: Django :: 3.1',
        'Framework :: Django :: 3.2',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'Intended Audience :: Financial and Insurance Industry',
        'Intended Audience :: Healthcare Industry',
        'Intended Audience :: Manufacturing',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: Database :: Front-Ends',
        'Topic :: Office/Business :: Financial :: Spreadsheet',
        'Topic :: Scientific/Engineering :: Visualization',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Widget Sets'
    ],
)
