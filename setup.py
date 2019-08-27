import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="thruster",
    version="0.0.8",
    author="Akshay Takkar",
    author_email="akshay.takkar101@gmail.com",
    description="ASGI compatible HTTP/2 web server",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/blackblood/Thruster",
    packages=setuptools.find_packages(),
    entry_points = {
        'console_scripts': ['thruster=thruster.server:main'],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)