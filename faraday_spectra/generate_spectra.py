import numpy
import scipy.ndimage

def generate_spectra(freqs, util_RM, n_spectra=100, min_phi=-1000, max_phi=1000,
                     phi_sampling=300, max_noise=0.333, phi_padding=0,
                     complex_fraction=0.5):
    """Generate simulated Faraday spectra."""
    # Compute the RMSFs.
    lsq = (3e8 / freqs) ** 2
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
    }
