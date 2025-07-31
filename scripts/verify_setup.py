#!/usr/bin/env python3
"""
Development environment verification script.

This script verifies that the development environment is properly set up
and all required components are working correctly.
"""
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple


def check_python_version() -> Tuple[bool, str]:
    """Check Python version compatibility."""
    version = sys.version_info
    min_version = (3, 11)

    if version >= min_version:
        return (
            True,
            f"✅ Python {version.major}.{version.minor}.{version.micro} (>= 3.11)",
        )
    else:
        return (
            False,
            f"❌ Python {version.major}.{version.minor}.{version.micro} (< 3.11)",
        )


def check_uv_installation() -> Tuple[bool, str]:
    """Check if uv is installed and working."""
    try:
        result = subprocess.run(
            ["uv", "--version"], capture_output=True, text=True, check=True
        )
        version = result.stdout.strip()
        return True, f"✅ {version}"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False, "❌ uv not found or not working"


def check_required_packages() -> Tuple[bool, str]:
    """Check if required packages are installed."""
    required_packages = [
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "redis",
        "pydantic",
        "pydantic-settings",
        "pytest",
        "black",
        "isort",
        "flake8",
        "mypy",
        "pre-commit",
    ]

    missing_packages = []

    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing_packages.append(package)

    if not missing_packages:
        return True, f"✅ All {len(required_packages)} required packages installed"
    else:
        return False, f"❌ Missing packages: {', '.join(missing_packages)}"


def check_directory_structure() -> Tuple[bool, str]:
    """Check if required directories exist."""
    project_root = Path(__file__).parent.parent
    required_dirs = [
        "app",
        "app/api",
        "app/api/v1",
        "app/core",
        "app/dependencies",
        "app/middleware",
        "app/models",
        "app/routers",
        "app/services",
        "app/utils",
        "app/validators",
        "tests",
        "tests/unit",
        "tests/integration",
        "tests/e2e",
        "scripts",
        "docs",
        "k8s",
    ]

    missing_dirs = []
    for dir_path in required_dirs:
        if not (project_root / dir_path).exists():
            missing_dirs.append(dir_path)

    if not missing_dirs:
        return True, f"✅ All {len(required_dirs)} required directories exist"
    else:
        return False, f"❌ Missing directories: {', '.join(missing_dirs)}"


def check_init_files() -> Tuple[bool, str]:
    """Check if __init__.py files exist in Python packages."""
    project_root = Path(__file__).parent.parent
    python_dirs = [
        "app",
        "app/api",
        "app/api/v1",
        "app/core",
        "app/dependencies",
        "app/middleware",
        "app/models",
        "app/routers",
        "app/services",
        "app/utils",
        "app/validators",
        "tests",
        "tests/unit",
        "tests/integration",
        "tests/e2e",
    ]

    missing_init_files = []
    for dir_path in python_dirs:
        init_file = project_root / dir_path / "__init__.py"
        if not init_file.exists():
            missing_init_files.append(f"{dir_path}/__init__.py")

    if not missing_init_files:
        return True, f"✅ All {len(python_dirs)} Python packages have __init__.py files"
    else:
        return False, f"❌ Missing __init__.py files: {', '.join(missing_init_files)}"


def check_configuration_files() -> Tuple[bool, str]:
    """Check if configuration files exist."""
    project_root = Path(__file__).parent.parent
    config_files = [
        "pyproject.toml",
        "pytest.ini",
        ".coveragerc",
        ".pre-commit-config.yaml",
        ".env.example",
        "Makefile",
    ]

    missing_files = []
    for file_path in config_files:
        if not (project_root / file_path).exists():
            missing_files.append(file_path)

    if not missing_files:
        return True, f"✅ All {len(config_files)} configuration files exist"
    else:
        return False, f"❌ Missing configuration files: {', '.join(missing_files)}"


def check_pre_commit_hooks() -> Tuple[bool, str]:
    """Check if pre-commit hooks are installed."""
    git_hooks_dir = Path(__file__).parent.parent / ".git" / "hooks"

    if not git_hooks_dir.exists():
        return False, "❌ Git hooks directory not found (not a git repository)"

    pre_commit_hook = git_hooks_dir / "pre-commit"
    if not pre_commit_hook.exists():
        return False, "❌ Pre-commit hook not installed"

    if not os.access(pre_commit_hook, os.X_OK):
        return False, "❌ Pre-commit hook not executable"

    return True, "✅ Pre-commit hooks installed and executable"


