import json
import subprocess
import sys
import os
import argparse

RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
RESET = "\033[0m"

def read_uber_config():
    """Reads the 'uber-config' file from the script's directory and returns the parsed JSON."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_file_path = os.path.join(script_dir, "uber-config")
    try:
        with open(config_file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"{RED}Error [1]: Configuration file '{config_file_path}' not found.{RESET}")
        return None
    except json.JSONDecodeError:
        print(f"{RED}Error [2]: Invalid JSON format in '{config_file_path}'.{RESET}")
        return None

def read_project_config(dir_path):
    """Reads the 'uber' file from the specified directory and returns the parsed JSON."""
    config_file_path = os.path.join(dir_path, "uber")
    try:
        with open(config_file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"{RED}Error [7]: Project configuration file '{config_file_path}' not found.{RESET}")
        return None
    except json.JSONDecodeError:
        print(f"{RED}Error [8]: Invalid JSON format in '{config_file_path}'.{RESET}")
        return None

def info_command(project_config):
    """Prints project information from the configuration."""
    if not project_config:
        return

    project_info = project_config.get("project-info", {})
    project_name = project_info.get("project-name", "unknown_project")
    project_source = project_info.get("project-source", "main.py")
    version = project_info.get("version", "1.0")
    venv_configs = project_config.get("venv-configs", {})

    main_venv = None
    for venv_name, venv_config in venv_configs.items():
        if venv_config.get("main", False):
            main_venv = venv_name
            break

    print(f"Project Name: {project_name}")
    print(f"Project Source: {project_source}")
    print(f"Version: {version}")
    if main_venv:
        print(f"Main Venv: {main_venv}")

def run_command(project_config, uber_config, dir_path):
    """Creates virtual environments, installs dependencies, and runs the project."""
    if not project_config:
        return

    venv_configs = project_config.get("venv-configs", {})
    dependencies = project_config.get("dependencies", {})
    project_source = project_config.get("project-info", {}).get("project-source", "main.py")
    ignore = uber_config.get("ignore", {})
    ignore_warnings = ignore.get("warnings", False)
    ignore_errors = ignore.get("errors", False)
    ignore_info = ignore.get("info", False)

    # Create virtual environments
    for venv_name in venv_configs:
        if venv_name == "test-venv":
            if not ignore_info:
                print(f"{YELLOW}INFO: Ignoring creation of 'test-venv'.{RESET}")
            continue

        print(f"Creating virtual environment: {venv_name}")
        try:
            subprocess.run([sys.executable, "-m", "venv", venv_name], check=True)
            print(f"Virtual environment '{venv_name}' created successfully.")
        except subprocess.CalledProcessError as e:
            if not ignore_errors:
                print(f"{RED}Error [3]: Error creating virtual environment '{venv_name}': {e}{RESET}")
            return

    # Install dependencies
    for package, details in dependencies.items():
        venv_name = details.get("venv")
        package_version = details.get("version")

        if venv_name and venv_name in venv_configs:
            pip_executable = os.path.join(venv_name, "bin", "pip") if os.name != 'nt' else os.path.join(venv_name, "Scripts", "pip.exe")

            # Check if package is already installed
            try:
                subprocess.run([pip_executable, "show", package], check=True, capture_output=True)
                if not ignore_info:
                    print(f"{YELLOW}INFO: Dependency '{package}' already installed in '{venv_name}'. Skipping.{RESET}")
                continue
            except subprocess.CalledProcessError:
                pass  # Package is not installed, proceed with installation

            print(f"Installing {package} in {venv_name}")
            install_command = [pip_executable, "install"]
            if package_version:
                install_command.append(f"{package}=={package_version}")
            else:
                install_command.append(package)

            try:
                subprocess.run(install_command, check=True)
                print(f"Successfully installed {package} in {venv_name}.")
            except subprocess.CalledProcessError as e:
                if not ignore_errors:
                    print(f"{RED}Error [4]: Error installing {package} in {venv_name}: {e}{RESET}")
                return

    # Run the project with virtual environment activation
    main_venv = None
    for venv_name, venv_config in venv_configs.items():
        if venv_config.get("main", False):
            main_venv = venv_name
            break

    if main_venv:
        if os.name == 'nt':  # Windows
            activate_script = os.path.join(main_venv, "Scripts", "activate")
            run_command = f'"{activate_script}" && python "{project_source}"'
            try:
                subprocess.run(run_command, shell=True, check=True)
            except subprocess.CalledProcessError as e:
                if not ignore_errors:
                    print(f"{RED}Error [5]: Error running project: {e}{RESET}")
        else:  # macOS or Linux
            activate_script = os.path.join(main_venv, "bin", "activate")
            run_command = f'source "{activate_script}" && python "{project_source}"'
            try:
                subprocess.run(run_command, shell=True, executable='/bin/bash', check=True)
            except subprocess.CalledProcessError as e:
                if not ignore_errors:
                    print(f"{RED}Error [5]: Error running project: {e}{RESET}")
    else:
        if not ignore_errors:
            print(f"{RED}Error [6]: No main virtual environment defined to run the project.{RESET}")

def main():
    parser = argparse.ArgumentParser(description="Process 'uber' project configuration.")
    parser.add_argument("--dir", type=str, default=os.path.dirname(os.path.abspath(__file__)), help="Specify the directory containing 'uber'.")
    subparsers = parser.add_subparsers(dest="command")

    # info subcommand
    subparsers.add_parser("info", help="Display project information.")

    # run subcommand
    subparsers.add_parser("run", help="Create virtual environments, install dependencies, and run the project.")

    args = parser.parse_args()
    dir_path = args.dir
    uber_config = read_uber_config()
    project_config = read_project_config(dir_path)

    if args.command == "info":
        info_command(project_config)
    elif args.command == "run":
        run_command(project_config, uber_config, dir_path)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()