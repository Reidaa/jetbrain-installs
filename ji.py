import argparse
import os
import shutil
import sys
import tarfile
from typing import Optional
from pathlib import Path
import colorama
import requests
from tqdm import tqdm

# TODO ADD SUBPARSERS GROUP (JI INSTALL)
# TODO CATCH CTRL+C
# TODO ADD UNIT TEST

product_codes = {
    # "android-studio": "AI", NOT WORKING
    "idea-ult": "UI",  # IntelliJ IDEA Ultimate
    "idea-com": ["IC", "IIC"],  # IntelliJ IDEA Community
    "idea-edu": ["IE", "IIE"],  # IntelliJ IDEA Educational
    "pycharm-pro": ["PY", "PCP"],  # PyCharm Professional
    "pycharm-com": ["PC", "PCP"],  # PyCharm Community
    "pycharm-edu": ["PE", "PCE"],  # PyCharm Educational
    "phpstorm": ["PS"],
    "webstorm": ["WS"],
    "rubymine": ["RM"],
    "appcode": ["OC", "AC"],
    "clion": ["CL"],
    "goland": ["GO"],
    "datagrip": ["DG"],
    "rider": ["RD"],
}

DEFAULT_BINARY_PATH = "/usr/local/bin"
DEFAULT_INSTALL_DIRECTORY_PATH = "/opt"
DEFAULT_TMP_FILE_PATH = "/tmp/"
DEFAULT_URL = "https://data.services.jetbrains.com//products/releases?&code={code}&latest=true&type=release"
ARG_BIN_DEST_DESC = "path of the launch script(s) or symlink(s)"
ARG_DIR_DEST_DESC = "path to the IDE(s)' directory(ies)"
ARG_DRY_DESC = "test run, nothing is installed"
SEPARATION = "----- {soft} -----"
HELP = f"""\
Enjoy :)
-----------------------
{str(list(product_codes))}
"""


class ColorPrint:
    @staticmethod
    def print_success(message: str, end: str = "\n"):
        print(f"{colorama.Fore.GREEN}{message}{colorama.Style.RESET_ALL}", end=end)

    @staticmethod
    def print_fail(message: str, end: str = "\n"):
        print(f"{colorama.Fore.RED}{message}{colorama.Style.RESET_ALL}", end=end)


class InstallerError(Exception):
    pass


class InstallerFlags:
    def __init__(self):
        self.decompressed = False
        self.installed = False


class InstallerOptions:
    def __init__(self, symlink: bool = False, dry: bool = False, script: bool = False):
        self.__symlink = symlink
        self.__dry = dry
        self.__script = script
        self.__shortcut_dirpath = None
        self.__install_dirpath = None

    @property
    def shortcut_dirpath(self):
        return self.__shortcut_dirpath

    @property
    def install_dirpath(self):
        return self.__shortcut_dirpath

    @property
    def dry(self):
        return self.__dry

    @property
    def symlink(self):
        return self.__symlink

    @property
    def script(self):
        return self.__script


class Installer:
    def __init__(self, url: str, options: InstallerOptions, shortcut_path: Optional[str] = None,
                 dir_path: Optional[str] = None
                 ):
        self.bin_dest = shortcut_path if (shortcut_path is not None) else DEFAULT_BINARY_PATH
        self.dir_dest = dir_path if (dir_path is not None) else DEFAULT_INSTALL_DIRECTORY_PATH
        self.options: InstallerOptions = options
        self.url = url

        self.dir_location = ""
        self.filename: str = ""
        self.dl_loc: str = ""
        self.dirname: str = ""
        self.bin_name: str = ""
        self.flags = InstallerFlags()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

    def run(self):
        if not Path(self.dir_dest).is_dir():
            raise InstallerError("Install location is not a directory")
        if not Path(self.bin_dest).is_dir():
            raise InstallerError("Binary install location is not a directory")

        self.bin_dest = Path(self.bin_dest).resolve()
        self.dir_dest = Path(self.dir_dest).resolve()

        # if not self.options.dry:
        # if not os.access(self.bin_dest, os.W_OK):
        #     raise InstallerError(f"Can not access '{self.bin_dest}'")

        self.filename = self.url.rsplit('/', 1)[1]
        self.dl_loc = self.filename
        self.bin_name = f"{self.filename.split('-')[0].lower()}.sh"

        self._download()
        self._decompress()
        if not self.options.dry:
            self._install()
            self._make_shortcut()
        else:
            print("Installation skipped")

    def _download(self):
        status = f"Downloading {self.filename}:"
        print(f"\r{status}", end=" ")

        response = requests.get(self.url, allow_redirects=True, stream=True, timeout=5)
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024 * 4
        pbar = tqdm(total=total_size, desc=status.rstrip(":"), unit_scale=True, file=sys.stdout, leave=False)
        with open(self.dl_loc, 'wb') as handle:
            for data in response.iter_content(block_size):
                pbar.update(len(data))
                handle.write(data)
        pbar.close()

        print(f"\r{status}", end=" ")
        if total_size != 0 and pbar.n != total_size:
            ColorPrint.print_fail("fail")
        else:
            ColorPrint.print_success("done")

    def _decompress(self):
        status = f"Decompressing {self.filename}:"

        try:
            with tarfile.open(self.dl_loc, "r") as archive:
                self.dirname = os.path.commonpath(archive.getnames())
                members = archive.getmembers()
                pbar = tqdm(members, desc=status.rstrip(":"), unit_scale=True, file=sys.stdout, leave=False)
                for member in members:
                    archive.extract(member)
                    pbar.update()
                pbar.close()
                self.dir_location = f"{self.dir_dest}/{self.dirname}"
        except EOFError as e:
            self.flags.decompressed = False
            print(f"\r{status}", end=" ")
            ColorPrint.print_fail("fail")
            print(f"Error: {e}.", file=sys.stderr)
        else:
            self.flags.decompressed = True
            print(f"\r{status}", end=" ")
            ColorPrint.print_success("done")

    def _install(self):
        status = f"Installing {self.dirname} to {self.dir_dest}:"
        print(status, end=" ")

        if self.flags.decompressed is True:
            try:
                if not os.access(self.dir_dest, os.W_OK):
                    raise InstallerError(f"Can not access '{self.dir_dest}'")
                shutil.copytree(self.dirname, self.dir_location)
            except Exception as e:
                self.flags.installed = False
                ColorPrint.print_fail("fail")
                print(f"Error: {e}.", file=sys.stderr)
            else:
                self.flags.installed = True
                ColorPrint.print_success("done")
        else:
            print("skipped")

    def _make_shortcut(self):
        src = f"{self.dir_location}/bin/{self.bin_name}"
        dest = f"{self.bin_dest}/{self.bin_name}"
        status = f"Creating symlink from {src} to {dest}:"
        print(status, end=" ")

        if self.flags.installed is True:
            if self.options.symlink:
                self._make_link()
        else:
            print("skipped")

    def _make_link(self):
        src = f"{self.dir_location}/bin/{self.bin_name}"
        dest = f"{self.bin_dest}/{self.bin_name}"
        status = f"Creating symlink from {src} to {dest}:"
        print(status, end=" ")

        src = Path(src).resolve()
        dest = Path(dest).resolve()
        try:
            os.symlink(src, dest)
        except Exception as e:
            ColorPrint.print_fail("fail")
            print(f"Error: {e}.", file=sys.stderr)
        else:
            ColorPrint.print_success("done")

    def _make_script(self):
        raise NotImplementedError

    def cleanup(self):
        if Path(self.filename).exists():
            OSOperation.remove_file(self.filename)
        if Path(self.dirname).exists():
            OSOperation.remove_dir(self.dirname)


