#!/usr/bin/env python3
"""Functions for handling and plotting time magnetic indices data
"""
import numpy as np
import datetime as dt
import scipy
from scipy import signal
from matplotlib import ticker
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import (MultipleLocator, AutoMinorLocator,
                               AutoLocator, FuncFormatter)

def central_diff(dataframe,**kwargs):
    """Takes central difference of the columns of a dataframe
    Inputs
        df (DataFrame)- data
        dt (int)- spacing used for denominator
        kwargs:
            fill (float)- fill value for ends of diff
    Returns
        cdiff (DataFrame)
    """
    times = dataframe.copy(deep=True).index
    df = dataframe.copy(deep=True)
    df = df.reset_index(drop=True).fillna(method='ffill')
    df_fwd = df.copy(deep=True)
    df_bck = df.copy(deep=True)
    df_fwd.index -= 1
    df_bck.index += 1
    if kwargs.get('forward',False):
        # Calculate dt at each time interval
        dt = times[1::]-times[0:-1]
        cdiff = (df_fwd-df)/(dt.seconds+dt.microseconds/1e6)
        cdiff.drop(index=[-1],inplace=True)
    else:
        # Calculate dt at each time interval
        dt = times[2::]-times[0:-2]
        diff = (df_fwd-df_bck).drop(index=[-1,0,df_bck.index[-1],
                                                df_bck.index[-2]])
        cdiff = diff/(dt.seconds+dt.microseconds/1e6)
        cdiff.loc[0] = 0
        cdiff.loc[len(cdiff)]=0
        cdiff.sort_index(inplace=True)
    cdiff.index = dataframe.index
    return cdiff

def pyplotsetup(*,mode='presentation',**kwargs):
    """Creates dictionary to send to rcParams for pyplot defaults
    Inputs
        mode(str)- default is "presentation"
        kwargs:
    """
    #Always
    settings={"text.usetex": False,
              "font.family": "sans-serif",
              "font.size": 28}
    #         "font.sans-serif": ["Helvetica"]}
    if 'presentation' in mode:
        #increase lineweights
        settings.update({'lines.linewidth': 3})
    if 'print' in mode:
        #Change colorcycler
        colorwheel = plt.cycler('color',
                ['maroon', 'magenta', 'tab:blue', 'green',
                 'tab:olive','tab:cyan'])
        settings.update({'axes.prop_cycle': colorwheel})
    elif 'digital' in mode:
        #make non white backgrounds, adjust borders accordingly
        settings.update({'axes.edgecolor': 'white',
                         'axes.labelcolor': 'white',
                         'axes.facecolor': '#375e95',
                         'figure.facecolor':'#375e95',
                         'text.color':'white',
                         'ytick.color':'white',
                         'xtick.color':'white'})
        #Change colorcycler
        colorwheel = plt.cycler('color',
                   ['#FAFFB0', 'magenta', 'peru', 'chartreuse', 'wheat',
                    'lightgrey', 'springgreen', 'coral', 'plum', 'salmon'])
        settings.update({'axes.prop_cycle': colorwheel})
    elif 'solar' in mode:
        #make non white backgrounds, adjust borders accordingly
        settings.update({'axes.edgecolor': 'white',
                         'axes.labelcolor': 'white',
                         'axes.facecolor': '#788091',
                         'figure.facecolor':'#788091',
                         'text.color':'white',
                         'ytick.color':'white',
                         'xtick.color':'white'})
        #Change colorcycler
        colorwheel = plt.cycler('color',
                   ['gold', 'aqua', 'salmon', 'darkred', 'wheat',
                    'lightgrey', 'springgreen', 'coral', 'plum', 'salmon'])
        settings.update({'axes.prop_cycle': colorwheel})
    return settings

def safelabel(label):
    """Returns str that will not break latex format
    Input
        label
    Return
        label
    """
    culprits = ['_','%']#ones that show up often
    for c in culprits:
        label = ('\\'+c).join(label.split(c))
    return label

