from setuptools import setup, find_packages

setup(
    name="data_sources",
    version="0.0.1",
    author="Ansgar Wehrhahn",
    author_email="ansgar.wehrhahn@physics.uu.se",
    packages=find_packages(),
    install_requires=["numpy", "pycurl", "astropy", "astroquery", "pandas", "requests", "pyyaml"]
)
