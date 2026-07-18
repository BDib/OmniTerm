import os
import time
import sys
import platform
from winpty import PtyProcess

def run_diagnostic():
    print("--- OmniTerm Diagnostic Tool ---")
    print(f"OS: {platform.system()} {platform.release()} ({platform.version()})")
    print(f"Python Version: {sys.version}")
    print(f"Current Directory: {os.getcwd()}")
    
    log_file = "test.log"
    if os.path.exists(log_file):
        os.remove(log_file)

    try:
        print("\n[1] Attempting to spawn PTY with cmd.exe...")
        # winpty spawns hidden by default as it's a headless process
        proc = PtyProcess.spawn('cmd.exe')
        print("    Success: PTY process spawned.")

        print(f"[2] Executing command: dir > {log_file}")
        # We send \r\n to ensure the command is executed
        proc.write(f"dir > {log_file}\r\n")
        
        print("[3] Waiting 2 seconds for command completion...")
        time.sleep(2)

        print("[4] Checking for output file...")
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                content = f.read()
                line_count = len(content.splitlines())
            print(f"    Success: {log_file} found with {line_count} lines.")
        else:
            print("    Failure: Output file was not created.")

        print("[5] Cleaning up...")
        proc.terminate()
        print("    PTY terminated.")

    except Exception as e:
        print(f"\n[!] ERROR encountered: {str(e)}")
        print("    This usually suggests winpty cannot find the required DLLs or ")
        print("    the Windows Pseudo Console (ConPTY) is being blocked.")

if __name__ == "__main__":
    run_diagnostic()