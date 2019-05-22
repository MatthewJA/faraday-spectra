import numpy
import scipy.ndimage

def generate_spectra(freqs, util_RM, n_spectra=100, min_phi=-1000, max_phi=1000,
                     phi_sampling=300, max_noise=0.333, phi_padding=0,
                     complex_fraction=0.5, drop_channels=0.0):
    """Generate simulated Faraday spectra.

    Uses a two-screen model.

    Parameters
    ----------
    freqs : array or list
        Frequencies sampled, sorted.
    util_RM : module
        util_RM module from RMTools.
    n_spectra : int
        Number of spectra to generate (default: 100).
    min_phi : float
        Minimum Faraday depth in rad/m^2 (default: -1000).
    max_phi : float
        Maximum Faraday depth in rad/m^2 (default: 1000).
    phi_sampling : int
        Faraday depth sampling rate (default: 300).
    max_noise : float
        Maximum noise as a fraction of polarised intensity (default: 0.333).
    phi_padding : int
        How far from the edges of the spectrum to place depths (default: 0).
    complex_fraction : float
        Fraction of generated spectra that are complex
        (i.e. not single-screen; default: 0.5)
    drop_channels : float
        Fraction of channels to drop (default: 0).

    Returns
    -------
    dict
        {
            depths: N x 2 array of Faraday depths.
            amps: N x 2 array of polarised intensities normalised to largest
                component.
            simple: N array of whether spectra are simple.
            spectra: N x F array of true polarised spectra.
            spectra_noisy: N x F array of polarised spectra with noise.
            fdf_gt: N x D array of groundtruth Faraday spectra.
            sim_fdf: N x D array of simulated Faraday dispersion function
                (Faraday spectra).
            targets: N x D array of smoothed true Faraday spectra.
            noise: N array of noise levels.
            dropped_channels: N x D boolean array of whether channels
                were dropped.
        }
    """
    # Compute the RMSFs.
    lsq = (3e8 / numpy.asarray(freqs)) ** 2
    phis = numpy.linspace(min_phi, max_phi, phi_sampling)

    # Generate some Faraday spectra.

    # True parameters: peak positions, amplitudes, and phases.
    depths = numpy.random.uniform(
        min_phi + phi_padding, max_phi - phi_padding, size=(n_spectra, 2))
    amps = numpy.random.uniform(0, 1, size=(n_spectra, 2))
    amps[:, 0] = 1  # Normalise first amplitude to 1.
    # Set simple sources to have 0 for the second peak.
    simple = numpy.random.binomial(1, 1 - complex_fraction, size=(n_spectra,)).astype(bool)
    amps[simple, 1] = 0
    phases = numpy.random.uniform(-numpy.pi / 2, numpy.pi / 2, size=(n_spectra, 2))
    # spectra stores the complex spectrum.
    spectra = numpy.zeros((n_spectra, len(lsq)), dtype='complex')
    fdf_gt = numpy.zeros((n_spectra, phi_sampling), dtype='complex')

    # Drop some channels entirely, at random.
    channel_mask = numpy.random.binomial(1, drop_channels, size=(n_spectra, len(lsq))).astype(bool)

    for i in range(n_spectra):
        for p in range(2):
            if p == 1:
                if simple[i] and amps[i, p]:
                    raise RuntimeError('Unexpected: {}'.format(str((simple[i], amps[i, :]))))
            spectra[i] += amps[i, p] * numpy.exp(2 * 1j * (phases[i, p] + depths[i, p] * lsq))
            idx = phis.searchsorted(depths[i, p])
            fdf_gt[i, idx] += amps[i, p] * numpy.cos(phases[i, p])
            fdf_gt[i, idx] += 1j * amps[i, p] * numpy.sin(phases[i, p])

    # Add Gaussian noise.
    sigmas = numpy.random.uniform(0, max_noise, size=(n_spectra, 1))
    noise = numpy.random.normal(loc=0, scale=sigmas, size=(n_spectra, len(lsq)))
    spectra_noisy = spectra + noise

    # Blank random channels.
    spectra_noisy *= numpy.where(channel_mask, numpy.nan, 1)

    # RM synthesis on the spectra.
    sim_fdf, fwhm = util_RM.do_rmsynth_planes(spectra_noisy.real.T, spectra_noisy.imag.T, lsq, phis)

    sim_fdf = sim_fdf.T

    # Blur the true FDF to get the targets.
    targets_real = scipy.ndimage.gaussian_filter1d(fdf_gt.real, sigma=3, axis=-1)
    targets_imag = scipy.ndimage.gaussian_filter1d(fdf_gt.imag, sigma=3, axis=-1)
    targets = targets_real + 1j * targets_imag

    return {
        'depths': depths,
        'amps': amps,
        'simple': simple,
        'spectra': spectra,
        'spectra_noisy': spectra_noisy,
        'fdf_gt': fdf_gt,
        'sim_fdf': sim_fdf,
        'targets': targets,
        'noise': sigmas,
        'dropped_channels': channel_mask,
    }