class OSOperation:

    @staticmethod
    def remove_dir(dirpath: str):
        status = f"Removing dir {dirpath}:"
        print(status, end=" ")

        try:
            shutil.rmtree(dirpath)
        except OSError as e:
            ColorPrint.print_fail("fail")
            print(f"Error: {e.filename} - {e.strerror}.", file=sys.stderr)
        else:
            ColorPrint.print_success("done")

    @staticmethod
    def remove_file(filepath: str):
        status = f"Removing {filepath}:"
        print(status, end=" ")

        try:
            os.remove(filepath)
        except OSError:
            ColorPrint.print_fail("fail")
            # print(f"Error: {e.filename} - {e.strerror}.", file=sys.stderr)
        else:
            ColorPrint.print_success("done")

    @staticmethod
    def is_admin() -> bool:
        status = "Checking admin privilege:"
        print(status, end=" ")

        if os.getuid() == 0:
            print("granted")
            return True
        else:
            print("not granted")
            return False


def get_latest_url(product_code: str, platform: str = "linux") -> str:
    status = "Finding the latest download link:"
    print(status, end=" ")

    r = requests.get(DEFAULT_URL.format(code=product_code[0]), timeout=5)
    response = r.json()
    download_links = response[product_code[-1]][0]["downloads"]
    if platform not in download_links:
        ColorPrint.print_fail("fail")
        raise Exception("Platform not found")
    download_link = download_links[platform]["link"]
    ColorPrint.print_success("done")
    return download_link


def parameters():
    parser = argparse.ArgumentParser(
        description="CLI to install some of Jetbrains' IDE",
        conflict_handler='resolve',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=HELP
    )

    install_group = parser.add_argument_group()
    install_group.add_argument("--install", nargs="+", dest="installs", metavar="XXX")
    shortcut_group = install_group.add_mutually_exclusive_group(required=True)
    shortcut_group.add_argument("-l", "--link", action="store_true", help="create symlink(s)", dest="is_link")
    shortcut_group.add_argument("-s", "--script", action="store_true", help="create script(s)", dest="is_script")
    install_group.add_argument("--shortcut-loc", help=ARG_BIN_DEST_DESC, type=str, metavar="PATH", dest="bin_dest")
    install_group.add_argument("--install-loc", help=ARG_DIR_DEST_DESC, type=str, metavar="PATH", dest="dir_dest")
    install_group.add_argument("-d", "--dry", help=ARG_DRY_DESC, action="store_true")

    return parser.parse_args()


def main():
    args = parameters()
    options = InstallerOptions(symlink=args.is_link, dry=args.dry)
    # choices = list(product_codes.keys())

    if sys.platform != "linux":
        raise NotImplementedError(f"Not usable on {sys.platform}")
    for soft in set(args.installs):
        print(SEPARATION.format(soft=soft.upper()))
        if soft not in product_codes:
            print(f"unknown, skipping")
        else:
            url = get_latest_url(product_codes[soft])
            with Installer(url, options, dir_path=args.dir_dest, shortcut_path=args.bin_dest) as installer:
                installer.run()


if __name__ == '__main__':
    try:
        main()
    except NotImplementedError as err:
        print(f"Error: {err}.", file=sys.stderr)
    except InstallerError as err:
        print(f"Error: {err}.", file=sys.stderr)
