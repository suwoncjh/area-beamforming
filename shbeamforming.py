import numpy as np
import scipy.special as sp
import spherical_sampling
from utilities import f_to_k

# Eigenmike capsule angles from mh Acoustics documentation
# phi_mics = np.radians(np.array([
#                            69, 90, 111, 90, 32, 55, 90, 125, 148,
#                            125, 90, 55, 21, 58, 121, 159, 69, 90,
#                            111, 90, 32, 55, 90, 125, 148, 125, 90,
#                            55, 21, 58, 122, 159]).reshape(1,-1))
# theta_mics = np.radians(np.array([
#                           0, 32, 0, 328, 0, 45, 69, 45, 0, 315, 291,
#                           315, 91, 90, 90, 89, 180, 212, 180, 148,
#                           180, 225, 249, 225, 180, 135, 111, 135,
#                           269, 270, 270, 271]).reshape(1,-1))
#
# Y_eigenmike = sph_harm_array(N, theta_mics, phi_mics)
Y_eigenmike = np.loadtxt('Y_mics.dat').view(complex)
Q = 32 # number of mic capsules

def sht( x, N ):
    # calculates spherical harmonic transform of
    # eigenmike space-domain signal x up to order N

    p_nm = (4*np.pi / Q) * Y_eigenmike[:, :(N+1)**2].conj().T @ x.T

    return p_nm


def srp_fft( x, fs, N_fft=None ):
    # calculate fft for use in SRP algorithm
    # zeros noise-dominated lower bands in higher-order SH channels
    # removes bands above spatial nyquist (8 kHz for Eigenmike)

    p_nm_k = np.fft.fft(x, axis=1, n=N_fft)
    # take FFT of incoming time-SH-domain frame

    if not N_fft:
        N_fft = p_nm_k.shape[1]
        # infer FFT length if not specified

    f_vals = np.linspace(0, fs/2, N_fft//2)
    k_vals = f_to_k(f_vals)
    # calculate frequency and wavenumber bin values

    cutoff_2nd = np.searchsorted(f_vals, [400])[0]
    cutoff_3rd = np.searchsorted(f_vals, [1000])[0]
    cutoff_4th = np.searchsorted(f_vals, [1800])[0]
    spatial_nyquist = np.searchsorted(f_vals, [8000])[0]+1
    # find bins for low cutoff frequencies and spatial nyquist
    # figures for these listed in Eigenmike documentation

    p_nm_k[4:9,:cutoff_2nd] = 0
    p_nm_k[9:16,:cutoff_3rd] = 0
    p_nm_k[16:,:cutoff_4th] = 0
    p_nm_k = p_nm_k[:, 1:spatial_nyquist]
    # zero frequency bands as calculated above and trim
    # spatially-aliased high frequency bands

    k_vals = k_vals[1:spatial_nyquist]
    # trim list of wavenumbers to match

    return p_nm_k, k_vals


def b( n, k, r, r_a=None ):
    # n = SH order
    # k = wavenumber
    # r = mic position radius
    # r_a = rigid sphere radius

    if r_a == None:
        r_a = r # r_a = r with eigenmike

    b = (4 * np.pi * 1j**n
    * (sp.spherical_jn(n, k*r) -
    sp.spherical_jn(n, k*r_a, True) / sph_hankel2(n, k*r_a, True)
    * sph_hankel2(n, k*r)))

    return b


def B_diag_matrix( N, k, r, beampattern='pwd', r_a=None):
    # makes diagonal matrix containing b(n,kr) coefficients

    b_array = np.array([b(n, k, r, r_a)
                for n in range(N+1) for m in range(-n, n+1)])

    if beampattern == 'pwd':
        d = 1

    elif beampattern == 'min_sidelobe':
        d = np.array([d_minimum_sidelobe(N, n)
                for n in range(N+1) for m in range(-n, n+1)])

    # apply weights for selected beam pattern and diagonalify
    B = np.diag(d/b_array)

    return B


def B_3D( N, k, r, beampattern='pwd', r_a=None ):
    # makes 3D matrix containing stack of b(n,kr) diagonals

    B = np.array([B_diag_matrix(N, k, r, beampattern, r_a) for k in k])

    return B
    # B = np.array([np.diag(
    #         np.array([b(n, k, 0.042)
    #         for n in range(N+1) for m in range(-n, n+1)]))
    #     for k in k])


def g0(N_sh):
    return np.sqrt( (2*N_sh + 1) / (N_sh+1)**2 )

def d_minimum_sidelobe(N_sh, n_sh):
    # equation from Delikaris-Manias 2016
    return (g0(N_sh) * (sp.gamma(N_sh+1) * sp.gamma(N_sh+2) /
                        sp.gamma(N_sh+1+n_sh) * sp.gamma(N_sh+3+n_sh)))

def sph_hankel2(n, z, derivative=False):

    h2 = (sp.spherical_jn(n, z, derivative)
          - 1j*sp.spherical_yn(n, z, derivative))

    return h2


def sph_harm_array(N, theta, phi):

    # Q = np.max(phi.shape)*theta.shape[np.argmin(phi.shape)]
    # find number of angles
    if type(theta) == float:
        Q = 1
    else:
        Q = len(theta)

    Y_mn = np.zeros([Q, (N+1)**2], dtype=complex)

    for i in range((N+1)**2):
        n = np.floor(np.sqrt(i))
        m = i - (n**2) - n
        # trick from ambiX paper

        Y_mn[:,i] = sp.sph_harm(m, n, theta, phi).reshape(1,-1)

    return np.array(Y_mn)
