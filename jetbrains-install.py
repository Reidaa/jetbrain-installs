import os
import shutil
import sys
from typing import Optional

import colorama
import requests
from tqdm import tqdm

product_codes = {
    "idea-ult": "UI",  # IntelliJ IDEA Ultimate
    "idea-com": "IC",  # IntelliJ IDEA Community
    "idea-edu": "IE",  # IntelliJ IDEA Educational
    "pycharm-pro": "PY",  # PyCharm Professional
    "pycharm-com": "PC",  # PyCharm Community
    "pycharm-edu": "PE",  # PyCharm Educational
    "phpstorm": "PS",
    "webstorm": "ws",
    "rubymine": "RM",
    "appcode": "OC",
    "clion": "CL",
    "goland": "GO",
    "datagrip": "DG",
    "rider": "RD",
    "android-studio": "AI",
}


class ColorPrint:
    @staticmethod
    def print_success(message, end: str = "\n"):
        print(f"{colorama.Fore.GREEN}{message}{colorama.Style.RESET_ALL}", end=end)

    @staticmethod
    def print_fail(message, end: str = "\n"):
        print(f"{colorama.Fore.RED}{message}{colorama.Style.RESET_ALL}", end=end)


class Installer:
    def __init__(self, url: str):
        self.url = url
        self.filename: str = ""
        self.dirname: str = ""

    def run(self):
        self.download()
        self.install()
        self.cleanup()

    def install(self):
        status = f"Installing {self.filename}"
        print(status, end=" ", flush=True)
        ColorPrint.print_success("done")
        return

    def download(self):
        if self.url.find('/'):
            self.filename = self.url.rsplit('/', 1)[1]
        status = f"Downloading {self.filename}:"
        print(f"\r{status}", end=" ")

        response = requests.get(self.url, allow_redirects=True, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024 * 4
        progress_bar = tqdm(total=total_size, desc=status, unit_scale=True, file=sys.stdout, leave=False)
        with open(self.filename, 'wb') as handle:
            for data in response.iter_content(block_size):
                progress_bar.update(len(data))
                handle.write(data)
        progress_bar.close()

        if total_size != 0 and progress_bar.n != total_size:
            print(f"\r{status}", end=" ")
            ColorPrint.print_fail("fail")
        else:
            print(f"\r{status}", end=" ")
            ColorPrint.print_success("done")
        return

    def cleanup(self):
        removeFile(self.filename)
        removeDir(self.dirname)


def removeDir(dirname: str):
    status = f"Removing {dirname}:"
    print(status, end=" ", flush=False)

    try:
        shutil.rmtree(dirname)
    except OSError as e:
        ColorPrint.print_fail("fail")
        print(f"\rError: {e.filename} - {e.strerror}.", file=sys.stderr)
    else:
        ColorPrint.print_success("done")
    return


def removeFile(filename: str):
    status = f"Removing {filename}:"
    print(status, end=" ", flush=True)

    try:
        os.remove(filename)
    except OSError as e:
        ColorPrint.print_fail("fail")
        print(f"\rError: {e.filename} - {e.strerror}.", file=sys.stderr)
    else:
        ColorPrint.print_success("done")
    return


def checkAdminPrivilege() -> bool:
    status = "checking admin privilege:"
    print(status, end=" ", flush=True)

    if os.getuid() == 0:
        print("granted")
        return True
    else:
        print("not granted")
        return False


def getLatestURL(product_code: str, platform: str = "linux") -> Optional[str]:
    status = "Finding the latest download link:"

    print(status, end=" ", flush=True)
    r = requests.get(f"https://data.services.jetbrains.com//products/releases?&code={product_code}&latest=true&type"
                     f"=release", timeout=5)
    response = r.json()
    if platform not in response[product_code][0]["downloads"]:
        ColorPrint.print_fail("not found")
        return None
    download_links = response[product_code][0]["downloads"][platform]["link"]
    ColorPrint.print_success("found")
    return download_links


def main():
    url = getLatestURL(product_codes["datagrip"])
    Installer(url).run()
    # parser = argparse.ArgumentParser(
    #     # prog=""
    #     description="Command line installer of Jetbrains product"
    # )
    # parser.add_argument()


if __name__ == '__main__':
    main()
