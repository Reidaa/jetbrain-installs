import argparse
import os
import pathlib
import shutil
import sys
import tarfile
from typing import Optional, Dict, Callable

import colorama
import requests
from tqdm import tqdm

product_codes = {
    # "android-studio": "AI", NOT WORKING
    "idea-ult": "UI",  # IntelliJ IDEA Ultimate
    "idea-com": "IC",  # IntelliJ IDEA Community
    "idea-edu": "IE",  # IntelliJ IDEA Educational
    "pycharm-pro": "PY",  # PyCharm Professional
    "pycharm-com": "PC",  # PyCharm Community
    "pycharm-edu": "PE",  # PyCharm Educational
    "phpstorm": "PS",
    "webstorm": "WS",
    "rubymine": "RM",
    "appcode": "OC",
    "clion": "CL",
    "goland": "GO",
    "datagrip": "DG",
    "rider": "RD",
}


class ColorPrint:
    @staticmethod
    def print_success(message, end: str = "\n"):
        print(f"{colorama.Fore.GREEN}{message}{colorama.Style.RESET_ALL}", end=end)

    @staticmethod
    def print_fail(message, end: str = "\n"):
        print(f"{colorama.Fore.RED}{message}{colorama.Style.RESET_ALL}", end=end)


class InstallerError(Exception):
    pass


class Installer:
    def __init__(self,
                 url: str,
                 bin_destination: str = "/usr/local/bin",
                 dir_destination: str = "/opt/",
                 options: Dict[str, bool] = None
                 ):
        self.bin_dest = bin_destination
        self.dir_dest = dir_destination
        self.options = options
        self.url = url

        self.dirlocation = ""
        self.filename: str = ""
        self.dirname: str = ""
        self.binname: str = ""
        self.flags = {
            "decompress": False,
            "install": False
        }

    def run(self):
        if not pathlib.Path(self.dir_dest).is_dir():
            raise InstallerError("Install location is not a directory")
        if not pathlib.Path(self.bin_dest).is_dir():
            raise InstallerError("Binary install location is not a directory")

        self.bin_dest = pathlib.Path(self.bin_dest).resolve()
        self.dir_dest = pathlib.Path(self.dir_dest).resolve()

        if not isAdmin():
            if not os.access(self.dir_dest, os.W_OK) or not os.access(self.bin_dest, os.W_OK):
                raise InstallerError(f"Can not access '{self.dir_dest}' and/or '{self.bin_dest}' as regular user")

        self.filename = self.url.rsplit('/', 1)[1]
        self.binname = f"{self.filename.split('-')[0].lower()}.sh"

        self.download()
        self.decompress()
        self.install()
        self.make_shortcut()
        self.cleanup()

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
                self.dirlocation = f"{self.dir_dest}/{self.dirname}"
        except EOFError as e:
            self.flags["decompress"] = False
            print(f"\r{status}", end=" ")
            ColorPrint.print_fail("fail")
            print(f"Error: {e}.", file=sys.stderr)
        else:
            self.flags["decompress"] = True
            print(f"\r{status}", end=" ")
            ColorPrint.print_success("done")

        return

    def install(self):
        status = f"Installing {self.dirname} to {self.dir_dest}:"
        print(status, end=" ")

        if not self.options["dry"] and self.flags["decompress"] is True:
            try:
                shutil.copytree(self.dirname, self.dirlocation)
            except Exception as e:
                self.flags["install"] = False
                ColorPrint.print_fail("fail")
                print(f"Error: {e}.", file=sys.stderr)
            else:
                self.flags["install"] = True
                ColorPrint.print_success("done")
        else:
            print("skipped")

        return

    def make_shortcut(self):
        src = f"{self.dirlocation}/bin/{self.binname}"
        dest = f"{self.bin_dest}/{self.binname}"
        status = f"Creating symlink from {src} to {dest}:"
        print(status, end=" ")

        if not self.options["dry"] and self.flags["install"] is True:
            if self.options["symlink"]:
                self._make_symlink()
            elif self.options["script"]:
                self._make_launch_script()
            else:
                print("unknown type")
        else:
            print("skipped")

        return

    def _make_symlink(self):
        src = f"{self.dirlocation}/bin/{self.binname}"
        dest = f"{self.bin_dest}/{self.binname}"
        status = f"Creating symlink from {src} to {dest}:"
        print(status, end=" ")

        src = pathlib.Path(src).resolve()
        dest = pathlib.Path(dest).resolve()
        try:
            os.symlink(src, dest)
        except Exception as e:
            ColorPrint.print_fail("fail")
            print(f"Error: {e}.", file=sys.stderr)
        else:
            ColorPrint.print_success("done")

    def _make_launch_script(self):
        src = f"{self.dirlocation}/bin/{self.binname}"
        dest = f"{self.bin_dest}/{self.binname}"
        status = f"Creating launch script for {src} located in {dest}:"
        print(status, end=" ")
        pass



    def cleanup(self):
        if self.filename:
            removeFile(self.filename)
        if self.dirname:
            removeDir(self.dirname)
        pass


