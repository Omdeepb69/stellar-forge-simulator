import setuptools
import os

_PROJECT_NAME = "StellarForgeSimulator"
_PROJECT_VERSION = "0.1.0"  # Initial development version
_PROJECT_AUTHOR = "Omdeep Borkar"
_PROJECT_AUTHOR_EMAIL = "omdeeborkar@gmail.com"
_PROJECT_URL = "https://github.com/Omdeepb69/Stellar Forge Simulator"
_PROJECT_DESCRIPTION = (
    "Develop an endless 2D space exploration sandbox featuring a "
    "player-controlled rocket navigating procedurally generated star systems. "
    "Utilizes physics simulations for celestial body interactions and simple "
    "ML techniques to create diverse planetary characteristics."
)

# Try to read the README file for the long description
try:
    with open("README.md", "r", encoding="utf-8") as fh:
        _LONG_DESCRIPTION = fh.read()
    _LONG_DESCRIPTION_CONTENT_TYPE = "text/markdown"
except FileNotFoundError:
    _LONG_DESCRIPTION = _PROJECT_DESCRIPTION
    _LONG_DESCRIPTION_CONTENT_TYPE = "text/plain"


_INSTALL_REQUIRES = [
    "pygame>=2.1.0",  # Specify a reasonable minimum version
    "numpy>=1.20.0",  # Specify a reasonable minimum version
    "scikit-learn>=1.0.0",  # Specify a reasonable minimum version
]

_PYTHON_REQUIRES = ">=3.8" # Specify minimum Python version


setuptools.setup(
    name=_PROJECT_NAME,
    version=_PROJECT_VERSION,
    author=_PROJECT_AUTHOR,
    author_email=_PROJECT_AUTHOR_EMAIL,
    description=_PROJECT_DESCRIPTION,
    long_description=_LONG_DESCRIPTION,
    long_description_content_type=_LONG_DESCRIPTION_CONTENT_TYPE,
    url=_PROJECT_URL,
    packages=setuptools.find_packages(where="src"), # Assumes code is in 'src' directory
    package_dir={"": "src"}, # Tells setuptools packages are under src
    classifiers=[
        "Development Status :: 3 - Alpha",  # Or 4 - Beta, 5 - Production/Stable
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License", # Choose an appropriate license
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Games/Entertainment :: Simulation",
        "Topic :: Scientific/Engineering :: Astronomy",
        "Topic :: Scientific/Engineering :: Physics",
    ],
    python_requires=_PYTHON_REQUIRES,
    install_requires=_INSTALL_REQUIRES,
    # Add entry points if you have command-line scripts
    # entry_points={
    #     'console_scripts': [
    #         'stellar-forge=stellar_forge_simulator.main:run_game', # Example entry point
    #     ],
    # },
    # Include data files if needed (e.g., assets, models)
    # package_data={
    #     'your_package_name': ['assets/*', 'models/*.pkl'],
    # },
    # include_package_data=True, # Often used with MANIFEST.in
    project_urls={ # Optional: Add other relevant URLs
        "Bug Tracker": f"{_PROJECT_URL}/issues",
        "Source Code": _PROJECT_URL,
    },
    license="MIT", # Match the classifier
    keywords="pygame simulation space sandbox procedural generation physics machine-learning game",
)