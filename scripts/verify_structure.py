#!/usr/bin/env python3
"""
Project structure verification script.

This script verifies that the project has the correct directory structure
and all necessary __init__.py files are present.
"""
import sys
from pathlib import Path


def check_directory_structure() -> bool:
    """Check if the project has the correct directory structure."""
    project_root = Path(__file__).parent.parent
    required_dirs = [
        "app",
        "app/api",
        "app/api/v1",
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
        "docs",
        "k8s",
        "scripts",
    ]

    missing_dirs = []
    for dir_path in required_dirs:
        full_path = project_root / dir_path
        if not full_path.exists():
            missing_dirs.append(dir_path)

    if missing_dirs:
        print(f"❌ Missing directories: {missing_dirs}")
        return False

    print("✅ All required directories exist")
    return True


def check_init_files() -> bool:
    """Check if all Python packages have __init__.py files."""
    project_root = Path(__file__).parent.parent

    # Directories that should have __init__.py files
    python_dirs = [
        "app",
        "app/api",
        "app/api/v1",
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

    if missing_init_files:
        print(f"❌ Missing __init__.py files: {missing_init_files}")
        return False

    print("✅ All Python packages have __init__.py files")
    return True


def check_import_structure() -> bool:
    """Test basic import structure."""
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))

    try:
        # Test basic imports
        import app  # noqa: F401
        import app.api  # noqa: F401
        import app.models  # noqa: F401
        import app.services  # noqa: F401
        import app.utils  # noqa: F401
        import tests  # noqa: F401

        print("✅ Basic import structure works")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    finally:
        sys.path.pop(0)


def main() -> None:
    """Run all structure verification checks."""
    print("🔍 Verifying project structure...")
    print("-" * 50)

    checks = [
        ("Directory Structure", check_directory_structure),
        ("__init__.py Files", check_init_files),
        ("Import Structure", check_import_structure),
    ]

    all_passed = True
    for check_name, check_func in checks:
        print(f"\n📋 {check_name}:")
        if not check_func():
            all_passed = False

    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All structure checks passed!")
        sys.exit(0)
    else:
        print("❌ Some structure checks failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