def check_import_structure() -> Tuple[bool, str]:
    """Test basic import structure."""
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))

    try:
        import app
        import app.api
        import app.core
        import app.models
        import app.services
        import app.utils
        import tests

        return True, "✅ Basic import structure works"
    except ImportError as e:
        return False, f"❌ Import error: {e}"
    finally:
        sys.path.pop(0)


def check_fastapi_app() -> Tuple[bool, str]:
    """Test FastAPI app creation."""
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))

    try:
        from app.main import app

        if app is None:
            return False, "❌ FastAPI app is None"

        if not hasattr(app, "title"):
            return False, "❌ FastAPI app missing title attribute"

        return True, f"✅ FastAPI app created successfully: {app.title}"
    except Exception as e:
        return False, f"❌ FastAPI app creation failed: {e}"
    finally:
        sys.path.pop(0)


def check_test_environment() -> Tuple[bool, str]:
    """Test test environment setup."""
    try:
        result = subprocess.run(
            ["uv", "run", "pytest", "--version"],
            capture_output=True,
            text=True,
            check=True,
        )
        return True, f"✅ Test environment working: {result.stdout.strip()}"
    except subprocess.CalledProcessError as e:
        return False, f"❌ Test environment failed: {e}"


def check_linting_tools() -> Tuple[bool, str]:
    """Test linting tools."""
    tools = [
        ("black", ["uv", "run", "black", "--version"]),
        ("isort", ["uv", "run", "isort", "--version"]),
        ("flake8", ["uv", "run", "flake8", "--version"]),
        ("mypy", ["uv", "run", "mypy", "--version"]),
    ]

    working_tools = []
    failed_tools = []

    for tool_name, command in tools:
        try:
            subprocess.run(command, capture_output=True, check=True)
            working_tools.append(tool_name)
        except subprocess.CalledProcessError:
            failed_tools.append(tool_name)

    if not failed_tools:
        return True, f"✅ All linting tools working: {', '.join(working_tools)}"
    else:
        return False, f"❌ Failed tools: {', '.join(failed_tools)}"


def main():
    """Run all verification checks."""
    print("🔍 Verifying Development Environment...")
    print("=" * 60)

    checks = [
        ("Python Version", check_python_version),
        ("UV Installation", check_uv_installation),
        ("Required Packages", check_required_packages),
        ("Directory Structure", check_directory_structure),
        ("__init__.py Files", check_init_files),
        ("Configuration Files", check_configuration_files),
        ("Pre-commit Hooks", check_pre_commit_hooks),
        ("Import Structure", check_import_structure),
        ("FastAPI App", check_fastapi_app),
        ("Test Environment", check_test_environment),
        ("Linting Tools", check_linting_tools),
    ]

    all_passed = True
    results = []

    for check_name, check_func in checks:
        print(f"\n📋 {check_name}:")
        passed, message = check_func()
        print(f"   {message}")
        results.append((check_name, passed, message))
        if not passed:
            all_passed = False

    print("\n" + "=" * 60)
    print("📊 SUMMARY:")

    passed_count = sum(1 for _, passed, _ in results if passed)
    total_count = len(results)

    print(f"✅ Passed: {passed_count}/{total_count}")
    print(f"❌ Failed: {total_count - passed_count}/{total_count}")

    if all_passed:
        print("\n🎉 All checks passed! Development environment is ready.")
        print("\n🚀 Next steps:")
        print("   1. Copy .env.example to .env and configure your settings")
        print("   2. Run 'make setup' to complete the setup")
        print("   3. Run 'make test' to verify everything works")
        print("   4. Run 'make run' to start the development server")
        sys.exit(0)
    else:
        print("\n⚠️  Some checks failed. Please fix the issues above.")
        print("\n🔧 Common fixes:")
        print("   1. Run 'uv sync' to install dependencies")
        print("   2. Run 'make setup' to complete the setup")
        print("   3. Check the error messages above for specific issues")
        sys.exit(1)


if __name__ == "__main__":
    main()
