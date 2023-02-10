import sys

if sys.version_info < (3, 8, 0):
    print("Python 3.8+ is required")
    exit(1)
import io  # noqa E402
import os  # noqa E402
from setuptools import find_packages, setup  # noqa E402
from pathlib import Path  # noqa E402
from typing import List  # noqa E402
import ast  # noqa E402
import re  # noqa E402

CURDIR = Path(__file__).parent

EXCLUDE_FROM_PACKAGES = ["tests"]


with io.open(os.path.join(CURDIR, "README.md"), "r", encoding="utf-8") as f:
    README = f.read()


with io.open(os.path.join(CURDIR, "requirements.txt"), "r", encoding="utf-8") as f:
    required = f.read().splitlines()

setup(
    name="stcli",
    version="1.0.0",
    author="antb123 on stellar-public",
    author_email="",
    description="stcli - a repl command line crypto wallet for stellar that is simple and all in one file",
    long_description=README,
    long_description_content_type="text/markdown",
    url="http://github.com/antb123/stcli",
    packages=find_packages(exclude=EXCLUDE_FROM_PACKAGES),
    include_package_data=True,
    keywords=[],
    scripts=[],
    entry_points={"console_scripts": ["stcli = stcli.stcli:main"]},
    extras_require={},
    zip_safe=False,
    python_requires=">=3.8",
    install_requires=required,
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.8",
    ],
    license="MIT",
)
