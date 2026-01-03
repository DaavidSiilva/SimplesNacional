from setuptools import setup, find_packages

setup(
    name="simplesnacional",
    version="0.1.0",
    description="Biblioteca e CLI para consulta e atualização da base de dados do Simples Nacional.",
    author="David Silva",
    author_email="david.emery.silva@gmail.com",
    packages=find_packages(),
    install_requires=[
        "requests",
        "beautifulsoup4",
        "rich"
    ],
    entry_points={
        "console_scripts": [
            "simplesnacional=simplesnacional:cli",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)
