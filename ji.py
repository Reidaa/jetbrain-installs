#!/usr/bin/env python3

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

# TODO ADD REMOVE (JI REMOVE)
# TODO ADD UPDATE (JI UPDATE)
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

DEFAULT_URL = "https://data.services.jetbrains.com//products/releases?&code={code}&latest=true&type=release"

DEFAULT_BINARY_PATH = "/usr/local/bin"
DEFAULT_INSTALL_DIRECTORY_PATH = "/opt"
DEFAULT_TMP_FILE_PATH = "/tmp/"

ARG_BIN_DEST_DESC = "path of the launch script(s) or symlink(s)"
ARG_DIR_DEST_DESC = "path to the IDE(s)' directory(ies)"
ARG_DRY_DESC = "test run, nothing is installed or removed"
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

    @staticmethod
    def print_skipped(message: str, end: str = "\n"):
        print(f"{colorama.Fore.MAGENTA}{message}{colorama.Style.RESET_ALL}", end=end)


class InstallerError(Exception):
    pass


class InstallerFlags:
    def __init__(self):
        self.decompressed = False
        self.installed = False


class InstallerOptions:
    def __init__(self, dry: bool = False, shortcut_path: Optional[str] = None, dir_path: Optional[str] = None):
        self.__dry = dry
        self.__shortcut_dirpath = shortcut_path if (shortcut_path is not None) else DEFAULT_BINARY_PATH
        self.__install_dirpath = dir_path if (dir_path is not None) else DEFAULT_INSTALL_DIRECTORY_PATH

    @property
    def shortcut_dirpath(self):
        return self.__shortcut_dirpath

    @property
    def install_dirpath(self):
        return self.__install_dirpath

    @property
    def dry(self):
        return self.__dry


class Installer:
    def __init__(self, url: str, options: InstallerOptions):
        self.options: InstallerOptions = options
        self.url = url
        self.flags = InstallerFlags()

        self.dir_location = ""
        self.filename: str = ""
        self.dl_loc: str = ""
        self.dirname: str = ""
        self.bin_name: str = ""
        self.dir_dest: str = ""
        self.bin_dest: str = ""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

    def run(self):
        if not Path(self.options.install_dirpath).is_dir():
            raise InstallerError("Install location is not a directory")
        if not Path(self.options.shortcut_dirpath).is_dir():
            raise InstallerError("Shortcut install location is not a directory")

        self.bin_dest = Path(self.options.shortcut_dirpath).resolve()
        self.dir_dest = Path(self.options.install_dirpath).resolve()

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
            ColorPrint.print_skipped("Dry install, installation skipped")

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
            ColorPrint.print_fail(f"fail: Error: {e}.")
            # print(f"Error: {e}.", file=sys.stderr)
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
                ColorPrint.print_fail(f"fail: Error: {e}.")
                # print(f"Error: {e}.", file=sys.stderr)
            else:
                self.flags.installed = True
                ColorPrint.print_success("done")
        else:
            # print("skipped")
            ColorPrint.print_skipped("skipped")

    def _make_shortcut(self):
        src = f"{self.dir_location}/bin/{self.bin_name}"
        dest = f"{self.bin_dest}/{self.bin_name}"
        status = f"Creating symlink from {src} to {dest}:"
        print(status, end=" ")

        if self.flags.installed is False:
            ColorPrint.print_skipped("skipped")
        else:
            src = Path(src).resolve()
            dest = Path(dest).resolve()
            try:
                os.symlink(src, dest)
            except Exception as e:
                ColorPrint.print_fail(f"fail: Error: {e}.")
                # print(f"Error: {e}.", file=sys.stderr)
            else:
                ColorPrint.print_success("done")


    def cleanup(self):
        if Path(self.filename).exists():
            OSOperation.remove_file(self.filename)
        if Path(self.dl_loc).exists():
            OSOperation.remove_file(self.dl_loc)
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
        e = "Platform not found"
        ColorPrint.print_fail(f"fail: {e}")
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

    # subparsers = parser.add_subparsers(dest="subparser_name")
    # parser_install = subparsers.add_parser("install", help="install help")
    # parser_remove = subparsers.add_parser("remove", help="remove help")
    # parser_update = subparsers.add_parser("update", help="update help")
    # parser_install.add_argument("softs", nargs="+", metavar="XXX")
    # parser_install.add_argument("--install-loc", help=ARG_DIR_DEST_DESC, type=str, metavar="PATH", dest="dir_dest")
    # parser_install.add_argument("--shortcut-loc", help=ARG_BIN_DEST_DESC, type=str, metavar="PATH", dest="bin_dest")
    # parser_remove.add_argument("softs", nargs="+", metavar="XXX")
    # parser_update.add_argument("softs", nargs="+", metavar="XXX")

    parser.add_argument("-i", "--install", nargs="+", dest="softs", metavar="soft", required=True)
    parser.add_argument("-d", "--dry", help=ARG_DRY_DESC, action="store_true")
    parser.add_argument("--install-loc", help=ARG_DIR_DEST_DESC, type=str, metavar="PATH", dest="dir_dest")
    parser.add_argument("--shortcut-loc", help=ARG_BIN_DEST_DESC, type=str, metavar="PATH", dest="bin_dest")

    return parser.parse_args()


def main():
    args = parameters()

    if sys.platform.startswith("linux") is False:
        raise NotImplementedError(f"{sys.platform} not supported")

    for soft in set(args.softs):
        print(SEPARATION.format(soft=soft.upper()))
        if soft not in product_codes:
            print(f"unknown, skipping")
        else:

            options = InstallerOptions(dry=args.dry, dir_path=args.dir_dest, shortcut_path=args.bin_dest)
            url = get_latest_url(product_codes[soft])
            with Installer(url, options) as installer:
                installer.run()


if __name__ == '__main__':
    try:
        main()
    except NotImplementedError as err:
        print(f"Error: {err}.", file=sys.stderr)
    except InstallerError as err:
        print(f"Error: {err}.", file=sys.stderr)
