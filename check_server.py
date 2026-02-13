import time
import urllib.request
import sys

def check_server():
    url = "http://127.0.0.1:8000/health"
    print(f"Checking {url}...")
    for i in range(10):
        try:
            with urllib.request.urlopen(url) as response:
                if response.status == 200:
                    print("Server is UP!")
                    return
        except Exception as e:
            print(f"Attempt {i+1}: Server not ready ({e})")
            time.sleep(2)
    
    print("Server failed to start.")
    sys.exit(1)

if __name__ == "__main__":
    check_server()
