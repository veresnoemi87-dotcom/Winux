import os
import requests

class WinuxKernel:
    def __init__(self, root_dir: str):
        self.root_dir = os.path.abspath(root_dir)

    # -----------------------------
    # INTERNAL: sandbox path resolver
    # -----------------------------
    def _sandbox(self, path: str) -> str:
        if not path:
            path = "."
        if os.path.isabs(path):
            full = os.path.abspath(os.path.join(self.root_dir, path.lstrip("/")))
        else:
            full = os.path.abspath(os.path.join(os.getcwd(), path))

        if not full.startswith(self.root_dir):
            raise PermissionError("Outside sandbox")
        return full

    # -----------------------------
    # FILESYSTEM HELPERS
    # -----------------------------
    def write_file(self, path: str, text: str):
        full = self._sandbox(path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(text)

    def append_file(self, path: str, text: str):
        full = self._sandbox(path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "a", encoding="utf-8") as f:
            f.write(text + "\n")

    def read_file(self, path: str) -> str:
        full = self._sandbox(path)
        with open(full, "r", encoding="utf-8") as f:
            return f.read()

    def exists(self, path: str) -> bool:
        try:
            full = self._sandbox(path)
        except PermissionError:
            return False
        return os.path.exists(full)

    def list_all(self, path: str = "."):
        full = self._sandbox(path)
        if not os.path.isdir(full):
            raise NotADirectoryError(path)

        dirs = []
        files = []
        for entry in os.listdir(full):
            p = os.path.join(full, entry)
            if os.path.isdir(p):
                dirs.append(entry + "/")
            else:
                files.append(entry)
        return sorted(dirs) + sorted(files)

    def cd(self, path: str):
        full = self._sandbox(path)
        if not os.path.isdir(full):
            raise FileNotFoundError(path)
        os.chdir(full)

    # -----------------------------
    # NETWORK HELPERS (requests)
    # -----------------------------
    def http_get_text(self, url: str) -> str:
        r = requests.get(url)
        r.raise_for_status()
        return r.text

    def http_download(self, url: str, dest_path: str):
        full = self._sandbox(dest_path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        r = requests.get(url)
        r.raise_for_status()
        with open(full, "wb") as f:
            f.write(r.content)
