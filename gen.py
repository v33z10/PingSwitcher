import subprocess
import sys

def build():
    print("1. Installing PyInstaller and Pillow...")
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller", "pillow"], check=True)

    print("2. Building EXE...")
    # Используем sys.executable -m PyInstaller, чтобы обойти проблему с PATH
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconsole",        
        "--onefile",          
        "--icon=icon.ico",    
        "--add-data", "icon.ico;.", 
        "PingSwitcher.py"
    ]
    
    # Запускаем сборку
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("\n=============================================")
        print("Done! Your EXE is in the 'dist' folder.")
        print("=============================================")
    else:
        print("\n[ERROR] Build failed. Please check the output above.")

if __name__ == "__main__":
    build()