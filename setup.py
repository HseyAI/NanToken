from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="nantoken",
    version="0.1.0",
    author="NanToken Team",
    author_email="hello@nantoken.dev",
    description="Intelligent LLM Token Tracker - track usage, estimate costs, plan tasks",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/nantoken",
    project_urls={
        "Bug Tracker": "https://github.com/yourusername/nantoken/issues",
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "tiktoken>=0.5.0",
        "openai>=1.12.0",
        "google-generativeai>=0.3.0",
        "pyyaml>=6.0",
        "tabulate>=0.9.0",
        "colorama>=0.4.6",
        "requests>=2.31.0",
        "anthropic>=0.18.0",
        "mcp[cli]>=1.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "nantoken=nantoken.cli:main",
            "nantoken-shell=nantoken.shell:main",
            "nantoken-ask=ask:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)