#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Created on Wed Jan 22 15:52:24 2014
Script to analyse the seismograms generated by SPECFEM.
The arguments must be correct paths to existing seismogram files or
an existing option (--hold, --grid)
@author: Alexis Bottero (alexis.bottero@gmail.com)
"""
from __future__ import (absolute_import, division, print_function)

import argparse # To deal with arguments :
                # https://docs.python.org/2/library/argparse.html
import numpy as np              # NumPy (multidimensional arrays, linear algebra, ...)
import matplotlib.pyplot as plt # Matplotlib's pyplot: MATLAB-like syntax
import matplotlib.mlab as mlab  # Numerical python functions written for compatability with MATLAB commands with the same names
import matplotlib.cm as cm      # This module provides a large set of colormaps and other related tools
from pylab import specgram
from numpy.fft import rfftfreq, rfft
import os
from sys import exit
import math as M
from matplotlib.colors import Normalize
from matplotlib import __version__ as mplVersion

MATPLOTLIB_VERSION = mplVersion

def _nearestPow2(x):
    """
    Find power of two nearest to x

    >>> _nearestPow2(3)
    2.0
    >>> _nearestPow2(15)
    16.0

    :type x: float
    :param x: Number
    :rtype: Int
    :return: Nearest power of 2 to x
    """
    a = M.pow(2, M.ceil(np.log2(x)))
    b = M.pow(2, M.floor(np.log2(x)))
    if abs(a - x) < abs(b - x):
        return a
    else:
        return b

def spectrogram(data, samp_rate, per_lap=0.9, wlen=None, log=False,
                outfile=None, fmt=None, axes=None, dbscale=False,
                mult=8.0, cmap=None, zorder=None, title=None, show=True,
                sphinx=False, clip=[0.0, 1.0]):
    """
    Computes and plots spectrogram of the input data.

    :param data: Input data
    :type samp_rate: float
    :param samp_rate: Samplerate in Hz
    :type per_lap: float
    :param per_lap: Percentage of overlap of sliding window, ranging from 0
        to 1. High overlaps take a long time to compute.
    :type wlen: int or float
    :param wlen: Window length for fft in seconds. If this parameter is too
        small, the calculation will take forever.
    :type log: bool
    :param log: Logarithmic frequency axis if True, linear frequency axis
        otherwise.
    :type outfile: str
    :param outfile: String for the filename of output file, if None
        interactive plotting is activated.
    :type fmt: str
    :param fmt: Format of image to save
    :type axes: :class:`matplotlib.axes.Axes`
    :param axes: Plot into given axes, this deactivates the fmt and
        outfile option.
    :type dbscale: bool
    :param dbscale: If True 10 * log10 of color values is taken, if False the
        sqrt is taken.
    :type mult: float
    :param mult: Pad zeros to length mult * wlen. This will make the
        spectrogram smoother. Available for matplotlib > 0.99.0.
    :type cmap: :class:`matplotlib.colors.Colormap`
    :param cmap: Specify a custom colormap instance
    :type zorder: float
    :param zorder: Specify the zorder of the plot. Only of importance if other
        plots in the same axes are executed.
    :type title: str
    :param title: Set the plot title
    :type show: bool
    :param show: Do not call `plt.show()` at end of routine. That way, further
        modifications can be done to the figure before showing it.
    :type sphinx: bool
    :param sphinx: Internal flag used for API doc generation, default False
    :type clip: [float, float]
    :param clip: adjust colormap to clip at lower and/or upper end. The given
        percentages of the amplitude range (linear or logarithmic depending
        on option `dbscale`) are clipped.
    """
    # enforce float for samp_rate
    samp_rate = float(samp_rate)

    # set wlen from samp_rate if not specified otherwise
    if not wlen:
        wlen = samp_rate / 100.

    npts = len(data)
    # nfft needs to be an integer, otherwise a deprecation will be raised
    # XXX add condition for too many windows => calculation takes for ever
    nfft = int(_nearestPow2(wlen * samp_rate))
    if nfft > npts:
        nfft = int(_nearestPow2(npts / 8.0))

    if mult is not None:
        mult = int(_nearestPow2(mult))
        mult = mult * nfft
    nlap = int(nfft * float(per_lap))

    data = data - data.mean()
    end = npts / samp_rate

    # Here we call not plt.specgram as this already produces a plot
    # matplotlib.mlab.specgram should be faster as it computes only the
    # arrays
    # XXX mlab.specgram uses fft, would be better and faster use rfft
    if MATPLOTLIB_VERSION >= [0, 99, 0]:
        specgram, freq, time = mlab.specgram(data, Fs=samp_rate, NFFT=nfft,
                                             pad_to=mult, noverlap=nlap)
    else:
        specgram, freq, time = mlab.specgram(data, Fs=samp_rate,
                                             NFFT=nfft, noverlap=nlap)

    # db scale and remove zero/offset for amplitude
    if dbscale:
        specgram = 10 * np.log10(specgram[1:, :])
    else:
        specgram = np.sqrt(specgram[1:, :])
    freq = freq[1:]

    vmin, vmax = clip
    if vmin < 0 or vmax > 1 or vmin >= vmax:
        msg = "Invalid parameters for clip option."
        raise ValueError(msg)
    _range = float(specgram.max() - specgram.min())
    vmin = specgram.min() + vmin * _range
    vmax = specgram.min() + vmax * _range
    norm = Normalize(vmin, vmax, clip=True)

    if not axes:
        fig = plt.figure()
        ax = fig.add_subplot(111)
    else:
        ax = axes

    # calculate half bin width
    halfbin_time = (time[1] - time[0]) / 2.0
    halfbin_freq = (freq[1] - freq[0]) / 2.0

    # argument None is not allowed for kwargs on matplotlib python 3.3
    kwargs = dict((k, v) for k, v in
                  (('cmap', cmap), ('zorder', zorder))
                  if v is not None)

    if log:
        # pcolor expects one bin more at the right end
        freq = np.concatenate((freq, [freq[-1] + 2 * halfbin_freq]))
        time = np.concatenate((time, [time[-1] + 2 * halfbin_time]))
        # center bin
        time -= halfbin_time
        freq -= halfbin_freq
        # pcolormesh issue was fixed in matplotlib r5716 (2008-07-07)
        # between tags 0.98.2 and 0.98.3
        # see:
        #  - http://matplotlib.svn.sourceforge.net/viewvc/...
        #    matplotlib?revision=5716&view=revision
        #  - http://matplotlib.org/_static/CHANGELOG
        if MATPLOTLIB_VERSION >= [0, 98, 3]:
            # Log scaling for frequency values (y-axis)
            ax.set_yscale('log')
            # Plot times
            ax.pcolormesh(time, freq, specgram, norm=norm, **kwargs)
        else:
            X, Y = np.meshgrid(time, freq)
            ax.pcolor(X, Y, specgram, cmap=cmap, zorder=zorder, norm=norm)
            ax.semilogy()
    else:
        # this method is much much faster!
        specgram = np.flipud(specgram)
        # center bin
        extent = (time[0] - halfbin_time, time[-1] + halfbin_time,
                  freq[0] - halfbin_freq, freq[-1] + halfbin_freq)
        ax.imshow(specgram, interpolation="nearest", extent=extent, **kwargs)

    # set correct way of axis, whitespace before and after with window
    # length
    ax.axis('tight')
    ax.set_xlim(0, end)
    ax.grid(False)
    if axes:
        return ax

    ax.set_xlabel('Time [s]')
    ax.set_ylabel('Frequency [Hz]')
    if title:
        ax.set_title(title)

    if not sphinx:
        # ignoring all NumPy warnings during plot
        temp = np.geterr()
        np.seterr(all='ignore')
        plt.draw()
        np.seterr(**temp)
    if outfile:
        if fmt:
            fig.savefig(outfile, format=fmt)
        else:
            fig.savefig(outfile)
    elif show:
        plt.show()
    else:
        return ax

def zeroPad(t,ft,nZeros):
    """ From t and f(t) add points to t and zeros to f(t)
    dt must be constant : t[1]-t[0]=t[2]-t[1]=...=t[n]-t[n-1]
    """
    dt=t[1]-t[0]
    for i in np.arange(nZeros):
        t=np.append(t,t[-1]+dt)
        ft=np.append(ft,0.0)
    return t,ft

parser = argparse.ArgumentParser(description='Analyse seismograms generated by SPECFEM')

parser.add_argument('-s','--spectrum',nargs='?',type=int, choices=[1,2,4,8,16,32],
    help='Plot spectrum of seismogram. By default the seismogram is zero \
          padded up to the next power of 2. You can multiply this value by \
          adding an optional argument. For example : --spectrum 4 will zero \
          pad the seismogram up to the third power of 2.',default=99)
parser.add_argument('--specgram', nargs='?',type=int,default=-1,
    help='show spectrogram (the resolution res (sampling=Fs/res) can be given in option, default: sampling = Fs/100)')
parser.add_argument('--hold', action='store_true',
    help='plot all on the same figure')
parser.add_argument('--semilogy', action='store_true',
    help='Y axis in log scale')
parser.add_argument('-n','--normalize', action='store_true',
    help='_if --hold is chosen and if the number of traces is 2 rescale the second trace for comparison of the first one \
          _if --hold is not chosen rescale every trace so that the absolute maximum is one')
parser.add_argument('-f','--factor',  type=float, default=1.0,
    help='_if --hold is chosen and if the number of traces is 2 rescale the second trace \
          _if --hold is not chosen rescale every trace')
parser.add_argument('-w','--linewidth',  type=float, default=1.0,
    help='set linewidth on plots')
parser.add_argument('--fontsize',  type=float, default=16.0,
    help='set fontsize on plots')
parser.add_argument('--xlabel',  type=str, default="",
    help='set xlabel on plots: ex \"r\'time ($s$)\'\"')
parser.add_argument('--ylabel',  type=str, default="",
    help='set ylabel on plots: ex \"r\'time ($s$)\'\"')
parser.add_argument('-g','--grid', action='store_true',
    help='show a grid on the plot')
parser.add_argument('files', nargs='+', type=argparse.FileType('r'),
    help='files to be plotted')
parser.add_argument('--plot_option', type=str,
    help="Plotting options. Examples : 'r-+' will produce red crosses linked \
    by lines ",default='-')
parser.add_argument('--shift', type=float,
    help="If one file given : shift its abscissa values. If several files are given shift all of them with respect to the \
          first one",default=0.0)
parser.add_argument('--invert_yaxis', action='store_true',default=False,
    help='Invert y axis')
parser.add_argument('--invert_axis', action='store_true',default=False,
    help='Invert axis (first column becomes ordinates, second becomes abscissa)')
parser.add_argument('-l','--legend', nargs='?',type=str,
    help='Add a legend. Labels must be given separated by commas. By default, if no label is given the name of the files will \
    be used',default='99')
parser.add_argument('-c','--colors', nargs=1,type=str,
    help='Use this option to set curves colors (RGB). Labels must be given separated by +. Ex:0,0,0.8+0.8,0,0',default='99')
parser.add_argument('--writeFFT', action='store_true',
    help='Write FFT in file')
parser.add_argument('-v','--verbose', action='store_true',
    help='show more details')

args = parser.parse_args()

plot_legend = False
default_legend = False
legend_loc = 0
#'best' 	0
#'upper right' 	1
#'upper left' 	2
#'lower left' 	3
#'lower right' 	4
#'right' 	5
#'center left' 	6
#'center right' 	7
#'lower center' 	8
#'upper center' 	9
#'center' 	10
user_labels = []
default_colors = True
user_colors = []
for seismo in args.files:      # Loop on the files given
    user_labels.append(seismo.name) # By default the labels are the name of the files
plot_spectrum = True
plot_specgram = False
fact = -1
y_axis_already_inverted = False
temp_color = []

if args.colors != '99': # If --colors is given
    default_colors = False
    user_colors = args.colors[0].split('+')
    if len(user_colors) != len(args.files):
        exit(str(len(user_colors))+" color(s) is/are given while "+str(len(args.files))+" file(s) has-ve to be ploted! "+
        "We remind that colors must be separated by commas. Terminating ...")
    for string in user_colors: # For ex string = '0.1,0.1,0'
        temp_color.append(tuple([float(i) for i in string.split(',')])) # temp_color = (0.1,0.1,0)
    user_colors = temp_color # For ex [(0.1,0.1,0),(0.8,0.1,0),(0.1,0.5,0.3)]

if args.legend == None: # If --legend is given with no argument
    default_legend = True
    plot_legend = True
elif args.legend == '99': # If --legend is not given
    plot_legend = False
else:
    plot_legend = True
    user_labels = args.legend.split(',')
    if len(user_labels) != len(args.files):
        exit(str(len(user_labels))+" label(s) is/are given while "+str(len(args.files))+" files has-ve to be ploted! "+
        "We remind that labels must be separated by commas. Terminating ...")

if args.spectrum == None: # If --spectrum is given with no argument
    plot_spectrum = True  # We plot the spectrum ...
    pad = 1               # ... without zero padding
elif args.spectrum == 99: # If --spectrum is not given
    plot_spectrum = False # We don't plot the spectrum
    pad = -1
else:
    plot_spectrum = True
    pad = args.spectrum

if args.specgram == None: # If --specgram is given with no argument
    plot_specgram = True  # We plot the specgram
    fact = -1             # NFFT will be len(signal)/100
    plot_spectrum = False # Hence we don't plot the spectrum
elif args.specgram == -1: # If --spectrum is not given
    plot_specgram = False # Nothing to be done
else:                     # Else ...
    plot_specgram = True  # We plot the specgram
    fact = args.specgram  # With the NFFT given
    plot_spectrum = False # Hence we don't plot the spectrum

scaleFilesWithFirstOne = args.hold and len(args.files) > 1
scaleEverything = not scaleFilesWithFirstOne
factorFirstFile = 1.0 # If scaleFilesWithFirstOne this will be used to scale the second file with respect to the first one
factorSecondFile = 1.0

for idx,seismo in enumerate(args.files):      # Loop on the files given
    if os.stat(seismo.name).st_size == 0:
        exit(seismo.name+" is empty!")
    data = np.loadtxt(seismo)  # Load the seismogram
    if len(np.shape(data)) == 1:
        if plot_spectrum or plot_specgram:
            exit("Just one column in",seismo.name,"! Impossible to calculate a spectrum...")
        else:
            t_seismo = np.arange(len(data))
            ampl_seismo = data[:]
            if args.verbose:
                print("Just one column in",seismo.name,"! Using the indices as abscissa")
    else:
        t_seismo = data[:, 0]      # First column is time
        ampl_seismo = data[:, 1]   # Second column is amplitude
    dt=t_seismo[1]-t_seismo[0] # Time interval
    nt = len(t_seismo)         # Total number of points
    if len(args.files) > 1 and seismo == args.files[0]: # If several files has been given we shift them with respect to the first one
        t_shift = 0.0
    else:
        t_shift = args.shift # This is zero except if it has been given with option --shift
    if seismo == args.files[0] or args.hold is False:
        tmin = t_seismo[0] + t_shift
        tmax = t_seismo[-1] + t_shift
    else:
        tmin=min(tmin,t_seismo[0] + t_shift)
        tmax=max(tmax,t_seismo[-1] + t_shift)
    if not args.hold:
        plt.figure()
    if plot_spectrum:
        N2=2**(nt-1).bit_length()*pad   # (Smallest power of 2 greater than length)*pad
        t_seismo,ampl_seismo=zeroPad(t_seismo,ampl_seismo,N2-nt) # Zero-pad the seismogram
        Sf = abs(rfft(ampl_seismo,N2)/nt)  # Perform Fourier transform
        freq_seismo = rfftfreq(N2,d=dt) # Compute frequency vector
        if scaleFilesWithFirstOne:
            if seismo != args.files[0]:
                factorFirstFile = args.factor
            else:
                factorFirstFile = 1.0
            if args.normalize:
                factorSecondFile = max(Sf)
            else:
                factorSecondFile = 1.0
        else:
            if args.normalize:
                factorSecondFile = max(Sf)/args.factor
            else:
                factorSecondFile = 1.0/args.factor
        if default_colors:
            plt.plot(freq_seismo,Sf*factorFirstFile/factorSecondFile,args.plot_option,label=user_labels[idx],
            linewidth=args.linewidth)
            if args.writeFFT:
                np.savetxt(seismo.name+".fft",np.dstack((freq_seismo,Sf*factorFirstFile/factorSecondFile))[0])
                print(seismo.name+".fft has been written.")
        else:
            plt.plot(freq_seismo,Sf*factorFirstFile/factorSecondFile,args.plot_option,label=user_labels[idx],color=user_colors[idx],
            linewidth=args.linewidth)
            if args.writeFFT:
                np.savetxt(seismo.name+".fft",np.dstack((freq_seismo,Sf*factorFirstFile/factorSecondFile))[0])
                print(seismo.name+".fft has been written.")
        plt.xlim(freq_seismo[0], freq_seismo[-1])
        if args.invert_yaxis:
            plt.gca().invert_yaxis()
        plt.grid(args.grid)
        plt.hold(args.hold)
        if plot_legend:
            plt.legend(fontsize=args.fontsize,loc=legend_loc)
        if not default_legend:
           plt.rc('text', usetex=True)
        plt.rc('font', family='serif')
        font = {'family' : 'normal',
        'weight' : 'bold',
        'size'   : args.fontsize}
        plt.rc('font', **font)
        plt.xlabel(args.xlabel,fontsize=args.fontsize+2)
        plt.ylabel(args.ylabel,fontsize=args.fontsize+2)

    elif plot_specgram:
        # Pxx is the segments x freqs array of instantaneous power, freqs is
        # the frequency vector, bins are the centers of the time bins in which
        # the power is computed, and im is the matplotlib.image.AxesImage
        # instance
        Fs = int(1.0/dt)  # the sampling frequency
        if t_seismo[0] < 0:
            t_seismo = t_seismo - t_seismo[0]
        if fact == -1:
            fact=100
        ax1 = plt.subplot(211)
        plt.title(seismo.name)
        plt.plot(t_seismo,ampl_seismo,label=user_labels[idx])
        plt.subplot(212, sharex=ax1)
        im=spectrogram(ampl_seismo, Fs, wlen = Fs/fact,show=False,axes=plt.gca())
        plt.xlim(tmin, tmax)
        if args.invert_yaxis:
            if not y_axis_already_inverted:
                plt.gca().invert_yaxis()
                y_axis_already_inverted = True
        plt.ylim(0,Fs/2.0)
        if plot_legend:
            plt.legend(loc=legend_loc)

    else:
        if args.verbose:
            print("Mean absolute value of:",seismo.name,":",np.mean(abs(ampl_seismo)))
        if scaleFilesWithFirstOne:
            if seismo != args.files[0]:
                factorFirstFile = args.factor
            else:
                factorFirstFile = 1.0
            if args.normalize:
                factorSecondFile = max(abs(ampl_seismo))
            else:
                factorSecondFile = 1.0
        else:
            if args.normalize:
                factorSecondFile = max(abs(ampl_seismo))/args.factor
            else:
                factorSecondFile = 1.0/args.factor
        if default_colors:
            if args.invert_axis:
                if not args.semilogy:
                    plt.plot(ampl_seismo*factorFirstFile/factorSecondFile,t_seismo+t_shift,args.plot_option,
                    linewidth=args.linewidth,label=user_labels[idx])
                else:
                    plt.semilogy(ampl_seismo*factorFirstFile/factorSecondFile,t_seismo+t_shift,args.plot_option,
                    linewidth=args.linewidth,label=user_labels[idx])
            else:
                if not args.semilogy:
                    plt.plot(t_seismo+t_shift, ampl_seismo*factorFirstFile/factorSecondFile,args.plot_option,
                    linewidth=args.linewidth,label=user_labels[idx])
                else:
                    plt.semilogy(t_seismo+t_shift, ampl_seismo*factorFirstFile/factorSecondFile,args.plot_option,
                    linewidth=args.linewidth,label=user_labels[idx])
        else:
            if args.invert_axis:
                if not args.semilogy:
                    plt.plot(ampl_seismo*factorFirstFile/factorSecondFile,t_seismo+t_shift,args.plot_option,color=user_colors[idx],
                    linewidth=args.linewidth,label=user_labels[idx])
                else:
                    plt.semilogy(ampl_seismo*factorFirstFile/factorSecondFile,t_seismo+t_shift,args.plot_option,color=user_colors[idx],
                    linewidth=args.linewidth,label=user_labels[idx])
            else:
                if not args.semilogy:
                    plt.plot(t_seismo+t_shift, ampl_seismo*factorFirstFile/factorSecondFile,args.plot_option,color=user_colors[idx],
                    linewidth=args.linewidth,label=user_labels[idx])
                else:
                    plt.semilogy(t_seismo+t_shift, ampl_seismo*factorFirstFile/factorSecondFile,args.plot_option,color=user_colors[idx],
                    linewidth=args.linewidth,label=user_labels[idx])
        if not args.invert_axis:
            plt.xlim(tmin, tmax)
        else:
            plt.ylim(tmin, tmax)
        plt.grid(args.grid)
        plt.hold(args.hold)
        font = {'family' : 'serif',
        'size'   : args.fontsize}
        plt.rc('font', **font)
        plt.xlabel(args.xlabel,fontsize=args.fontsize+2)
        plt.ylabel(args.ylabel,fontsize=args.fontsize+2)
        if plot_legend:
            plt.legend(loc=legend_loc)
        if not default_legend:
           if args.hold or plot_specgram:
               plt.rc('text', usetex=True)
        if args.invert_yaxis:
            if not y_axis_already_inverted:
                plt.gca().invert_yaxis()
                y_axis_already_inverted = True
    if not args.hold and not plot_specgram:
        plt.title(seismo.name)
plt.show()

