import subprocess
import sys
import os

def run_scripts(script_names):
    """
    Runs a list of Python scripts sequentially.  Handles errors,
    captures output, and prints informative messages to the console.

    Args:
        script_names (list): A list of strings, where each string is the
                            name of a Python script (e.g., "script1.py").
                            The scripts are assumed to be in the same
                            directory as this script.
    """
    if not script_names:
        print("Error: No scripts provided to run.")
        sys.exit(1)  # Use sys.exit for a cleaner exit

    print(f"Running the following scripts: {', '.join(script_names)}")

    for script_name in script_names:
        # Check if the script name ends with .py
        if not script_name.endswith(".py"):
            print(f"Error: Script name '{script_name}' must end with '.py'. Skipping.")
            continue  # Move to the next script in the list

        # Construct the full path to the script.  This is crucial!
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), script_name)

        # Check if the script file exists
        if not os.path.exists(script_path):
            print(f"Error: Script not found at '{script_path}'. Skipping.")
            continue  # Move to the next script

        print(f"\nRunning script: {script_name} (Full path: {script_path})")
        try:
            # Use subprocess.run for better control and error handling
            #  * capture_output=True:  Capture stdout and stderr
            #  * text=True: Decode the output as text
            #  * check=True:  Raise a CalledProcessError if the script fails
            result = subprocess.run(
                ["python", script_path],  # Use the full path
                capture_output=True,
                text=True,
                check=True,  # This will raise an exception on non-zero exit
            )

            # Print the script's output
            print(f"Output from {script_name}:")
            print(result.stdout)

            # Print the script's exit code
            print(f"Exit code for {script_name}: {result.returncode}")

        except subprocess.CalledProcessError as e:
            # Handle errors from the subprocess
            print(f"Error running script '{script_name}':")
            print(f"  Return code: {e.returncode}")
            print(f"  Output (stderr):\n{e.stderr}")  # Print stderr
            print(f"  Output (stdout):\n{e.stdout}")
            #  Don't exit, just continue to the next script
            continue
        except FileNotFoundError:
            print(f"Error: Python interpreter not found.  Make sure Python is in your PATH.")
            sys.exit(1) # Exit if python itself isn't found
        except Exception as e:
            # Handle other exceptions (e.g., if the script itself has an error)
            print(f"An unexpected error occurred while running script '{script_name}': {e}")
            # Don't exit, continue to the next script.
            continue

    print("\nFinished running all scripts.")



if __name__ == "__main__":
    # Example usage:
    # List the names of the scripts you want to run *in order*.
    scripts_to_run = ["script1.py", "script2.py", "script3.py", "update_postgres_schema.py", "update_all_user_columns.py"]
    # Create dummy scripts if they don't exist
    for script_name in scripts_to_run:
        if not os.path.exists(script_name):
            with open(script_name, "w") as f:
                f.write(f"# This is a dummy script: {script_name}\n")
                f.write("print(f'Running {__file__}')\n")
                f.write("print('Hello from the script!')\n")
    run_scripts(scripts_to_run)
    # After this script is done running, it will attempt to execute
    # the scripts listed in `scripts_to_run`.  Make sure those scripts
    # exist in the same directory as this script, or provide the full
    # path to each script.