def general_plot_settings(ax, **kwargs):
    """Sets a bunch of general settings
    Inputs
        ax
        kwargs:
            do_xlabel(boolean)- default False
            color(str)- see matplotlib named colors
            legend_loc(see pyplot)- 'upper right' etc
            iscontour(boolean)- default False
    """
    #TODO: is the missing xlabel in here?
    #Xlabel
    if kwargs.get('iscontour',False):
        ax.set_xlim(kwargs.get('xlim',None))
        ax.xaxis.set_minor_locator(AutoMinorLocator())
        if kwargs.get('do_xlabel',True):
            ax.set_xlabel(kwargs.get('xlabel',''))
    if kwargs.get('timedelta',False):
        tmin,tmax = ax.get_xlim()
        def timedelta_ticks(x,pos):
            if type(x)==type(dt.timedelta):
                hrs = x.days*24+t1.seconds/3600
            else:
                hrs = x/(1e9*3600)
            hours = int(hrs)
            minutes = (int(abs(hrs*60)%60))
            #return "{:d}:{:02d}".format(hours,minutes)
            return "{:d}".format(hours)
        #Get original limits
        xlims = ax.get_xlim()
        if (xlims[1]-xlims[0])*1e-9/3600 > 4.5:
            #Manually adjust the xticks
            '''
            n = 3600*4.5/1e-9
            locs = [-6*n,-5*n,-4*n,-3*n,-2*n,-n,0,n,2*n,3*n,4*n,5*n,6*n]
            '''
            n = 3600*4/1e-9
            locs = [i*n for i in range(-100,100)]
            #locs = [-6*n,-5*n,-4*n,-3*n,-2*n,-n,0,n,2*n,3*n,4*n,5*n,6*n]
        else:
            n = 3600*0.5/1e-9
            locs = [-8*n,-7*n,-6*n,-5*n,-4*n,-3*n,-2*n,-n,0,n,2*n,3*n]
        locs = [np.round(l/1e10)*1e10 for l in locs]
        ax.xaxis.set_ticks(locs)
        formatter = FuncFormatter(timedelta_ticks)
        ax.xaxis.set_major_formatter(formatter)
        #ax.xaxis.set_minor_locator(AutoMinorLocator(3))
        ax.xaxis.set_minor_locator(AutoMinorLocator(4))
        #Get original limits
        ax.set_xlim(xlims)
        if kwargs.get('do_xlabel',True):
            ax.set_xlabel(
                    #kwargs.get('xlabel',r'Time $\left[ hr:min\right]$'))
                    kwargs.get('xlabel',r'Time $\left[ hr\right]$'))
        if not kwargs.get('do_xlabel',True):
            ax.xaxis.set_major_formatter(ticker.NullFormatter())
    else:
        #ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%H:%M'))
        ax.set_xlim(kwargs.get('xlim',None))
        tmin,tmax = ax.get_xlim()
        time_range = mdates.num2timedelta(tmax-tmin)
        if time_range>dt.timedelta(hours=6):
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H'))
        if kwargs.get('do_xlabel',False):
            ax.set_xlabel(kwargs.get('xlabel',r'Time $\left[ hr\right]$'))
        else:
            #ax.xaxis.set_major_formatter(mdates.DateFormatter('%-H:%M'))
            #ax.set_xlabel(
            #         kwargs.get('xlabel',r'Time $\left[ hr:Mn\right]$'))
            pass
        ax.xaxis.set_minor_locator(AutoMinorLocator(6))
    #Ylabel
    ax.set_ylim(kwargs.get('ylim',None))
    ax.yaxis.set_minor_locator(AutoMinorLocator())
    ax.set_ylabel(kwargs.get('ylabel',''))
    ax.tick_params(which='major', length=9)
    if kwargs.get('legend',True):
        ax.legend(loc=kwargs.get('legend_loc',None))

def get_omni_cdas(start,end,as_df=True,**variables):
    from cdasws import CdasWs
    import pandas as pd
    if type(start)==pd._libs.tslibs.timestamps.Timestamp:
        start = dt.datetime.fromtimestamp(start.timestamp())
        end = dt.datetime.fromtimestamp(end.timestamp())
    cdas = CdasWs()
    omni_allvars = cdas.get_variables('OMNI_HRO_1MIN')
    omni_vars = ['SYM_H']
    for var in variables:
        if var in omni_allvars:
            omni_vars.append(var)
    status,omni = cdas.get_data('OMNI_HRO_1MIN',omni_vars,start,end)
    if as_df:
        df = pd.DataFrame(omni['SYM_H'], columns=['sym_h'],
                              index=omni['Epoch'])
        return df
    else:
        return omni

