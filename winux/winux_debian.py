import os
import sys
import json
from winux_kernel import WinuxKernel

HOSTNAME = "debian-sandbox"
PKG_ID = "wdebian"
BASE_PKG_URL = "https://codyhub.lovable.app/api/get"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.join(SCRIPT_DIR, "root")
USER_DB_DIR = os.path.join(ROOT_DIR, "user")
PKG_DIR = os.path.join(ROOT_DIR, "packages")

os.makedirs(ROOT_DIR, exist_ok=True)
os.makedirs(USER_DB_DIR, exist_ok=True)
os.makedirs(PKG_DIR, exist_ok=True)

kernel = WinuxKernel(ROOT_DIR)

# ==========================================
# AUTH SYSTEM
# ==========================================

def load_password(username: str):
    path = os.path.join(USER_DB_DIR, f"user_{username}.txt")
    if not os.path.exists(path):
        return None
    return open(path, "r", encoding="utf-8").read().strip()

def save_password(username: str, password: str):
    path = os.path.join(USER_DB_DIR, f"user_{username}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(password)

def auth_gateway():
    users = [f for f in os.listdir(USER_DB_DIR) if f.startswith("user_")]
    if not users:
        print("No users found. Creating first account.")
        while True:
            username = input("Username: ").strip()
            if not username:
                continue
            password = input("Password: ")
            save_password(username, password)
            print(f"Account created for {username}")
            return username
    else:
        while True:
            username = input("Username: ").strip()
            if not username:
                continue
            if load_password(username) is None:
                print("No such user.")
                continue
            password = input("Password: ")
            if load_password(username) == password:
                print("Login successful.")
                return username
            print("Wrong password.")

# ==========================================
# PACKAGE INTERPRETER
# ==========================================

def run_package_command(cmd, args):
    pkg_path = os.path.join(PKG_DIR, cmd)

    # Try with .py extension
    if not os.path.exists(pkg_path):
        if os.path.exists(pkg_path + ".py"):
            pkg_path += ".py"
        else:
            return False  # not a package command

    try:
        code = kernel.read_file(pkg_path)
        namespace = {}
        exec(code, namespace)

        if "main" not in namespace:
            print(f"{cmd}: package has no main(args) function")
            return True

        namespace["main"](args)
        return True

    except Exception as e:
        print(f"{cmd}: error running package:", e)
        return True

# ==========================================
# RUN COMMAND (run <pythonfile>)
# ==========================================

def cmd_run(args):
    if not args:
        print("run: missing file operand")
        return

    filename = args[0]
    if not kernel.exists(filename):
        print(f"run: {filename}: No such file")
        return

    try:
        code = kernel.read_file(filename)
        namespace = {}
        exec(code, namespace)
    except Exception as e:
        print("run:", e)

# ==========================================
# COMMAND IMPLEMENTATIONS
# ==========================================

def print_help():
    print("Available commands:")
    print("  help              - show this help")
    print("  clear             - clear screen")
    print("  ls                - list files and folders")
    print("  cd DIR            - change directory")
    print("  pwd               - print working directory")
    print("  cat FILE          - show file contents")
    print("  touch FILE        - create empty file")
    print("  nano FILE         - edit file")
    print("  curl URL          - HTTP GET")
    print("  ping HOST         - fake ping")
    print("  history           - show command history")
    print("  pkg list          - list remote packages")
    print("  pkg install NAME  - download remote file")
    print("  pkg remove NAME   - delete installed file")
    print("  run FILE          - execute a python file")
    print("  logout            - log out")
    print("  exit              - exit simulator")

def cmd_ls(args):
    path = args[0] if args else "."
    try:
        for e in kernel.list_all(path):
            print(e)
    except Exception as e:
        print(f"ls: {e}")

def cmd_cd(args):
    if not args:
        kernel.cd(ROOT_DIR)
        return
    try:
        kernel.cd(args[0])
    except PermissionError:
        print("cd: permission denied")
    except FileNotFoundError:
        print("cd: no such file or directory")
    except Exception as e:
        print(f"cd: {e}")

def cmd_pwd():
    cwd = os.getcwd()
    vpath = cwd.replace(ROOT_DIR, "", 1).replace("\\", "/")
    if vpath == "":
        vpath = "/"
    print(vpath)

def cmd_cat(args):
    if not args:
        print("cat: missing file operand")
        return
    try:
        print(kernel.read_file(args[0]), end="")
    except FileNotFoundError:
        print(f"cat: {args[0]}: No such file or directory")

def cmd_touch(args):
    if not args:
        print("touch: missing file operand")
        return
    kernel.write_file(args[0], "")

def cmd_nano(args):
    if not args:
        print("nano: missing file operand")
        return
    filename = args[0]
    print(f"--- nano: editing {filename} ---")
    print("(existing content below)")
    print("--------------------------------")
    try:
        print(kernel.read_file(filename), end="")
    except:
        pass
    print("--------------------------------")
    print("Type your text. Single dot (.) to save and exit.")
    kernel.write_file(filename, "")
    while True:
        line = input("> ")
        if line == ".":
            break
        kernel.append_file(filename, line)

def cmd_curl(args):
    if not args:
        print("curl: no URL specified")
        return
    try:
        print(kernel.http_get_text(args[0]))
    except Exception as e:
        print(f"curl: {e}")

def cmd_ping(args):
    if not args:
        print("ping: missing host operand")
        return
    host = args[0]
    print(f"PING {host} (127.0.0.1)")
    print(f"64 bytes from {host}: icmp_seq=1 ttl=64 time=0.12 ms")
    print(f"64 bytes from {host}: icmp_seq=2 ttl=64 time=0.14 ms")
    print(f"--- {host} ping statistics ---")
    print("2 packets transmitted, 2 received, 0% packet loss")

def cmd_history(history):
    for i, line in enumerate(history, start=1):
        print(f"{i}  {line}")

# ==========================================
# PACKAGE MANAGER
# ==========================================

def pkg_list():
    url = f"{BASE_PKG_URL}?id={PKG_ID}&list"
    print(f"[pkg] listing remote files for id={PKG_ID}")
    try:
        text = kernel.http_get_text(url)
        data = json.loads(text)
        for f in data.get("files", []):
            print(f"{f['name']}  {f['updated_at']}")
    except Exception as e:
        print(f"pkg list: {e}")

def pkg_install(name: str):
    url = f"{BASE_PKG_URL}?id={PKG_ID}&name={name}"
    dest = os.path.join(PKG_DIR, name)
    print(f"[pkg] installing {name} ...")
    try:
        kernel.http_download(url, dest)
        print(f"[pkg] installed to {dest}")
    except Exception as e:
        print(f"pkg install: {e}")

def pkg_remove(name: str):
    dest = os.path.join(PKG_DIR, name)
    if os.path.exists(dest):
        os.remove(dest)
        print(f"[pkg] removed {name}")
    else:
        print(f"[pkg] {name} not installed")

# ==========================================
# MAIN SHELL LOOP
# ==========================================

def main():
    user = auth_gateway()
    kernel.cd(ROOT_DIR)
    print(f"Linux {HOSTNAME} 5.15.0 x86_64 GNU/Linux")
    print(f"Welcome, {user}!\n")

    history = []

    while True:
        cwd = os.getcwd()
        vpath = cwd.replace(ROOT_DIR, "", 1).replace("\\", "/")
        if vpath == "":
            vpath = "/"

        line = input(f"{user}@{HOSTNAME}:{vpath}$ ").strip()
        if not line:
            continue

        history.append(line)

        parts = line.split()
        cmd = parts[0]
        args = parts[1:]

        # --- pkg command ---
        if cmd == "pkg":
            if not args:
                print("pkg: missing subcommand")
            elif args[0] == "list":
                pkg_list()
            elif args[0] == "install" and len(args) > 1:
                pkg_install(args[1])
            elif args[0] == "remove" and len(args) > 1:
                pkg_remove(args[1])
            else:
                print("pkg: invalid usage")
            continue

        # --- run command ---
        if cmd == "run":
            cmd_run(args)
            continue

        # --- built-in commands ---
        if cmd == "help": print_help()
        elif cmd == "clear": os.system("cls" if os.name == "nt" else "clear")
        elif cmd == "ls": cmd_ls(args)
        elif cmd == "cd": cmd_cd(args)
        elif cmd == "pwd": cmd_pwd()
        elif cmd == "cat": cmd_cat(args)
        elif cmd == "touch": cmd_touch(args)
        elif cmd == "nano": cmd_nano(args)
        elif cmd == "curl": cmd_curl(args)
        elif cmd == "ping": cmd_ping(args)
        elif cmd == "history": cmd_history(history)
        elif cmd == "logout":
            print("logging out...")
            user = auth_gateway()
            kernel.cd(ROOT_DIR)
            history.clear()
        elif cmd == "exit":
            print("logout")
            break
        else:
            # Try package command
            if run_package_command(cmd, args):
                continue

            print(f"bash: {cmd}: command not found")

if __name__ == "__main__":
    main()
