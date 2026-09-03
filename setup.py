"""Setup configuration for NATO ASCII Browser."""
from setuptools import setup, find_packages

setup(
    name="nato-browser",
    version="0.5.0",
    description="ASCII Web Browser for the Terminal",
    author="NATO Browser Team",
    python_requires=">=3.10",
    packages=find_packages(),
    install_requires=[
        "requests",
        "pyfiglet",
        "textual",
        "httpx",
        "pillow",  # optional but recommended for image rendering
    ],
    extras_require={
        "video": ["av"],
    },
    entry_points={
        "console_scripts": [
            "nato-browser=nato_browser.main:run_default",
            "nato-browser-tui=nato_browser.main:run_textual",
            "nato-browser-gui=nato_browser.main:run_tkinter",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.14",
    ],
)
