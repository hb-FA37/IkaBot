from setuptools import setup, find_packages

with open("requirements.txt") as file_:
    requirements = file_.readlines()

with open("requirements.test.txt") as file_:
    test_requirements = file_.readlines()

extras = {
    "test": test_requirements,
}

setup(
    name="ikabot",
    version="0.1.0",
    discription="Simple Discord bot and utilities",
    packages=find_packages("src"),
    package_dir={"": "src"},
    python_requires=">=3.6",
    install_requires=requirements,
    test_require=test_requirements,
)
