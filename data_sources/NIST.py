# This fixes the broken import in nistasd
import urllib.request
from nistasd import NISTLines, NISTASD

import numpy as np
import pandas as pd
from astropy import units as q

from .Cache import UseCache

@UseCache()
def load(element, wmin, wmax, wunit="micrometer"):
    wmin = wmin * q.Unit(wunit).to(q.nanometer)
    wmax = wmax * q.Unit(wunit).to(q.nanometer)

    nist = NISTLines(spectrum=element, lower_wavelength=wmin, upper_wavelength=wmax)
    lines = nist.get_lines()

    # Could use more?
    # Or use pandas?
    # wave = [l["wave"] for l in lines]
    # ion = [l["spectrum"] for l in lines]
    # height = [l["rel_int"] for l in lines]

    lines = pd.DataFrame.from_records(lines)
    # lines = np.rec.fromarrays((wave, ion, height), names=["wave", "ion", "height"])
    # Select only lines within the desired window
    select = (lines["wave"] >= wmin) & (lines["wave"] <= wmax)
    lines = lines[select]
    # Convert from nanometer to input unit
    lines["wave"] *= q.nanometer.to(wunit)

    return lines

if __name__ == "__main__":
    import matplotlib.pyplot as plt
    element = "Th"
    wmin = 10000
    wmax = 12000
    lines = load(element, wmin, wmax, wunit="AA")

    plt.plot(lines["wave"], lines["height"])
    plt.show()