def shade_plot(axis, *, do_full=False):
    """Credit Qusai from NSF proposal:
        Shade the ICME regions"""

    # ICME Timings
    def hour(minutes):
        """return hour as int from given minutes"""
        return int((minutes)/60//24)

    def minute(minutes):
        """return minute as int from given minutes"""
        return int(minutes % 60)

    # From Tuija email
    icme = (

        # (dt.datetime(2014, 2, 15, 13+hour(25), minute(25)),  # SH1
        #  dt.datetime(2014, 2, 16, 4+hour(45), minute(45)),  # EJ1
        #  dt.datetime(2014, 2, 16, 16+hour(55), minute(55))),  # ET1

        (dt.datetime(2014, 2, 18, 7+hour(6), minute(6)),  # SH2
         dt.datetime(2014, 2, 18, 15+hour(45), minute(45)),  # EJ2
         dt.datetime(2014, 2, 19, 3+hour(55), minute(55))),  # ET2

        (dt.datetime(2014, 2, 19, 3+hour(56), minute(56)),  # SH3
         dt.datetime(2014, 2, 19, 12+hour(45), minute(45)),  # EJ3
         dt.datetime(2014, 2, 20, 3+hour(9), minute(9))),  # ET3

        # (dt.datetime(2014, 2, 20, 3+hour(9), minute(9)),  # SH4
        #  dt.datetime(2014, 2, 21, 3+hour(15), minute(15)),  # EJ4
        #  dt.datetime(2014, 2, 22, 13+hour(00), minute(00))),  # ET4

        )
    fullicme = (

        (dt.datetime(2014, 2, 15, 13+hour(25), minute(25)),  # SH1
         dt.datetime(2014, 2, 16, 4+hour(45), minute(45)),  # EJ1
         dt.datetime(2014, 2, 16, 16+hour(55), minute(55))),  # ET1

        (dt.datetime(2014, 2, 18, 7+hour(6), minute(6)),  # SH2
         dt.datetime(2014, 2, 18, 15+hour(45), minute(45)),  # EJ2
         dt.datetime(2014, 2, 19, 3+hour(55), minute(55))),  # ET2

        (dt.datetime(2014, 2, 19, 3+hour(56), minute(56)),  # SH3
         dt.datetime(2014, 2, 19, 12+hour(45), minute(45)),  # EJ3
         dt.datetime(2014, 2, 20, 3+hour(9), minute(9))),  # ET3

        (dt.datetime(2014, 2, 20, 3+hour(9), minute(9)),  # SH4
         dt.datetime(2014, 2, 21, 3+hour(15), minute(15)),  # EJ4
         dt.datetime(2014, 2, 22, 13+hour(00), minute(00))),  # ET4

        )
    if do_full:
        icme = fullicme

    for num, times in enumerate(icme, start=2):
        sheath = mpl.dates.date2num(times[0])
        ejecta = mpl.dates.date2num(times[1])
        end = mpl.dates.date2num(times[2])
        axis.axvspan(sheath, ejecta, facecolor='k', alpha=0.1,
                     label=('sheath ' + str(num)))
        axis.axvspan(ejecta, end, facecolor='k', alpha=0.4,
                     label=('ejecta ' + str(num)))

def mark_times(axis):
    """Function makes vertical marks at specified time stamps
    Inputs
        axis- object to mark
    """
    #FROM Tuija Email June 20, 2021:
    '''
    % IMF changes
02 19 10 20
02 19 17 45
% Density peaks 18/12-17 UT, 19/0940-1020 UT, 19/1250-1440
02 18 12 00
02 18 17 00
02 19 09 00
02 19 10 20
02 19 12 50
02 19 14 40
% AL: substorm onsets 18/1430, 18/1615, 18/1850, 19/0030, 19/0356, 19/0900, 19/1255
02 18 14 30
02 18 16 10
02 18 18 50
02 19 00 30
02 19 03 56
02 19 09 00
02 19 12 55
    '''
    timeslist=[]
    #IMF changes
    timeslist.append([dt.datetime(2014,2,19,10,20),'IMF'])
    timeslist.append([dt.datetime(2014,2,19,17,45),'IMF'])
    #Density peaks
    timeslist.append([dt.datetime(2014,2,18,12,0),'Density'])
    timeslist.append([dt.datetime(2014,2,18,17,0),'Density'])
    timeslist.append([dt.datetime(2014,2,19,9,0),'Density'])
    timeslist.append([dt.datetime(2014,2,19,10,20),'Density'])
    timeslist.append([dt.datetime(2014,2,19,12,50),'Density'])
    timeslist.append([dt.datetime(2014,2,19,14,40),'Density'])
    #Substorm onsets based on AL
    timeslist.append([dt.datetime(2014,2,18,14,30),'Substorm'])
    timeslist.append([dt.datetime(2014,2,18,16,10),'Substorm'])
    timeslist.append([dt.datetime(2014,2,18,18,50),'Substorm'])
    timeslist.append([dt.datetime(2014,2,19,0,30),'Substorm'])
    timeslist.append([dt.datetime(2014,2,19,3,56),'Substorm'])
    timeslist.append([dt.datetime(2014,2,19,9,0),'Substorm'])
    timeslist.append([dt.datetime(2014,2,19,12,55),'Substorm'])
    #Colors, IMF, Density, Substorm
    colorwheel = dict({'IMF':'black',
                       'Density':'black',
                       'Substorm':'black'})
    lswheel = dict({'IMF':None,
                       'Density':None,
                       'Substorm':'--'})
    for stamp in timeslist:
        axis.axvline(stamp[0], color=colorwheel[stamp[1]],
                     linestyle=lswheel[stamp[1]], linewidth=1)

def plot_stack_distr(ax, times, mp, msdict, **kwargs):
    """Plots distribution of energies in particular zone
    Inputs
        mp(DataFrame)- total magnetosphere values
        msdict(Dict of DataFrames)- subzone values
        kwargs:
            do_xlabel(boolean)- default False
            ylabel(str)- default ''
            legend_loc(see pyplot)- 'upper right' etc
            subzone(str)- 'ms_full' is default
            value_set(str)- 'Virialvolume', 'Energy', etc
            ylim(tuple or list)- None
    """
    #Figure out value_keys and subzone
    subzone = kwargs.get('subzone', 'ms_full')
    kwargs.update({'legend_loc':kwargs.get('legend_loc','lower left')})
    if 'ms_full' in subzone:
        data = mp
    else:
        data = msdict[subzone]
    value_set = kwargs.get('value_set','Virial')
    values = {'Virial':['Virial 2x Uk [nT]', 'Virial Ub [nT]','Um [nT]',
                        'Virial Surface Total [nT]'],
              'Energy':['Virial Ub [J]', 'KE [J]', 'Eth [J]'],
              #'Energy2':['u_db [J]', 'uHydro [J]'],
              'Energy2':['uB [J]', 'uHydro [J]'],
              'Report':['Utot2 [J]', 'Utot [J]','uB [J]','uB_dipole [J]',
                        'u_db [J]', 'uHydro [J]'],
              'Virial%':['Virial 2x Uk [%]', 'Virial Ub [%]',
                               'Virial Surface Total [%]'],
              'Energy%':['Virial Ub [%]', 'KE [%]', 'Eth [%]']}
    #Get % within specific subvolume
    if '%' in value_set:
        kwargs.update({'ylim':kwargs.get('ylim',[0,100])})
        for value in values[''.join(value_set.split('%'))]:
                #find total
                if 'Virial' in value_set:
                    total = data['Virial [nT]']
                elif 'Energy' in value_set:
                    total = (data['Utot [J]']-data['uB [J]']+
                             data['Virial Ub [J]'])
                data[value.split('[')[0]+'[%]'] = data[value]/total*100
    #Optional layers depending on value_key
    starting_value = 0
    if (not '%' in value_set) and ('Virial' in value_set):
        ax.plot(times, data['Virial Surface Total [nT]'], color='#05BC54',
                linewidth=4,label='Boundary Stress')#light green color
        starting_value = data['Virial Surface Total [nT]']
        values[value_set].remove('Virial Surface Total [nT]')
        ax.axhline(0,color='white',linewidth=0.5)
    if kwargs.get('dolog',False):
        for value in values[value_set]:
            label = value.split(' [')[0].split('Virial ')[-1]
            ax.semilogy(times,data[value],label=safelabel(label))
    else:
        for value in values[value_set]:
            label = value.split(' [')[0].split('Virial ')[-1]
            ax.fill_between(times,starting_value,starting_value+data[value],
                            label=safelabel(label))
            starting_value = starting_value+data[value]
    if (not '%' in value_set) and kwargs.get('doBios',True):
        if any(['bioS' in k for k in data.keys()]):
            ax.plot(times, data['bioS [nT]'], color='white', ls='--',
                    label='BiotSavart')
    #General plot settings
    general_plot_settings(ax, **kwargs)

def plot_stack_contrib(ax, times, mp, msdict, **kwargs):
    """Plots contribution of subzone to virial Dst
    Inputs
        mp(DataFrame)- total magnetosphere values
        msdict(Dict of DataFrames)- subzone values
        kwargs:
            do_xlabel(boolean)- default False
            ylabel(str)- default ''
            legend_loc(see pyplot)- 'upper right' etc
            omni
    """
    #Figure out value_key
    value_key = kwargs.get('value_key','Virial [nT]')
    #Optional layers depending on value_key
    starting_value = 0
    if not '%' in value_key:
        ax.axhline(0,color='white',linewidth=0.5)
        if ('Virial' in value_key) or ('bioS' in value_key):
            if 'omni' in kwargs:
                ax.plot(kwargs.get('omni')['Time [UTC]'],
                        kwargs.get('omni')['sym_h'],color='white',
                        ls='--', label='SYM-H')
            else:
                print('omni not loaded! No obs comparisons!')
            '''
            try:
                if all(omni['sym_h'].isna()): raise NameError
                ax.plot(omni['Time [UTC]'],omni['sym_h'],color='white',
                    ls='--', label='SYM-H')
            except NameError:
                print('omni not loaded! No obs comparisons!')
            '''
        if ('bioS' in value_key) and ('bioS_ext [nT]' in mp.keys()):
            starting_value = mp['bioS_ext [nT]']
            starting_value = starting_value+ mp['bioS_int [nT]']
            ax.plot(times, mp['bioS_ext [nT]']+mp['bioS_int [nT]'],
                    color='#05BC54',linewidth=4,
                    label='External+Internal')#light green color
    #Plot stacks
    for i,(szlabel,sz) in enumerate([(l,z) for l,z in msdict.items()
                                     if ('closed_rc' not in l) and
                                        ('slice' not in l)]):
        print(szlabel)
        szval = sz[value_key]
        #NOTE changed just for this work
        #colorwheel = ['magenta', 'magenta', 'tab:blue']
        #colorwheel = ['maroon', 'magenta', 'tab:blue']
        colorwheel = ['magenta', 'tab:blue']
        labelwheel = ['Closed', 'Lobes']
        if szlabel=='rc':
            #kwargs['hatch'] ='x'
            #kwargs['edgecolor'] ='grey'
            pass
        else:
            kwargs['hatch'] =''
            kwargs['edgecolor'] =None
        #times, d = times[~d.isna()], d[~d.isna()]
        if kwargs.get('dolog',False):
            ax.semilogy(times,szval,label=szlabel)
        else:
            ax.fill_between(times,starting_value/kwargs.get('factor',1),
                              (starting_value+szval)/kwargs.get('factor',1),
                        label=labelwheel[i],hatch=kwargs.get('hatch'),
                            fc=colorwheel[i],
                            edgecolor=kwargs.get('edgecolor',None))
            starting_value = starting_value+szval
    ax.set_xlim([times[0],times[-1]])
    #Optional plot settings
    if ('bioS' in value_key) and ('%' in value_key):
        ax.set_ylim([-100,100])
    #General plot settings
    general_plot_settings(ax, **kwargs)

def plot_psd(ax, t, series, **kwargs):
    """plots estimated power spectral density from scipy.signal.periodogram
    Inputs
        ax (Axis object)- axis to plot on
        t (timeIndex)- timeseries used, only tested with equally spaced
        series array(floats)- signal data used
        kwargs:
            fs (float)- sampling frequency, will scale results
            label-
            ylim,xlabel,ylabel
    Returns
        None
    """
    f, Pxx = signal.periodogram(series,fs=kwargs.get('fs',1/300),nfft=3000)
    T_peak = (1/f[Pxx==Pxx.max()][0])/3600 #period in hours
    ax.semilogy(f*1e3,Pxx,label=kwargs.get('label',r'Virial $\Delta B$')
                                    +' Peak at  {:.2f} hrs'.format(T_peak))
    ax.set_xlim(kwargs.get('xlim',[0,0.5]))
    ax.set_ylim(kwargs.get('ylim',[1e-6*Pxx.max(),10*Pxx.max()]))
    ax.legend()
    ax.set_xlabel(kwargs.get('xlabel'))
    ax.set_ylabel(kwargs.get('ylabel'))

def plot_pearson_r(ax, tx, ty, xseries, yseries, **kwargs):
    """plots scatter with attached r correlation value for XY series
    Inputs
        ax (Axis object)- axis to plot on
        tx,ty (timeIndex)- timeseries used, only tested with equally spaced
        xseries,yseries array(floats)- signal data used
        kwargs:
            label-
            ylim,xlabel,ylabel
            skipplot- (True)
    Returns
        correlation value
    """
    #Pearson R Correlation
    xdata = np.interp(ty, tx, xseries)
    ydata = yseries.copy(deep=True).fillna(method='bfill')
    r = np.corrcoef(xdata,ydata)[0][1]
    #s = scipy.stats.spearmanr(xdata,ydata).correlation
    if (not kwargs.get('skipplot',False)) and ax!=None:
        #Plot with SW on X and Virial on Y
        ax.scatter(xdata,ydata,label='r = {:.2f}'.format(r))
        ax.legend()
        ax.set_xlabel(kwargs.get('xlabel'))
        ax.set_ylabel(kwargs.get('ylabel'))
    return r


def refactor(event,t0):
    # Gather segments of the event to pass directly to figure functions
    ev = {}
    ev['lobes'] = event['msdict']['lobes']
    ev['closed'] = event['msdict']['closed']
    ev['mp'] = event['mpdict']['ms_full']
    ev['inner'] = event['inner_mp']
    ev['sim'] = event['obs']['swmf_log']
    ev['sw'] = event['obs']['swmf_sw']
    timedelta = [t-t0 for t in event['time']]
    simtdelta = [t-t0 for t in ev['sim'].index]
    swtdelta = [t-t0 for t in ev['sw'].index]
    ev['times']=[float(n.to_numpy()) for n in timedelta]
    ev['simt']=[float(n.to_numpy()) for n in simtdelta]
    ev['swt']=[float(n.to_numpy()) for n in swtdelta]

    ## TOTAL
    #K1,5 from mp
    ev['Ks1'] = ev['mp']['K_netK1 [W]']
    ev['Ks5'] = ev['mp']['K_netK5 [W]']
    #K2,3,4 from lobes
    ev['Ks2al'] = ev['lobes']['K_netK2a [W]']
    ev['Ks2bl'] = ev['lobes']['K_netK2b [W]']
    ev['Ks3'] = ev['lobes']['K_netK3 [W]']
    ev['Ks4'] = ev['lobes']['K_netK4 [W]']
    #K2,6,7 from closed
    ev['Ks2ac'] = ev['closed']['K_netK2a [W]']
    ev['Ks2bc'] = ev['closed']['K_netK2b [W]']
    ev['Ks6'] = ev['closed']['K_netK6 [W]']
    ev['Ks7'] = ev['closed']['K_netK7 [W]']

    ## HYDRO
    #H1,5 from mp
    ev['Hs1'] = ev['mp']['P0_netK1 [W]']
    ev['Hs5'] = ev['mp']['P0_netK5 [W]']
    #H2,3,4 from lobes
    ev['Hs2al'] = ev['lobes']['P0_netK2a [W]']
    ev['Hs2bl'] = ev['lobes']['P0_netK2b [W]']
    ev['Hs3'] = ev['lobes']['P0_netK3 [W]']
    ev['Hs4'] = ev['lobes']['P0_netK4 [W]']
    #H2,6,7 from closed
    ev['Hs2ac'] = ev['closed']['P0_netK2a [W]']
    ev['Hs2bc'] = ev['closed']['P0_netK2b [W]']
    ev['Hs6'] = ev['closed']['P0_netK6 [W]']
    ev['Hs7'] = ev['closed']['P0_netK7 [W]']

    ## MAG
    #S1,5 from mp
    ev['Ss1'] = ev['mp']['ExB_netK1 [W]']
    ev['Ss5'] = ev['mp']['ExB_netK5 [W]']
    #S2,3,4 from lobes
    ev['Ss2al'] = ev['lobes']['ExB_netK2a [W]']
    ev['Ss2bl'] = ev['lobes']['ExB_netK2b [W]']
    ev['Ss3'] = ev['lobes']['ExB_netK3 [W]']
    ev['Ss4'] = ev['lobes']['ExB_netK4 [W]']
    #S2,6,7 from closed
    ev['Ss2ac'] = ev['closed']['ExB_netK2a [W]']
    ev['Ss2bc'] = ev['closed']['ExB_netK2b [W]']
    ev['Ss6'] = ev['closed']['ExB_netK6 [W]']
    ev['Ss7'] = ev['closed']['ExB_netK7 [W]']

    ## TOTAL
    #M1,5,total from mp
    ev['M1'] = ev['mp']['UtotM1 [W]'].fillna(value=0)
    ev['M5'] = ev['mp']['UtotM5 [W]'].fillna(value=0)
    ev['M'] = ev['mp']['UtotM [W]'].fillna(value=0)
    ev['MM'] = ev['mp']['MM [kg/s]'].fillna(value=0)
    #M1a,1b,2b,il from lobes
    ev['M1a'] = ev['lobes']['UtotM1a [W]'].fillna(value=0)
    ev['M1b'] = ev['lobes']['UtotM1b [W]'].fillna(value=0)
    ev['M2b'] = ev['lobes']['UtotM2b [W]'].fillna(value=0)
    ev['M2d'] = ev['lobes']['UtotM2d [W]'].fillna(value=0)
    ev['Mil'] = ev['lobes']['UtotMil [W]'].fillna(value=0)
    #M5a,5b,2a,ic from closed
    ev['M5a'] = ev['closed']['UtotM5a [W]'].fillna(value=0)
    ev['M5b'] = ev['closed']['UtotM5b [W]'].fillna(value=0)
    ev['M2a'] = ev['closed']['UtotM2a [W]'].fillna(value=0)
    ev['M2c'] = ev['closed']['UtotM2c [W]'].fillna(value=0)
    ev['Mic'] = ev['closed']['UtotMic [W]'].fillna(value=0)

    ev['M_lobes'] = ev['M1a']+ev['M1b']-ev['M2a']+ev['M2b']-ev['M2c']+ev['M2d']
    ev['M_closed'] = ev['M5a']+ev['M5b']+ev['M2a']-ev['M2b']+ev['M2c']-ev['M2d']

    ## HYDRO
    #HM1,5,total from mp
    ev['HM1'] = ev['mp']['uHydroM1 [W]'].fillna(value=0)
    ev['HM5'] = ev['mp']['uHydroM5 [W]'].fillna(value=0)
    ev['HM'] = ev['mp']['uHydroM [W]'].fillna(value=0)
    #HM1a,1b,2b,il from lobes
    ev['HM1a'] = ev['lobes']['uHydroM1a [W]'].fillna(value=0)
    ev['HM1b'] = ev['lobes']['uHydroM1b [W]'].fillna(value=0)
    ev['HM2b'] = ev['lobes']['uHydroM2b [W]'].fillna(value=0)
    ev['HM2d'] = ev['lobes']['uHydroM2d [W]'].fillna(value=0)
    ev['HMil'] = ev['lobes']['uHydroMil [W]'].fillna(value=0)
    #HM5a,5b,2a,ic from closed
    ev['HM5a'] = ev['closed']['uHydroM5a [W]'].fillna(value=0)
    ev['HM5b'] = ev['closed']['uHydroM5b [W]'].fillna(value=0)
    ev['HM2a'] = ev['closed']['uHydroM2a [W]'].fillna(value=0)
    ev['HM2c'] = ev['closed']['uHydroM2c [W]'].fillna(value=0)
    ev['HMic'] = ev['closed']['uHydroMic [W]'].fillna(value=0)

    ev['HM_lobes'] = ev['HM1a']+ev['HM1b']-ev['HM2a']+ev['HM2b']-ev['HM2c']+ev['HM2d']
    ev['HM_closed'] = ev['HM5a']+ev['HM5b']+ev['HM2a']-ev['HM2b']+ev['HM2c']-ev['HM2d']

    ## MAG
    #SM1,5,total from mp
    ev['SM1'] = ev['mp']['uBM1 [W]'].fillna(value=0)
    ev['SM5'] = ev['mp']['uBM5 [W]'].fillna(value=0)
    ev['SM'] = ev['mp']['uBM [W]'].fillna(value=0)
    #HM1a,1b,2b,il from lobes
    ev['SM1a'] = ev['lobes']['uBM1a [W]'].fillna(value=0)
    ev['SM1b'] = ev['lobes']['uBM1b [W]'].fillna(value=0)
    ev['SM2b'] = ev['lobes']['uBM2b [W]'].fillna(value=0)
    ev['SM2d'] = ev['lobes']['uBM2d [W]'].fillna(value=0)
    ev['SMil'] = ev['lobes']['uBMil [W]'].fillna(value=0)
    #SM5a,5b,2a,ic from closed
    ev['SM5a'] = ev['closed']['uBM5a [W]'].fillna(value=0)
    ev['SM5b'] = ev['closed']['uBM5b [W]'].fillna(value=0)
    ev['SM2a'] = ev['closed']['uBM2a [W]'].fillna(value=0)
    ev['SM2c'] = ev['closed']['uBM2c [W]'].fillna(value=0)
    ev['SMic'] = ev['closed']['uBMic [W]'].fillna(value=0)

    ev['SM_lobes'] = ev['SM1a']+ev['SM1b']-ev['SM2a']+ev['SM2b']-ev['SM2c']+ev['SM2d']
    ev['SM_closed'] = ev['SM5a']+ev['SM5b']+ev['SM2a']-ev['SM2b']+ev['SM2c']-ev['SM2d']

    ev['Uclosed'] = ev['closed']['Utot [J]']
    ev['Ulobes'] = ev['lobes']['Utot [J]']
    ev['U'] = ev['mp']['Utot [J]']
    # Central difference of partial volume integrals, total change
    # Total
    ev['K_cdiff_closed'] = -1*central_diff(ev['closed']['Utot [J]'])
    ev['K_cidff_lobes'] = -1*central_diff(ev['lobes']['Utot [J]'])
    ev['K_cdiff_mp'] = -1*central_diff(ev['mp']['Utot [J]'])
    # Hydro
    ev['H_cdiff_closed'] = -1*central_diff(ev['closed']['uHydro [J]'])
    ev['H_cdiff_lobes'] = -1*central_diff(ev['lobes']['uHydro [J]'])
    ev['H_cdiff_mp'] = -1*central_diff(ev['mp']['uHydro [J]'])
    # Mag
    ev['S_cdiff_closed'] = -1*central_diff(ev['closed']['uB [J]'])
    ev['S_cdiff_lobes'] = -1*central_diff(ev['lobes']['uB [J]'])
    ev['S_cdiff_mp'] = -1*central_diff(ev['mp']['uB [J]'])
    ev['dDstdt_sim'] = -1*central_diff(ev['sim']['dst_sm'])

    ev['K1'] = ev['Ks1']+ev['M1']
    ev['K5'] = ev['Ks5']+ev['M5']
    ev['K2a'] = ev['Ks2ac']+ev['M2a']+ev['M2c']
    ev['K2b'] = ev['Ks2bc']-ev['M2b']-ev['M2d']
    ev['Ksum'] = (ev['Ks1']+ev['Ks3']+ev['Ks4']+ev['Ks5']+ev['Ks6']+ev['Ks7']+
                  ev['M1']+ev['M5'])

    ev['dt'] = [(t1-t0)/1e9 for t0,t1 in zip(ev['times'][0:-1],ev['times'][1::])]
    ev['dt'].append(ev['dt'][-1])
    return ev

def ie_refactor(event,t0):
    # Name the top level
    ev = {}
    ev['ie_surface_north'] = event['/ionosphere_north_surface']
    ev['ie_surface_south'] = event['/ionosphere_south_surface']
    ev['term_north'] = event['/terminatornorth']
    ev['term_south'] = event['/terminatorsouth']
    timedelta = [t-t0 for t in ev['term_north'].index]
    ev['ie_times']=[float(n.to_numpy()) for n in timedelta]
    #TODO if not already in
    '''
    ev['sw'] = ev['obs']['swmf_sw']
    ev['swt'] = sw.index
    ev['log'] = ev['obs']['swmf_log']
    ev['logt'] = log.index
    '''
    #ev['ielogt = dataset[event]['obs']['ie_log'].index
    # Name more specific stuff
    ev['ie_dayFlux_north']=ev['ie_surface_north']['Bf_injectionPolesDayN [Wb]']
    ev['ie_dayFlux_south']=ev['ie_surface_south']['Bf_escapePolesDayS [Wb]']
    ev['ie_nightFlux_north'] = ev['ie_surface_north'][
                                             'Bf_injectionPolesNightN [Wb]']
    ev['ie_nightFlux_south'] = ev['ie_surface_south'][
                                             'Bf_escapePolesNightS [Wb]']
    ev['ie_night2dayNet_north'] = ev['term_north']['dPhidt_net [Wb/s]']
    ev['ie_night2dayNet_south'] = ev['term_south']['dPhidt_net [Wb/s]']
    ev['ie_allFlux']=(abs(ev['ie_dayFlux_north'])+abs(ev['ie_dayFlux_south'])+
                  abs(ev['ie_nightFlux_north'])+abs(ev['ie_nightFlux_south']))
    # Derive some things
    ev['dphidt_day_north'] = central_diff(abs(ev['ie_dayFlux_north']))
    ev['dphidt_day_south'] = central_diff(abs(ev['ie_dayFlux_south']))
    ev['dphidt_night_north'] = central_diff(abs(ev['ie_nightFlux_north']))
    ev['dphidt_night_south'] = central_diff(abs(ev['ie_nightFlux_south']))
    ev['dphidt'] = central_diff(ev['ie_allFlux'])
    ev['rxnDay_north'] = -ev['dphidt_day_north']+ev['ie_night2dayNet_north']
    ev['rxnDay_south'] = -ev['dphidt_day_south']+ev['ie_night2dayNet_south']
    ev['rxnNight_north']= -ev['dphidt_night_north']-ev['ie_night2dayNet_north']
    ev['rxnNight_south']= -ev['dphidt_night_south']-ev['ie_night2dayNet_south']
    return ev

if __name__ == "__main__":
    print('this module only contains helper functions and other useful '+
          'things for making plots!')
