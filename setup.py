"""Setup script for TeslaOnTarget package."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="teslaontarget",
    version="1.0.0",
    author="TeslaOnTarget Contributors",
    author_email="",
    description="Bridge Tesla vehicles with TAK servers for real-time position tracking",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/joshuafuller/TeslaOnTarget",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.7",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "teslaontarget=teslaontarget.cli:main",
            "tesla-auth=teslaontarget.auth:main",
        ],
    },
    include_package_data=True,
    package_data={
        "teslaontarget": ["config.py.template"],
    },
)