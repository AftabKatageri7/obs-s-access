from setuptools import setup, find_packages

setup(
    name="github-collab-manager",
    version="0.1.0",
    description="Manage GitHub repository collaborators using YAML-based team definitions",
    author="observability-s",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "PyGithub>=2.1.0",
        "PyYAML>=6.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-mock>=3.10",
        ],
    },
    entry_points={
        "console_scripts": [
            "github-collab-manager=github_collab_manager.cli:main",
        ],
    },
)

# Made with Bob
