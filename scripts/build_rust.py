import os
import platform
import shutil
import subprocess
import glob

# 1. Define source and target directories
PY_RUST_UTILS_DIR = "py_rust_utils"
TARGET_DIR = "src"

# Ensure target directory exists
os.makedirs(TARGET_DIR, exist_ok=True)

def get_library_filenames():
    """Determines the source library filename pattern and target library filename based on the OS."""
    system = platform.system()
    
    # Source filename pattern (actual name produced by cargo build)
    # Based on diagnostic output: 'libpy_rust_utils.so' was found on Linux.
    # The Cargo.toml for py_rust_utils has [lib] name = "py_rust_utils_module".
    # It seems the build process might simplify this to "py_rust_utils" for the actual file.
    if system == "Linux":
        source_filename_pattern = "libpy_rust_utils.so" 
        target_filename = "py_rust_utils.so"
    elif system == "Windows":
        # Assuming a similar simplification might occur, or it uses the direct name.
        # If [lib] name is "py_rust_utils_module", Cargo usually outputs "py_rust_utils_module.dll".
        # Let's assume it's "py_rust_utils.dll" to match the Linux finding's simplification.
        # If this fails, we'd check actual output on Windows.
        source_filename_pattern = "py_rust_utils.dll"
        target_filename = "py_rust_utils.dll"
    elif system == "Darwin": # macOS
        # Cargo typically produces lib<name>.dylib.
        # Using "libpy_rust_utils.dylib" similar to Linux pattern.
        source_filename_pattern = "libpy_rust_utils.dylib"
        target_filename = "py_rust_utils.so" # Target name as requested
    else:
        raise OSError(f"Unsupported operating system: {system}")
    return source_filename_pattern, target_filename

def find_compiled_library(search_dir, filename_pattern):
    """Searches for the compiled library in a directory."""
    # Search recursively for the library file.
    for root, _, files in os.walk(search_dir):
        if filename_pattern in files:
            # Prefer release builds if found in a path containing "release"
            if "release" in root.lower():
                return os.path.join(root, filename_pattern)
    # Fallback if not found in a "release" path explicitly (e.g. if search_dir is already specific)
    for root, _, files in os.walk(search_dir):
        if filename_pattern in files:
            return os.path.join(root, filename_pattern)
    return None

def main():
    source_lib_filename_pattern, target_lib_filename = get_library_filenames()

    compiled_lib_target_path = os.path.join(TARGET_DIR, target_lib_filename)

    print(f"Rust project directory: {os.path.abspath(PY_RUST_UTILS_DIR)}")
    print(f"Target directory for compiled library: {os.path.abspath(TARGET_DIR)}")
    print(f"Searching for source library pattern: '{source_lib_filename_pattern}'")
    print(f"Target library name (destination): '{target_lib_filename}'")
    print(f"Full target path: {os.path.abspath(compiled_lib_target_path)}")

    manifest_path = os.path.join(PY_RUST_UTILS_DIR, "Cargo.toml")
    print(f"\nBuilding Rust project '{PY_RUST_UTILS_DIR}' using manifest: {manifest_path}...")
    try:
        process = subprocess.run(
            ["cargo", "build", "--release", "--manifest-path", manifest_path],
            check=True,
            capture_output=True,
            text=True
        )
        print("Cargo build successful.")
        if process.stdout:
            print("Cargo stdout:\n", process.stdout)
        if process.stderr:
            print("Cargo stderr:\n", process.stderr)
            
    except subprocess.CalledProcessError as e:
        print(f"Error during cargo build: {e}")
        print(f"Cargo stdout:\n{e.stdout}")
        print(f"Cargo stderr:\n{e.stderr}")
        return
    except FileNotFoundError:
        print("Error: 'cargo' command not found. Please ensure Rust is installed and in your PATH.")
        return

    search_dir = os.path.join(PY_RUST_UTILS_DIR, "target")
    print(f"\nSearching for compiled library '{source_lib_filename_pattern}' in '{search_dir}'...")
    
    compiled_lib_source_path = find_compiled_library(search_dir, source_lib_filename_pattern)

    if not compiled_lib_source_path:
        print(f"Error: Compiled library pattern '{source_lib_filename_pattern}' not found in '{search_dir}'.")
        print("Please check the build output and the 'target' directory structure.")
        # Diagnostic: List contents of likely locations
        primary_search_path = os.path.join(PY_RUST_UTILS_DIR, "target", "release")
        if os.path.exists(primary_search_path):
            print(f"Contents of '{primary_search_path}': {os.listdir(primary_search_path)}")
        else:
            print(f"Directory '{primary_search_path}' does not exist.")
        
        # Check if Cargo built in a target-specific directory (e.g. target/<triple>/release)
        # This is a common case if a specific target is set via env vars or .cargo/config.toml
        for item in os.listdir(search_dir) if os.path.exists(search_dir) else []:
            potential_target_triple_dir = os.path.join(search_dir, item, "release")
            if os.path.isdir(potential_target_triple_dir) and item != "release": # Avoid re-listing primary_search_path
                print(f"Also checking in '{potential_target_triple_dir}'...")
                if os.path.exists(potential_target_triple_dir):
                     print(f"Contents of '{potential_target_triple_dir}': {os.listdir(potential_target_triple_dir)}")
        return

    print(f"Found compiled library at: {compiled_lib_source_path}")

    print(f"\nCopying '{compiled_lib_source_path}' to '{compiled_lib_target_path}'...")
    try:
        shutil.copy2(compiled_lib_source_path, compiled_lib_target_path)
        print("Library copied successfully.")
    except FileNotFoundError:
        print(f"Error: Source library file not found at '{compiled_lib_source_path}' during copy. This is unexpected after find_compiled_library succeeded.")
        return
    except Exception as e:
        print(f"Error copying library: {e}")
        return
        
    print("\nBuild process completed.")

if __name__ == "__main__":
    main()
