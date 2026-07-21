import os
import time
from winpty import PtyProcess

def test_line_endings():
    log_file = "nudge.log"
    if os.path.exists(log_file):
        os.remove(log_file)
    
    proc = PtyProcess.spawn('cmd.exe')
    time.sleep(1) # Wait for cmd to stabilize
    
    # We test both common Windows line endings and a flush command
    print("Testing CRLF...")
    proc.write("echo 'worked' > nudge.log\r\n")
    
    time.sleep(2)
    if os.path.exists(log_file):
        print("!!! SUCCESS: CRLF (\r\n) worked.")
        return

    print("Testing CR only...")
    proc.write("echo 'worked' > nudge.log\r")
    
    time.sleep(2)
    if os.path.exists(log_file):
        print("!!! SUCCESS: CR (\r) worked.")
    else:
        print("FAILURE: Still no file created.")

    proc.terminate()

if __name__ == "__main__":
    test_line_endings()