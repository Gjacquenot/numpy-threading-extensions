import os
import sys
import re
import glob

# NOTE: code adapted from psinfo

def open_binary(fname, **kwargs):
    return open(fname, "rb", **kwargs)

def cpu_physical_linux():
    """Return the number of physical cores in the system.
    None may be returned on failure.
    """
    # Method #1
    ls = set()
    # These 2 files are the same but */core_cpus_list is newer while
    # */thread_siblings_list is deprecated and may disappear in the future.
    # https://www.kernel.org/doc/Documentation/admin-guide/cputopology.rst
    # https://github.com/giampaolo/psutil/pull/1727#issuecomment-707624964
    # https://lkml.org/lkml/2019/2/26/41
    p1 = "/sys/devices/system/cpu/cpu[0-9]*/topology/core_cpus_list"
    p2 = "/sys/devices/system/cpu/cpu[0-9]*/topology/thread_siblings_list"
    for path in glob.glob(p1) or glob.glob(p2):
        with open_binary(path) as f:
            ls.add(f.read().strip())
    result = len(ls)
    if result != 0:
        return result

    # Method #2
    mapping = {}
    current_info = {}
    with open_binary('/proc/cpuinfo') as f:
        for line in f:
            line = line.strip().lower()
            if not line:
                # new section
                try:
                    mapping[current_info[b'physical id']] = \
                        current_info[b'cpu cores']
                except KeyError:
                    pass
                current_info = {}
            else:
                # ongoing section
                if line.startswith((b'physical id', b'cpu cores')):
                    key, value = line.split(b'\t:', 1)
                    current_info[key] = int(value)

    result = sum(mapping.values())
    return result or None  # mimic os.cpu_count()

def cpu_count_linux():
    """
    Return the number of logical CPUs and physical cores.
    None may be returned on failure.
    """
    try:
        num= os.sysconf("SC_NPROCESSORS_ONLN")
    except ValueError:
        # as a second fallback we try to parse /proc/cpuinfo
        num = 0
        with open_binary('/proc/cpuinfo') as f:
            for line in f:
                if line.lower().startswith(b'processor'):
                    num += 1

        # try to parse /proc/stat as a last resort
        if num == 0:
            search = re.compile(r'cpu\d')
            with open_text('/proc/stat') as f:
                for line in f:
                    line = line.split(' ')[0]
                    if search.match(line):
                        num += 1

        if num == 0:
            # mimic os.cpu_count()
            num=None
    return num, cpu_physical_linux()

