from setuptools import setup, find_packages

setup(
    name="unifile-by-soniscorett",
    version="2.4.0",
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "unifile=unifile.cli:run_cli",
        ],
    },
)
