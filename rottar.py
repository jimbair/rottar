#!/usr/bin/python
#
# Written in BASH by David Cantrell
# Ported to Python by James Bair
# 
# NOT YET FINISHED - DO NOT RUN LOL
# The BASH code is still in place, and as it is replaced with Python, 
# is being removed. Since this is a personal project for spare time, 
# I don't mind it being a bit jumbled for now. This is in git so I 
# don't lose the work I have done. I will update the header when done.
#
# Copyright (C) 2010 David Cantrell <david.l.cantrell@gmail.com>
# Copyright (C) 2010 James Bair <james.d.bair@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Modules
import os
import re

# Settings

# Paths to back up
backupInclude = ( '/bin', '/boot', '/etc', '/home', '/lib', '/lib64', '/opt',
                 '/root', '/sbin', '/usr', '/var' )

# Functions

def findTapeDevices():
    """
    Used to dynamically locate any and all SCSI Tape Devices.
    Returns a list of results.
    
    Note this ref:
    http://www.mjmwired.net/kernel/Documentation/scsi/st.txt

    Currently supports:
    st0  nst0  st0l  nst0l  st0m  nst0m  st0a  nst0a
    """
    results = []
    devices = os.listdir('/dev/')
    for device in devices:
        if re.search(r"""^n?st[0-9][l|m|a]?""", device) is not None:
            results.append('/dev/%s' % (device,))
    
    # Return None if zero results
    if results == []:
        return None

    return results

def validTapeDevice(devices=[]):
    """
    Used to validate if we support a tape device. Currently, this program will
    only support /dev/st0 style devices.
    """
    if devices == []:
        return None
    
    results = []

    for device in devices:
        if re.search(r"""^/dev/st[0-9]$""") is not None:
            results.append(device)

    # Return None if none found
    if results == []:
        return None

    return results

def main():
    """
    Our main function.
    """
 
    # Make sure we have a tape device
    dev = findTapeDevices()
    if dev is None:
        sys.stderr.write('Unable to find any tape devices.\n')
        sys.exit(1)
    # Now, make sure we support what we found
    elif validTapeDevice(dev) is None:
        sys.stderr.write('No supported tape devices found.\n')
        sys.exit(1)
    # We also only support a single device as of now.
    elif len(dev) != 1:
        sys.stderr.write('Found %d devices and '
                         'only a single device is supported.\n' % (len(dev),))
        sys.exit(1)

    # Check our folders we are backing up.
    for folder in backupInclude:
        if not os.path.isdir(folder):
            sys.stderr.write("ERROR: %s is not a folder and is "
                             "specified as a backup path.\n" % (folder,))
            sys.exit(1)

    # If we are good, make our device a string object.
    dev = dev[0]


# Paths to exclude (e.g., subdirectories in BACKUP_INCLUDE)
BACKUP_EXCLUDE=

# Full backup tape letter range (e.g., min of A and max of D would have
# four tapes in the full backup rotation)
MIN_FULL_VOL="A"
MAX_FULL_VOL="B"

# Full backup day
FULL_BACKUP_DAY="Mon"


### MAIN ###

PATH=/bin:/usr/bin
TARDB=/var/lib/tar

DAYOFWEEK="$(date +%a)"
STAMP="$(date +%d-%b-%Y)"
LISTED_INCR="${TARDB}/listed-incremental.$(hostname)"
CURR_INCR_TAPE="${TARDB}/curr_incremental_tape"
CURR_FULL_TAPE="${TARDB}/curr_full_tape"

if [ ! -r ${TAPEDEV} ]; then
    echo "${TAPEDEV} does not exist." >&2
    exit 1
fi

if [ ! -d "${TARDB}" ]; then
    mkdir -p "${INCRDR}"
fi

if [ "${DAYOFWEEK}" = "${FULL_BACKUP_DAY}" ]; then
    t="Full"
    CURR_FILE="${CURR_FULL_TAPE}"
    if [ -f "${CURR_FULL_TAPE}" ]; then
        curr="$(cat ${CURR_FULL_TAPE} | tr -d "\n" | od -An -t dC)"
        max="$(echo "${MAX_FULL_VOL}" | tr -d "\n" | od -An -t dC)"

        if [ "${curr}" = "${max}" ]; then
            NEEDED_TAPE="${MIN_FULL_VOL}"
        else
            next="$(expr ${curr} + 1)"
            NEEDED_TAPE="$(awk -v char=${next} 'BEGIN { printf "%c\n", char; exit }')"
        fi
    else
        NEEDED_TAPE="${MIN_FULL_VOL}"
    fi
else
    t="Incremental"
    CURR_FILE="${CURR_INCR_TAPE}"
    if [ -f "${CURR_INCR_TAPE}" ]; then
        NEEDED_TAPE="$(expr $(cat ${CURR_INCR_TAPE}) + 1)"
    else
        NEEDED_TAPE="1"
    fi
fi

EXCLUDE_LIST="$(mktemp -t exclude-list.XXXXXXXXXX)"
echo "${LISTED_INCR}" > ${EXCLUDE_LIST}
find /var -type s >> ${EXCLUDE_LIST}

echo "Insert tape \"${t} ${NEEDED_TAPE}\""
echo -n "Press Enter to begin ${t} backup for ${STAMP}..."
read JUNK

if [ "${t}" = "Full" ]; then
    echo
    echo -n ">>> Forcing full backup by removing listed incremental db..."
    rm -f ${LISTED_INCR} ${CURR_INCR_TAPE}
    echo "done."
fi

echo
echo -n ">>> Erasing tape \"${t} ${NEEDED_TAPE}\"..."
mt -f ${TAPEDEV} erase
echo "done."

echo
echo ">>> Running tar..."
tar -c -v -f ${TAPEDEV} -g ${LISTED_INCR} \
    -X ${EXCLUDE_LIST} \
    --acls --selinux --xattrs --totals=SIGUSR1 \
    ${BACKUP_INCLUDE} 2> ${TARDB}/tar.stderr
rm -f ${EXCLUDE_LIST}

echo
echo -n ">>> Recording current tape in use..."
echo "${NEEDED_TAPE}" > ${CURR_FILE}
echo "done."

echo
echo -n ">>> Rewinding and ejecting tape \"${t} ${NEEDED_TAPE}\"..."
mt -f ${TAPEDEV} offline
echo "done."
