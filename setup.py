from setuptools import setup, find_packages

setup(
    name="sysdoc",
    version="0.1.0",
    py_modules=["sysdoc", "sysdoc_gui"],
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "PyPDF2>=3.0.0",
    ],
    entry_points={
        "console_scripts": [
            "sysdoc=sysdoc:main",
        ],
    },
)
