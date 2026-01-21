from pathlib import Path

from cht_cyclones.tropical_cyclone import TropicalCyclone


def equal_track(left: Path, right: Path) -> bool:
    l_track = TropicalCyclone()
    l_track.read_track(filename=left.as_posix(), fmt="ddb_cyc")

    r_track = TropicalCyclone()
    r_track.read_track(filename=right.as_posix(), fmt="ddb_cyc")

    return l_track.track.equals(r_track.track)
