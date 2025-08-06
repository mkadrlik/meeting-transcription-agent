#!/usr/bin/env python3
"""
Setup script for Meeting Transcription Agent MCP Server
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="meeting-transcription-agent",
    version="0.1.0",
    author="Meeting Transcription Agent",
    author_email="",
    description="MCP Server for meeting transcription with audio capture",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/meeting-transcription-agent",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Multimedia :: Sound/Audio :: Capture/Recording",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
        "enhanced": [
            "scipy>=1.10.0",
            "librosa>=0.10.0",
            "webrtcvad>=2.0.10",
        ],
    },
    entry_points={
        "console_scripts": [
            "meeting-transcription-agent=main:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)