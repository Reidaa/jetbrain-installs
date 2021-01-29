import os
import shutil
import sys
from typing import Optional
import tarfile

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
    def __init__(self, url: str, destination: str = "/opt/"):
        self.url = url
        self.destination = destination
        self.filename: str = ""
        self.dirname: str = ""

        if self.url.find('/'):
            self.filename = self.url.rsplit('/', 1)[1]

    def run(self):
        self.download()
        self.decompress()
        self.install()
        self.cleanup()

    def decompress(self):
        status = f"Decompressing {self.filename}:"
        print(status, end=" ")

        try:
            with tarfile.open(self.filename, "r") as archive:
                self.dirname = os.path.commonpath(archive.getnames())
                members = archive.getmembers()
                pbar = tqdm(members, desc=status.rstrip(":"), unit_scale=True, file=sys.stdout, leave=False)
                for member in members:
                    archive.extract(member)
                    pbar.update()
                pbar.close()
        except:
            print(f"\r{status}", end=" ")
            ColorPrint.print_fail("fail")
        else:
            print(f"\r{status}", end=" ")
            ColorPrint.print_success("done")

        return

    def install(self):
        pass
        # status = f"Installing {self.filename} to {self.destination}:"
        # print(status, end=" ")
        #
        # try:
        #     with tarfile.open(self.filename, "r") as archive:
        #         # archive.extractall()
        #         self.dirname = os.path.commonpath(archive.getnames())
        # except:
        #     ColorPrint.print_fail("fail")
        # else:
        #     ColorPrint.print_success("done")

        # return

    def download(self):
        status = f"Downloading {self.filename}:"
        print(f"\r{status}", end=" ")

        response = requests.get(self.url, allow_redirects=True, stream=True, timeout=5)
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024 * 4
        pbar = tqdm(total=total_size, desc=status.rstrip(":"), unit_scale=True, file=sys.stdout, leave=False)
        with open(self.filename, 'wb') as handle:
            for data in response.iter_content(block_size):
                pbar.update(len(data))
                handle.write(data)
        pbar.close()

        if total_size != 0 and pbar.n != total_size:
            print(f"\r{status}", end=" ")
            ColorPrint.print_fail("fail")
        else:
            print(f"\r{status}", end=" ")
            ColorPrint.print_success("done")
        return

    def cleanup(self):
        removeFile(self.filename)
        removeDir(self.dirname)
        pass


def removeDir(dirname: str):
    status = f"Removing dir {dirname}:"
    print(status, end=" ")

    try:
        shutil.rmtree(dirname)
    except OSError as e:
        ColorPrint.print_fail("fail")
        # print(f"Error: {e.filename} - {e.strerror}.", file=sys.stderr)
    else:
        ColorPrint.print_success("done")
    return


def removeFile(filename: str):
    status = f"Removing {filename}:"
    print(status, end=" ")

    try:
        os.remove(filename)
    except OSError as e:
        ColorPrint.print_fail("fail")
        # print(f"Error: {e.filename} - {e.strerror}.", file=sys.stderr)
    else:
        ColorPrint.print_success("done")
    return


def checkAdminPrivilege() -> bool:
    status = "checking admin privilege:"
    print(status, end=" ")

    if os.getuid() == 0:
        print("granted")
        return True
    else:
        print("not granted")
        return False


def getLatestURL(product_code: str, platform: str = "linux") -> Optional[str]:
    status = "Finding the latest download link:"

    print(status, end=" ")
    r = requests.get(f"https://data.services.jetbrains.com//products/releases?&code={product_code}&latest=true&type"
                     f"=release", timeout=5)
    response = r.json()
    if platform not in response[product_code][0]["downloads"]:
        ColorPrint.print_fail("fail")
        return None
    download_links = response[product_code][0]["downloads"][platform]["link"]
    ColorPrint.print_success("done")
    return download_links


def main():
    to_install = ["datagrip"]
    for soft in to_install:
        print(f"----- {soft.upper()} -----")
        url = getLatestURL(product_codes[soft])
        Installer(url).run()
    # parser = argparse.ArgumentParser(
    #     # prog=""
    #     description="Command line installer of Jetbrains product"
    # )
    # parser.add_argument()


if __name__ == '__main__':
    main()
