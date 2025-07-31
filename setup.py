#!/usr/bin/env python3
"""
FileWallBall Setup Script

This setup script provides traditional Python package installation
for users who prefer pip over uv or need backward compatibility.
"""

from setuptools import find_packages, setup


# Read the README file
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()


# Read requirements from pyproject.toml
def read_requirements():
    requirements = []
    try:
        with open("pyproject.toml", "r", encoding="utf-8") as f:
            lines = f.readlines()
            in_dependencies = False
            for line in lines:
                line = line.strip()
                if line.startswith("dependencies = ["):
                    in_dependencies = True
                    continue
                elif line.startswith("]"):
                    break
                elif in_dependencies and line.startswith('"') and line.endswith('",'):
                    requirements.append(line.strip('",'))
    except FileNotFoundError:
        # Fallback requirements
        requirements = [
            "fastapi>=0.104.1",
            "uvicorn[standard]>=0.24.0",
            "python-multipart>=0.0.6",
            "aiofiles>=23.2.1",
            "python-jose[cryptography]>=3.3.0",
            "passlib[bcrypt]>=1.7.4",
            "python-dotenv>=1.0.0",
            "redis>=5.0.1",
            "kubernetes>=28.1.0",
            "prometheus-client>=0.19.0",
            "prometheus-fastapi-instrumentator>=6.1.0",
            "sqlalchemy>=2.0.23",
            "pymysql>=1.1.0",
            "cryptography>=41.0.7",
            "pillow>=10.2.0",
            "pydantic-settings>=2.1.0",
            "APScheduler>=3.10.4",
            "python-magic>=0.4.27",
            "slowapi>=0.1.9",
            "chardet>=5.2.0",
            "psutil>=5.9.0",
            "structlog>=23.2.0",
            "alembic>=1.16.4",
        ]
    return requirements


def read_dev_requirements():
    dev_requirements = [
        "pytest>=7.0.0",
        "pytest-asyncio>=0.21.0",
        "pytest-cov>=4.0.0",
        "black>=23.0.0",
        "isort>=5.12.0",
        "flake8>=6.0.0",
        "mypy>=1.0.0",
        "pre-commit>=4.2.0",
        "pytest-mock>=3.14.1",
        "httpx>=0.28.1",
        "rich>=13.0.0",
    ]
    return dev_requirements


setup(
    name="filewallball",
    version="0.1.0",
    author="FileWallBall Team",
    author_email="team@filewallball.com",
    description="File Wall Ball - Secure file storage and management system",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/filewallball/api",
    license="MIT",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Filesystems",
    ],
    python_requires=">=3.11",
    install_requires=read_requirements(),
    extras_require={
        "dev": read_dev_requirements(),
        "all": read_requirements() + read_dev_requirements(),
    },
    entry_points={
        "console_scripts": [
            "filewallball=app.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "app": ["*.yaml", "*.yml", "*.json"],
    },
    zip_safe=False,
    keywords="fastapi, file-upload, file-management, api, redis, kubernetes",
    project_urls={
        "Bug Reports": "https://github.com/filewallball/api/issues",
        "Source": "https://github.com/filewallball/api",
        "Documentation": "https://github.com/filewallball/api/tree/main/docs",
    },
)
