"""
pytermgui.input
---------------
author: bczsalba


File providing the getch() function to easily read character inputs.

credits:
    - original getch implementation: Danny Yoo (https://code.activestate.com/recipes/134892)
    - modern additions & idea:       kcsaff (https://github.com/kcsaff/getkey)
"""

# pylint doesn't see the C source
# pylint: disable=c-extension-no-member, no-name-in-module

import os
import tty
import sys
from typing import IO, AnyStr, Generator
from select import select
from codecs import getincrementaldecoder

if os.name == "posix":
    import termios
else:
    import msvcrt  # pylint: disable=import-error


def _is_ready(file: IO[AnyStr]) -> bool:
    """ Return if file is reading for reading """

    result = select([file], [], [], 0.0)
    return len(result[0]) > 0


class _GetchUnix:
    """ Getch implementation for UNIX """

    def __init__(self) -> None:
        """ Set up instance attributes """

        self.decode = getincrementaldecoder(sys.stdin.encoding)().decode

    def _read(self, num: int) -> str:
        """ Read num characters from sys.stdin """

        buff = ""
        while len(buff) < num:
            char = os.read(sys.stdin.fileno(), 1)
            buff += self.decode(char)

        return buff

    def get_chars(self) -> Generator[str, None, None]:
        """ Get characters while possible, yield them """

        descriptor = sys.stdin.fileno()
        old_settings = termios.tcgetattr(descriptor)
        tty.setcbreak(descriptor)

        try:
            yield self._read(1)

            while _is_ready(sys.stdin):
                yield self._read(1)

        finally:
            # reset terminal state, set echo on
            termios.tcsetattr(descriptor, termios.TCSADRAIN, old_settings)

    def __call__(self) -> str:
        """ Return all characters that can be read """

        buff = "".join(self.get_chars())
        # try:
        # except KeyboardInterrupt:
        # return '\x03'

        return buff


if os.name == "posix":
    # Use class if on a POSIX system
    getch = _GetchUnix()

else:
    # Use already-existing builtin library otherwise
    getch = msvcrt.wgetch  # type: ignore