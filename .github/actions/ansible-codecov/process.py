#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Brian Scholer (@briantist)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import sys
import subprocess
import re
import getopt
import time
from pathlib import Path


def get_flags(pattern, input):
    patpat = r'\{([^\}]+)\}'

    pats = re.findall(patpat, pattern)
    matcher = re.sub(patpat, r'(.*?)', pattern)
    match = re.search(matcher, input)

    if match:
        return [pats[i].replace('%', result) for i, result in enumerate(match.groups())]

    return None


def main(argv):
    additional_flags = file_flag_pattern = directory_flag_pattern = directory = fail_on_error = None

    opts, args = getopt.getopt(argv, '', [
        'directory=',
        'directory-flag-pattern=',
        'file-flag-pattern=',
        'additional-flags=',
        'fail-on-error',
    ])

    for opt, arg in opts:
        if opt == '--directory':
            directory = arg
        elif opt == '--directory-flag-pattern':
            directory_flag_pattern = arg
        elif opt == '--file-flag-pattern':
            file_flag_pattern = arg
        elif opt == '--additional-flags':
            additional_flags = arg
        elif opt == '--fail-on-error':
            fail_on_error = True

    extra_flags = additional_flags.split(',') if additional_flags else []

    flags = {}

    directory = Path(directory) if directory else Path.cwd()

    for f in directory.rglob('*'):
        if f.is_file():
            iflags = set()
            if directory_flag_pattern:
                for part in f.parent.parts:
                    dflags = get_flags(directory_flag_pattern, part)
                    if dflags:
                        iflags.update(dflags)

            fflags = get_flags(file_flag_pattern, str(f.name))
            if fflags:
                iflags.update(fflags)

            for flag in iflags:
                flags.setdefault(flag, []).append(str(f.resolve()))

    logextra = ' (+%r)' % extra_flags if extra_flags else ''

    for flag, files in flags.items():
        cmd = ['codecov', 'upload-coverage', '-F', flag]
        [cmd.extend(['-F', extra]) for extra in extra_flags]
        [cmd.extend(['-f', file]) for file in files]
        if fail_on_error:
            cmd.append('-Z')

        print('::group::Flag: %s%s' % (flag, logextra))

        print('Executing: %r' % cmd)

        max_attempt = 5
        for attempt in range(1, max_attempt + 1):
            try:
                subprocess.run(cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, check=True, text=True)
            except subprocess.CalledProcessError as e:
                match = re.search(r'Error: There was an error fetching the storage URL during POST: 429.*?time to availability: (?P<tta>\d+)s', e.stdout)
                if not match:
                    print(f"stdout: {e.stdout}")
                    print(f"stderr: {e.stderr}")
                    raise

                tta = int(match.group('tta')) + 10
                print((
                    f"::warning title=Codecov upload issue::Codecov tokenless upload from fork failed. "
                    f"Waiting {tta} seconds to try again [attempt {attempt} of {max_attempt}]."
                ))
                time.sleep(tta)
            else:
                break

        print('::endgroup::')


if __name__ == '__main__':
    main(sys.argv[1:])
