from setuptools import setup, find_packages

setup(
    name="tournament_core",
    version="1.0.0",
    packages=find_packages(),
    description="A rating system for doubles disc golf leagues",
    author="Disc Golf League",
    python_requires=">=3.6",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