def removeDir(dirname: str):
    status = f"Removing dir {dirname}:"
    print(status, end=" ")

    try:
        shutil.rmtree(dirname)
    except OSError as e:
        ColorPrint.print_fail("fail")
        print(f"Error: {e.filename} - {e.strerror}.", file=sys.stderr)
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


def isAdmin() -> bool:
    status = "Checking admin privilege:"
    print(status, end=" ")

    if os.getuid() == 0:
        print("granted")
        return True
    else:
        print("not granted")
        return False


def getLatestURL(product_code: str, platform: str = "linux") -> str:
    status = "Finding the latest download link:"

    print(status, end=" ")
    r = requests.get(f"https://data.services.jetbrains.com//products/releases?&code={product_code}&latest=true&type"
                     f"=release", timeout=5)
    response = r.json()
    download_links = response["PCP"][0]["downloads"]
    if platform not in download_links:
        ColorPrint.print_fail("fail")
        raise Exception("Platform not found")
    download_link = download_links[platform]["link"]
    ColorPrint.print_success("done")
    return download_link

def parameters() -> Callable:
    choices = list(product_codes.keys())
    parser = argparse.ArgumentParser(
        prog="jetbrains-install",
        description="Command line installer of Jetbrains IDE",
        conflict_handler='resolve',
        epilog="Enjoy :)"
    )
    # my_group = parser.add_mutually_exclusive_group(required=False)
    # my_group.add_argument('-v', '--verbose', action='store_true')
    # my_group.add_argument('-s', '--silent', action='store_true')

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--symlink", action="store_true", help="to create symlink(s)")
    group.add_argument("--script", action="store_true", help="to create launch script(s)")

    parser.add_argument("-v", '--version', action='version', version='v0.1')

    parser.add_argument("--install", nargs="+", required=True, dest="installs", choices=choices)

    parser.add_argument("--bin-dest", help="where to create the launch script(s) or symlink(s), relative or "
                                           "absolute path", type=str, default="/usr/local/bin")
    parser.add_argument("--dir-dest", help="where to install the IDE(s), relative or absolute path", type=str
                        , default="/opt/")

    parser.add_argument("-d", "--dry", action="store_true", help="test run, nothing is installed")

    return parser.parse_args()

def main():
    args = parameters()

    # print(args)
    options = {
        "symlink": args.symlink,
        "dry": args.dry,
        "script": None
    }

    for soft in args.installs:
        if soft in product_codes:
            print(f"----- {soft.upper()} -----")
            url = getLatestURL(product_codes[soft])
            try:
                Installer(url, dir_destination=args.dir_dest, bin_destination=args.bin_dest, options=options).run()
            except InstallerError as e:
                print(f"Error: {e}.", file=sys.stderr)


if __name__ == '__main__':
    main()
