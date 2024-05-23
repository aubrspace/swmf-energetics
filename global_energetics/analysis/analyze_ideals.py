#!/usr/bin/env python3
"""Analyze and plot data for the parameter study of ideal runs
"""
import os,sys,glob,time
import numpy as np
from numpy import abs, pi, cos, sin, sqrt, rad2deg, matmul, deg2rad
from scipy import signal
from scipy.stats import linregress
import datetime as dt
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import ticker, colors
from matplotlib.ticker import (MultipleLocator, AutoMinorLocator)
#interpackage imports
from global_energetics.analysis.plot_tools import (central_diff,
                                                   pyplotsetup,safelabel,
                                                   general_plot_settings,
                                                   plot_stack_distr,
                                                   plot_pearson_r,
                                                   plot_stack_contrib,
                                                   refactor,ie_refactor,
                                                   gmiono_refactor)
from global_energetics.analysis.proc_hdf import (load_hdf_sort)
from global_energetics.analysis.proc_indices import read_indices,ID_ALbays
from global_energetics.analysis.analyze_energetics import plot_power
from global_energetics.analysis.proc_timing import (peak2peak,
                                                    pearson_r_shifts)
from global_energetics.analysis.workingtitle import (
                                                     stack_energy_region_fig,
                                                     lobe_balance_fig,
                                                     solarwind_figure)

def interval_average(ev):
    interval_list = build_interval_list(TSTART,DT,TJUMP,
                                       ev['Ks1'].index)
    tave_ev = pd.DataFrame()
    for i,(start,end) in enumerate(interval_list):
        interv = (ev['Ks1'].index>start)&(ev['Ks1'].index<end)
        siminterv = (ev['sim'].index>start)&(ev['sim'].index<end)
        swinterv = ev['sw'].index==(start-(interval_list[0][0]-
                                           dt.datetime(2022,6,6,0,0)))
        for key in ev['sw'].keys():
            tave_ev.loc[i,key] = ev['sw'].loc[swinterv,key].mean()
        banlist = ['lobes','closed','mp','inner',
                   'sim','sw','times','simt','swt','dDstdt_sim',
                   'ie_surface_north','ie_surface_south',
                   'term_north','term_south','ie_times']
        keylist = [k for k in ev.keys() if k not in banlist]
        for key in[k for k in keylist if type(ev[k])is not type([])]:
            tave_ev.loc[i,key] = ev[key][interv].mean()
    return tave_ev

def interval_totalvariation(ev):
    interval_list = build_interval_list(TSTART,DT,TJUMP,
                                       ev['Ks1'].index)
    tv_ev = pd.DataFrame()
    for i,(start,end) in enumerate(interval_list):
        interv = (ev['Ks1'].index>start)&(ev['Ks1'].index<end)
        siminterv = (ev['sim'].index>start)&(ev['sim'].index<end)
        banlist = ['lobes','closed','mp','inner',
                   'sim','sw','times','simt','swt','dDstdt_sim',
                   'ie_surface_north','ie_surface_south',
                   'term_north','term_south','ie_times']
        keylist = [k for k in ev.keys() if k not in banlist]
        for key in[k for k in keylist if type(ev[k])is not type([])]:
            dt = [t.seconds for t in ev[key][interv].index[1::]-
                                     ev[key][interv].index[0:-1]]
            difference = abs(ev[key][interv].diff())
            variation = (difference[1::]).sum()
            #variation = (difference[1::]*dt).sum()
            tv_ev.loc[i,key] = variation
            #/abs(ev[key][interv]).mean()
            if key=='K1':
                if variation/abs(ev[key][interv]).mean()>3000:
                    print('\t',i,variation/abs(ev[key][interv]).mean())
    return tv_ev

def interval_correlation(ev,xkey,ykey,**kwargs):
    interval_list = build_interval_list(TSTART,DT,TJUMP,
                                       ev[xkey].index)
    for i,(start,end) in enumerate(interval_list):
        interv = (ev[xkey].index>start)&(ev[xkey].index<end)
        dt = [t.seconds for t in ev[xkey][interv].index[1::]-
                                 ev[xkey][interv].index[0:-1]]
        x = ev[xkey][interv].values/kwargs.get('xfactor',1)
        y = ev[ykey][interv].values/kwargs.get('yfactor',1)
        correlation = signal.correlate(x,y,mode="full")
        lags = signal.correlation_lags(x.size,y.size,mode="full")
        lag = lags[np.argmax(correlation)]
        if i==0:
            corr_ev = np.ndarray([len(interval_list),len(correlation)])
        corr_ev[i] = correlation
    return corr_ev,lags

def build_interval_list(tstart,tlength,tjump,alltimes):
    interval_list = []
    tend = tstart+tlength
    while tstart<alltimes[-1]:
        interval_list.append([tstart,tend])
        tstart+=tjump
        tend+=tjump
    return interval_list

def series_segments(event,ev,**kwargs):
    interval_list = build_interval_list(TSTART,DT,TJUMP,
                                       ev['Ks1'].index)
    #############
    #setup figure
    series_segK,(Kaxis,Kaxis2,Kaxis3) =plt.subplots(3,1,figsize=[20,24],
                                                 sharex=True)
    series_segH,(Haxis,Haxis2,Haxis3) =plt.subplots(3,1,figsize=[20,24],
                                                 sharex=True)
    series_segS,(Saxis,Saxis2,Saxis3) =plt.subplots(3,1,figsize=[20,24],
                                                 sharex=True)
    #Plot
    Kaxis.plot(ev['times'],ev['U']/1e15,label='Energy',c='grey')
    Haxis.plot(ev['times'],ev['mp']['uHydro [J]']/1e15,label='Energy',c='grey')
    Saxis.plot(ev['times'],ev['mp']['uB [J]']/1e15,label='Energy',c='grey')
    for i,(start,end) in enumerate(interval_list):
        interv = (ev['Ks1'].index>start)&(ev['Ks1'].index<end)
        interv_timedelta = [t-TSTART for t in ev['M1'][interv].index]
        interv_times=[float(n.to_numpy()) for n in interv_timedelta]

        # Total energy
        Kaxis.plot(interv_times,ev['U'][interv]/1e15,label=str(i))
        Kaxis2.plot(interv_times,
                   (ev['mp']['K_injectionK5 [W]'])[interv]/1e12,
                   label=str(i),c='red')
        Kaxis2.plot(interv_times,
                   (ev['mp']['K_escapeK5 [W]'])[interv]/1e12,
                   label=str(i),c='blue')
        Kaxis2.fill_between(interv_times,
                   (ev['mp']['K_netK5 [W]'])[interv]/1e12,
                   label=str(i),fc='grey')
        Kaxis2.fill_between(interv_times,
                   (ev['mp']['K_netK5 [W]'])[interv]/1e12,
             (ev['mp']['K_netK5 [W]']+ev['mp']['UtotM5 [W]'])[interv]/1e12,
                   label=str(i))
        Kaxis3.plot(interv_times,
                   (ev['mp']['K_injectionK1 [W]'])[interv]/1e12,
                   label=str(i),c='red')
        Kaxis3.plot(interv_times,
                   (ev['mp']['K_escapeK1 [W]'])[interv]/1e12,
                   label=str(i),c='blue')
        Kaxis3.fill_between(interv_times,
                           (ev['Ks1'])[interv]/1e12,
                   label=str(i),fc='grey')
        Kaxis3.fill_between(interv_times,
                           (ev['Ks1'])[interv]/1e12,
                           (ev['Ks1']+ev['M1'])[interv]/1e12,
                   label=str(i))
        # Hydro energy
        Haxis.plot(interv_times,ev['mp']['uHydro [J]'][interv]/1e15,
                   label=str(i))
        Haxis2.plot(interv_times,
                   (ev['mp']['P0_injectionK5 [W]'])[interv]/1e12,
                   label=str(i),c='red')
        Haxis2.plot(interv_times,
                   (ev['mp']['P0_escapeK5 [W]'])[interv]/1e12,
                   label=str(i),c='blue')
        Haxis2.fill_between(interv_times,
                   (ev['Hs5'])[interv]/1e12,
                   label=str(i),fc='grey')
        Haxis2.fill_between(interv_times,
                   (ev['Hs5'])[interv]/1e12,
                   (ev['Hs5']+ev['HM1'])[interv]/1e12,
                   label=str(i))
        Haxis3.plot(interv_times,
                   (ev['mp']['P0_injectionK1 [W]'])[interv]/1e12,
                   label=str(i),c='red')
        Haxis3.plot(interv_times,
                   (ev['mp']['P0_escapeK1 [W]'])[interv]/1e12,
                   label=str(i),c='blue')
        Haxis3.fill_between(interv_times,
                           (ev['Hs1'])[interv]/1e12,
                   label=str(i),fc='grey')
        Haxis3.fill_between(interv_times,
                           (ev['Hs1'])[interv]/1e12,
                           (ev['Hs1']+ev['HM1'])[interv]/1e12,
                   label=str(i))
        # Mag energy
        Saxis.plot(interv_times,ev['mp']['uB [J]'][interv]/1e15,label=str(i))
        Saxis2.plot(interv_times,
                   (ev['mp']['ExB_injectionK5 [W]'])[interv]/1e12,
                   label=str(i),c='red')
        Saxis2.plot(interv_times,
                   (ev['mp']['ExB_escapeK5 [W]'])[interv]/1e12,
                   label=str(i),c='blue')
        Saxis2.fill_between(interv_times,
                   (ev['Ss5'])[interv]/1e12,
                   label=str(i),fc='grey')
        Saxis2.fill_between(interv_times,
                   (ev['Ss5'])[interv]/1e12,
                   (ev['Ss5']+ev['SM1'])[interv]/1e12,
                   label=str(i))
        Saxis3.plot(interv_times,
                   (ev['mp']['ExB_injectionK1 [W]'])[interv]/1e12,
                   label=str(i),c='red')
        Saxis3.plot(interv_times,
                   (ev['mp']['ExB_escapeK1 [W]'])[interv]/1e12,
                   label=str(i),c='blue')
        Saxis3.fill_between(interv_times,
                           (ev['Ss1'])[interv]/1e12,
                   label=str(i),fc='grey')
        Saxis3.fill_between(interv_times,
                           (ev['Ss1'])[interv]/1e12,
                           (ev['Ss1']+ev['SM1'])[interv]/1e12,
                   label=str(i))


        Kaxis.axvline(float(pd.Timedelta(start-T0).to_numpy()),c='grey')
        Kaxis2.axvline(float(pd.Timedelta(start-T0).to_numpy()),c='grey')
        Kaxis3.axvline(float(pd.Timedelta(start-T0).to_numpy()),c='grey')
        Haxis.axvline(float(pd.Timedelta(start-T0).to_numpy()),c='grey')
        Haxis2.axvline(float(pd.Timedelta(start-T0).to_numpy()),c='grey')
        Haxis3.axvline(float(pd.Timedelta(start-T0).to_numpy()),c='grey')
        Saxis.axvline(float(pd.Timedelta(start-T0).to_numpy()),c='grey')
        Saxis2.axvline(float(pd.Timedelta(start-T0).to_numpy()),c='grey')
        Saxis3.axvline(float(pd.Timedelta(start-T0).to_numpy()),c='grey')
    labels = [('U','K'),('uHydro','H'),('uB','S')]
    for i,(axis,axis2,axis3) in enumerate([(Kaxis,Kaxis2,Kaxis3),
                                           (Haxis,Haxis2,Haxis3),
                                           (Saxis,Saxis2,Saxis3)]):
        general_plot_settings(axis,do_xlabel=False,legend=False,
                          ylabel=('Integrated '+labels[i][0]+
                                  r' Energy $\left[PJ\right]$'),
                          timedelta=True)
        general_plot_settings(axis2,do_xlabel=False,legend=False,
                          ylabel=('Integrated '+labels[i][1]+
                                  r'5 Flux $\left[TW\right]$'),
                          timedelta=True)
        general_plot_settings(axis3,do_xlabel=True,legend=False,
                          ylabel=('Integrated '+labels[i][1]+
                                  r'1 Flux $\left[TW\right]$'),
                          timedelta=True)
        axis.margins(x=0.01)
        axis2.margins(x=0.01)
        axis3.margins(x=0.01)
    ##Save
    series_segK.tight_layout(pad=1)
    figurename = path+'/series_seg_K_'+event+'.png'
    series_segK.savefig(figurename)
    plt.close(series_segK)
    print('\033[92m Created\033[00m',figurename)
    series_segH.tight_layout(pad=1)
    figurename = path+'/series_seg_H_'+event+'.png'
    series_segH.savefig(figurename)
    plt.close(series_segH)
    print('\033[92m Created\033[00m',figurename)
    series_segS.tight_layout(pad=1)
    figurename = path+'/series_seg_S_'+event+'.png'
    series_segS.savefig(figurename)
    plt.close(series_segS)
    print('\033[92m Created\033[00m',figurename)
    #############

def segments(event,ev,**kwargs):
    interval_list = build_interval_list(TSTART,DT,TJUMP,
                                       ev['Ks1'].index)
    #############
    #setup figure
    segments,(axis,axis2,axis3) =plt.subplots(3,1,figsize=[20,24],
                                                 sharey=False)
    #Plot
    for i,(start,end) in enumerate(interval_list):
        interv = (ev['Ks1'].index>start)&(ev['Ks1'].index<end)
        axis.plot(ev['M1'][interv].index,  ev['U'][interv]/1e15, label=str(i))
        axis2.plot(ev['M1'][interv].index,
                   (ev['mp']['K_injectionK5 [W]'])[interv]/1e12,
                   label=str(i),c='red')
        axis2.plot(ev['M1'][interv].index,
                   (ev['mp']['K_escapeK5 [W]'])[interv]/1e12,
                   label=str(i),c='blue')
        axis2.fill_between(ev['M1'][interv].index,
                   (ev['mp']['K_netK5 [W]'])[interv]/1e12,
                   label=str(i),fc='grey')
        axis2.fill_between(ev['M1'][interv].index,
                   (ev['mp']['K_netK5 [W]'])[interv]/1e12,
             (ev['mp']['K_netK5 [W]']+ev['mp']['UtotM5 [W]'])[interv]/1e12,
                   label=str(i))
        axis3.plot(ev['M1'][interv].index,(ev['Ks1']+ev['M1'])[interv]/1e12,
                   label=str(i))
    labels = [
              r'Integrated U Energy $\left[PJ\right]$',
              r'Integrated K5 Flux $\left[TW\right]$',
              r'Integrated K1 Flux $\left[TW\right]$'
              ]
    for i,ax in enumerate([axis,axis2,axis3]):
        general_plot_settings(ax,do_xlabel=(ax==axis3),legend=False,
                          ylim=[-15,5],
                          ylabel=labels[i],
                          timedelta=False)
        ax.margins(x=0.01)
    axis.set_ylabel(r'Energy $\left[PJ\right]$')
    axis.set_ylim([5,30])
    #Save
    segments.tight_layout(pad=1)
    figurename = path+'/segments'+event+'.png'
    segments.savefig(figurename)
    plt.close(segments)
    print('\033[92m Created\033[00m',figurename)

def interv_x_bar(variations,averages,event):
    #############
    #setup figure
    interv_xbar,(axis,axis2,axis3) =plt.subplots(3,1,figsize=[20,24],
                                                 sharey=True)
    #Plot
    y1s = variations['K1'].values
    y2s = variations['K5'].values
    y3s = variations['K2b'].values
    for i,(y1,y2,y3) in enumerate(zip(y1s,y2s,y3s)):
        axis.bar(i, y1, label=i)
        axis2.bar(i, y2, label=i)
        axis3.bar(i, y3, label=i)
    axis.set_ylabel(r'Tot. Variation K1 $\left[s\right]$')
    axis2.set_ylabel(r'Tot. Variation K5 $\left[s\right]$')
    axis3.set_ylabel(r'Tot. Variation K2b $\left[s\right]$')
    axis3.set_xlabel('Step ID')
    axis3.set_ylim([0,600])
    axis.margins(x=0.01)
    axis2.margins(x=0.01)
    axis3.margins(x=0.01)
    #Save
    interv_xbar.tight_layout(pad=1)
    figurename = path+'/interv_xbar_'+event+'.png'
    interv_xbar.savefig(figurename)
    plt.close(interv_xbar)
    print('\033[92m Created\033[00m',figurename)

def common_x_bar(event,ev,**kwargs):
    interval_list = build_interval_list(TSTART,DT,TJUMP,
                                       ev['Ks1'].index)
    #############
    #setup figure
    common_xbar,(axis,axis2,axis3) =plt.subplots(3,1,figsize=[20,24],
                                                 sharey=True)
    #Plot
    for i,(start,end) in enumerate(interval_list):
        interv = (ev['Ks1'].index>start)&(ev['Ks1'].index<end)
        commondelta = [t-start for t in ev['Ks1'][interv].index]
        commont = [float(n.to_numpy()) for n in commondelta]
        axis.bar(i, (ev['Ks1']+ev['M1'])[interv].mean()/1e12, label=i)
        axis2.bar(i,(ev['Ks5']+ev['M5'])[interv].mean()/1e12, label=i)
        axis3.bar(i,(ev['Ks3']+ev['Ks7'])[interv].mean()/1e12, label=i)
    axis.set_ylabel(r'Integrated Tot. Flux K1 $\left[TW\right]$')
    axis2.set_ylabel(r'Integrated Tot. Flux K5 $\left[TW\right]$')
    axis3.set_ylabel(r'Integrated Tot. Flux Kinner $\left[TW\right]$')
    axis3.set_xlabel('Step ID')
    axis3.set_ylim([-15,5])
    axis.margins(x=0.01)
    axis2.margins(x=0.01)
    axis3.margins(x=0.01)
    #Save
    common_xbar.tight_layout(pad=1)
    figurename = path+'/common_xbar_'+event+'.png'
    common_xbar.savefig(figurename)
    plt.close(common_xbar)
    print('\033[92m Created\033[00m',figurename)

def common_x_lineup(event,ev,**kwargs):
    interval_list = build_interval_list(TSTART,DT,TJUMP,
                                       ev['Ks1'].index)
    #############
    #setup figure
    common_xline,(axis,axis2,axis3) =plt.subplots(3,1,figsize=[20,24],
                                                  sharey=True)
    #Plot
    for i,(start,end) in enumerate(interval_list):
        interv = (ev['Ks1'].index>start)&(ev['Ks1'].index<end)
        commondelta = [t-start for t in ev['Ks1'][interv].index]
        commont = [float(n.to_numpy()) for n in commondelta]
        if (i)%4==0:
        #if True:
            axis.plot(commont,  ev['M1'][interv]/1e12, label=str(i))
            axis2.plot(commont, ev['Ks1'][interv]/1e12, label=str(i))
            axis3.plot(commont,(ev['Ks1']+ev['M1'])[interv]/1e12,label=str(i))
            axis.axhline(ev['M1'][interv].mean()/1e12,ls='--')
            axis2.axhline(ev['Ks1'][interv].mean()/1e12,ls='--')
            axis3.axhline((ev['Ks1']+ev['M1'])[interv].mean()/1e12,ls='--')
        for ax in [axis,axis2,axis3]:
            ax.legend()
            ax.set_ylim(-15,5)
            '''
            general_plot_settings(ax,do_xlabel=(ax==axis3),legend=True,
                          ylim=[-10,10],
                          ylabel=r'Integrated Flux $\left[TW\right]$',
                          timedelta=False)
            '''
            ax.margins(x=0.01)
    #Save
    common_xline.tight_layout(pad=1)
    figurename = path+'/common_xline_'+event+'.png'
    common_xline.savefig(figurename)
    plt.close(common_xline)
    print('\033[92m Created\033[00m',figurename)

def test_matrix(event,ev,path):
    timedelta = [t-T0 for t in dataset[event]['obs']['swmf_log'].index]
    times = [float(n.to_numpy()) for n in timedelta]
    interval_list =build_interval_list(TSTART,DT,TJUMP,dataset[event]['time'])
    #############
    #setup figure
    #matrix,(axis,axis2) =plt.subplots(2,1,figsize=[20,16],sharex=True)
    matrix,(axis) =plt.subplots(1,1,figsize=[20,8],sharex=True)
    axis.plot(ev['swt'],ev['sw']['bz'],label='bz',color='blue',lw=4)
    axis.plot(ev['swt'],ev['sw']['by'],label='by',color='magenta')
    axis.fill_between(ev['swt'],np.sqrt(ev['sw']['by']**2+ev['sw']['bz']**2),
                                        fc='grey',label='B',alpha=0.5)
    #axis2.plot(times,dataset[event]['obs']['swmf_log']['dst_sm'],label=event)
    general_plot_settings(axis,do_xlabel=True,legend=True,
                          ylabel=r'IMF $\left[nT\right]$',timedelta=True)
    #general_plot_settings(axis2,do_xlabel=True,legend=True,
    #                      ylabel=r'Dst $\left[nT\right]$',timedelta=True)
    axis.margins(x=0.01)
    matrix.tight_layout(pad=1)
    figurename = path+'/matrix'+event+'.png'
    matrix.savefig(figurename)
    plt.close(matrix)
    print('\033[92m Created\033[00m',figurename)

def plot_indices(dataset,path):
    interval_list = build_interval_list(TSTART,DT,TJUMP,
                                       dataset['stretched_MEDnHIGHu']['time'])
    colors = ['#80b3ffff','#0066ffff','#0044aaff',
              '#80ffb3ff','#2aff80ff','#00aa44ff',
              '#ffe680ff','#ffcc00ff','#806600ff']
    testpoints = ['stretched_LOWnLOWu',
                  'stretched_MEDnLOWu',
                  'stretched_HIGHnLOWu',
                  'stretched_LOWnMEDu',
                  'stretched_MEDnMEDu',
                  'stretched_HIGHnMEDu',
                  'stretched_LOWnHIGHu',
                  'stretched_MEDnHIGHu',
                  'stretched_HIGHnHIGHu']
    #############
    #setup figure
    indices,(axis,axis2) =plt.subplots(2,1,figsize=[20,16],sharex=True)
    for i,event in enumerate(testpoints):
        if event not in dataset.keys():
            continue
        timedelta = [t-T0 for t in dataset[event]['obs']['swmf_log'].index]
        times = [float(n.to_numpy()) for n in timedelta]
        #supdelta = [t-T0 for t in dataset[event]['obs']['vsupermag'].index]
        #suptimes = [float(n.to_numpy()) for n in supdelta]
        inddelta = [t-T0 for t in dataset[event]['obs']['swmf_index'].index]
        indtimes = [float(n.to_numpy()) for n in inddelta]
        axis.plot(times,
                  dataset[event]['obs']['swmf_log']['dst_sm'],
                  label=event,c=colors[i],lw=3)
        #axis2.plot(times,
        #          dataset[event]['obs']['swmf_log']['cpcpn'],
        #          label=event)
        axis2.plot(indtimes,dataset[event]['obs']['swmf_index']['AL'],
                   label=event,c=colors[i])
    for interv in interval_list:
        axis.axvline(float(pd.Timedelta(interv[0]-TSTART).to_numpy()),c='grey')
        axis2.axvline(float(pd.Timedelta(interv[0]-TSTART).to_numpy()),
                      c='grey')

    general_plot_settings(axis,do_xlabel=False,legend=False,
                          ylabel=r'Dst $\left[nT\right]$',timedelta=True)
    general_plot_settings(axis2,do_xlabel=True,legend=False,
                          ylabel=r'AL $\left[nT\right]$',timedelta=True)
    axis.margins(x=0.01)
    indices.tight_layout(pad=1)
    figurename = path+'/indices.png'
    indices.savefig(figurename)
    plt.close(indices)
    print('\033[92m Created\033[00m',figurename)

def energies(dataset,path):
    interval_list = build_interval_list(TSTART,DT,TJUMP,
                                       dataset['HIGHnHIGHu']['time'])
    #############
    #setup figure
    energies,(axis) =plt.subplots(1,1,figsize=[20,8],sharex=True)
    for event in dataset.keys():
        timedelta = [t-T0 for t in dataset[event]['time']]
        times = [float(n.to_numpy()) for n in timedelta]
        axis.plot(times,
                  dataset[event]['mpdict']['ms_full']['Utot [J]']/1e15,
                  label=event)
    for interv in interval_list:
        axis.axvline(float(pd.Timedelta(interv[0]-TSTART).to_numpy()),c='grey')

    general_plot_settings(axis,do_xlabel=True,legend=True,
                          ylabel=r'Energy $\left[PJ\right]$',timedelta=True)
    axis.margins(x=0.01)
    energies.tight_layout(pad=1)
    figurename = path+'/energies.png'
    energies.savefig(figurename)
    plt.close(energies)
    print('\033[92m Created\033[00m',figurename)

def couplers(dataset,path):
    interval_list = build_interval_list(TSTART,DT,TJUMP,
                                       dataset['HIGHnHIGHu']['time'])
    #############
    #setup figure
    couplers,(axis) =plt.subplots(1,1,figsize=[20,8],sharex=True)
    for event in dataset.keys():
        swtdelta = [t-T0 for t in dataset[event]['obs']['swmf_sw'].index]
        swtimes=[float(n.to_numpy()) for n in swtdelta]
        E0 = dataset[event]['mpdict']['ms_full']['Utot [J]'].dropna()[0]/1e15
        axis.plot(swtimes,E0+
                  dataset[event]['obs']['swmf_sw']['EinWang'].cumsum()*60/1e15,
                  #axis.plot(swtimes,dataset[event]['obs']['swmf_sw']['bz'],
                  label=event)
    for interv in interval_list:
        axis.axvline(float(pd.Timedelta(interv[0]-TSTART).to_numpy()),c='grey')

    general_plot_settings(axis,do_xlabel=True,legend=True,
                          ylabel=r'Energy $\left[PJ\right]$',timedelta=True)
    axis.margins(x=0.01)
    couplers.tight_layout(pad=1)
    figurename = path+'/couplers.png'
    couplers.savefig(figurename)
    plt.close(couplers)
    print('\033[92m Created\033[00m',figurename)

def explorer(event,ev,path):
    #############
    #setup figure
    explore1,(axis,axis2,axis3) =plt.subplots(3,1,figsize=[20,24],sharex=True)
    axis.plot(ev['swt'],ev['sw']['by'],label='by')
    axis.plot(ev['swt'],ev['sw']['bz'],label='bz')
    axis.fill_between(ev['swt'],np.sqrt(ev['sw']['by']**2+ev['sw']['bz']**2),
                                        fc='grey',label='B')

    axis2.plot(ev['times'],ev['U']/1e15,label='Energy')

    axis3.plot(ev['times'],(ev['Ks1']+ev['M1'])/1e12,label='K1')
    axis3.plot(ev['times'],(ev['Ks5']+ev['M5'])/1e12,label='K5')
    axis3.plot(ev['times'],ev['Ks3']/1e12,label='K3')
    axis3.plot(ev['times'],ev['Ks7']/1e12,label='K7')
    axis3.plot(ev['times'],ev['Ks4']/1e12,label='K4')
    axis3.plot(ev['times'],ev['Ks6']/1e12,label='K6')
    general_plot_settings(axis,do_xlabel=False,legend=True,
                          ylabel=r'IMF $\left[nT\right]$',timedelta=True)
    general_plot_settings(axis2,do_xlabel=False,legend=True,
                          ylabel=r'Energy $\left[PJ\right]$',timedelta=True)
    general_plot_settings(axis3,do_xlabel=True,legend=True,
                          ylim=[-20,18],
                          ylabel=r'Integrated Flux $\left[TW\right]$',
                          timedelta=True)
    axis.margins(x=0.01)
    axis2.margins(x=0.01)
    axis3.margins(x=0.01)
    explore1.tight_layout(pad=1)
    figurename = path+'/explore1'+event+'.png'
    explore1.savefig(figurename)
    plt.close(explore1)
    print('\033[92m Created\033[00m',figurename)



def scatter_rxn_energy(ev):
    #setup figure
    scatter_rxn,(axis) =plt.subplots(1,1,figsize=[20,20])
    #Plot
    X = ev['RXN_Day']/1e3
    Y = ev['K5']/1e12
    axis.scatter(X,Y,s=200)
    slope,intercept,r,p,stderr = linregress(X,Y)
    R2 = r**2
    linelabel = (f'K5 Flux [TW]:{slope:.2f}Eout [TW], R2={R2:.2f}')
    axis.plot(X,(intercept+X*slope),
                      label=linelabel,color='grey', ls='--')
    #Decorations
    axis.set_ylim([0,15])
    #axis.set_xlim([-5,25])
    axis.axhline(0,c='black')
    axis.axvline(0,c='black')
    axis.axline((0,0),(1,1),ls='--',c='grey')
    #axis.set_ylabel(r'-Integrated K1+K5 Flux $\left[ TW\right]$')
    axis.set_ylabel(r'Dayside Reconnection Rate $\left[Wb/s\right]$')
    axis.set_xlabel(r'Int. Energy Flux $\left[TW\right]$')
    axis.legend()
    scatter_rxn.tight_layout(pad=1)
    figurename = path+'/scatter_rxn_day.png'
    scatter_rxn.savefig(figurename)
    plt.close(scatter_rxn)
    print('\033[92m Created\033[00m',figurename)

def scatter_Ein_compare(tave):
    #############
    #setup figure
    scatter_Ein,(axis) =plt.subplots(1,1,figsize=[20,20])
    #Plot
    all_X = np.array([])
    all_Y = np.array([])
    for case in tave.keys():
        ev = tave[case]
        #axis.scatter(ev['EinWang']/1e12,-(ev['K1'])/1e12,label=case,
        #             s=200)
        #axis.scatter(ev['EinWang']/1e12,
        #             -(ev['K5']+ev['K1']+ev['Ks6']+ev['Ks4'])/1e12,
        #             label=case,s=200)
        axis.scatter(ev['EinWang']/1e12,-(ev['K1'])/1e12,label=case,
                     s=200)
        all_X = np.append(all_X,ev['EinWang'].values/1e12)
        all_Y = np.append(all_Y,-ev['K1'].values/1e12)
    slope,intercept,r,p,stderr = linregress(all_X,all_Y)
    linelabel = (f'-K1 Flux [TW]:{slope:.2f}Ein [TW], r={r:.2f}')
    axis.plot(all_X,(intercept+all_X*slope),
                      label=linelabel,color='grey', ls='--')
    #Decorations
    axis.set_ylim([-5,25])
    axis.set_xlim([-5,25])
    axis.axhline(0,c='black')
    axis.axvline(0,c='black')
    axis.axline((0,0),(1,1),ls='--',c='grey')
    #axis.set_ylabel(r'-Integrated K1+K5 Flux $\left[ TW\right]$')
    axis.set_ylabel(r'-Integrated LobeSheath K1 Flux $\left[ TW\right]$')
    axis.set_xlabel(r'Wang et. al 2014 $E_{in}\left[TW\right]$')
    axis.legend()
    scatter_Ein.tight_layout(pad=1)
    figurename = path+'/scatter_Ein.png'
    scatter_Ein.savefig(figurename)
    plt.close(scatter_Ein)
    print('\033[92m Created\033[00m',figurename)
    #############

def scatter_Pstorm(tave):
    #############
    #setup figure
    scatterPstorm,(axis) =plt.subplots(1,1,figsize=[20,20])
    #Plot
    for case in tave.keys():
        ev = tave[case]
        #axis.scatter(ev['Newell']/1e3,ev['K1']/1e12,label=case,
        #             s=200)
        axis.scatter(-ev['Pstorm']/1e12,-(ev['Ksum'])/1e12,label=case,
                     s=200)
    #Decorations
    axis.set_ylim([-5,25])
    axis.set_xlim([-5,25])
    axis.axhline(0,c='black')
    axis.axvline(0,c='black')
    axis.axline((0,0),(1,1),ls='--',c='grey')
    #axis.set_ylabel(r'-Integrated K1+K5 Flux $\left[ TW\right]$')
    axis.set_ylabel(r'-Integrated K Flux $\left[ TW\right]$')
    #axis.set_xlabel(r'Newell $\frac{d\phi}{dt}\left[kV\right]$')
    axis.set_xlabel(r'-$P_{storm}\left[TW\right]$')
    axis.legend()
    scatterPstorm.tight_layout(pad=1)
    figurename = path+'/scatter_Pstorm.png'
    scatterPstorm.savefig(figurename)
    plt.close(scatterPstorm)
    print('\033[92m Created\033[00m',figurename)

def scatter_internalFlux(tave):
    #############
    #setup figure
    scatterK2b,(axis) =plt.subplots(1,1,figsize=[20,20])
    #Plot
    shapes=['o','<','X','+','>','^']
    all_X = np.array([])
    all_Y = np.array([])
    for i,case in enumerate(tave.keys()):
        print(case, shapes[i])
        ev = tave[case]
        sc = axis.scatter(ev['Ulobes']/1e15,(ev['Ks2bl']+ev['M2b'])/1e12,
                          label=case,
                          marker=shapes[i],
                          s=200)
                          #cmap='twilight',
                          #c=(np.rad2deg(ev['clock'])+360)%360)
        all_X = np.append(all_X,ev['Ulobes'].values/1e15)
        all_Y = np.append(all_Y,(ev['Ks2bl']+ev['M2b']).values/1e12)
    slope,intercept,r,p,stderr = linregress(all_X,all_Y)
    linelabel = (f'K2b Flux [TW]:{slope:.2f}Ulobes [PJ], r={r:.2f}')
    axis.plot(all_X,(intercept+all_X*slope),
                      label=linelabel,color='grey', ls='--')

    #cbar = plt.colorbar(sc)
    #cbar.set_label(r' $\theta_{c}\left[ deg\right]$')
    #Decorations
    axis.legend()
    axis.axhline(0,c='black')
    axis.axvline(0,c='black')
    axis.set_xlabel(r'Integrated Lobe Energy $U \left[ PJ\right]$')
    axis.set_ylabel(r'Integrated Tail Flux K2b $\left[ TW\right]$')
    scatterK2b.tight_layout(pad=1)
    figurename = path+'/scatter_K2b.png'
    scatterK2b.savefig(figurename)
    plt.close(scatterK2b)
    print('\033[92m Created\033[00m',figurename)
    #############
    #setup figure
    scatterAL,(axis) =plt.subplots(1,1,figsize=[20,20])
    #Plot
    shapes=['o','<','X','+','>','^']
    all_X = np.array([])
    all_Y = np.array([])
    for i,case in enumerate(tave.keys()):
        print(case, shapes[i])
        ev = tave[case]
        sc = axis.scatter(ev['Ulobes']/1e15,(ev['al']),
                          label=case,
                          marker=shapes[i],
                          s=200)
                          #cmap='twilight',
                          #c=(np.rad2deg(ev['clock'])+360)%360)
        all_X = np.append(all_X,ev['Ulobes'].values/1e15)
        all_Y = np.append(all_Y,(ev['al']).values/1e12)
    slope,intercept,r,p,stderr = linregress(all_X,all_Y)
    linelabel = (f'AL [nT]:{slope:.2f}Ulobes [PJ], r={r:.2f}')
    axis.plot(all_X,(intercept+all_X*slope),
                      label=linelabel,color='grey', ls='--')

    #cbar = plt.colorbar(sc)
    #cbar.set_label(r' $\theta_{c}\left[ deg\right]$')
    #Decorations
    axis.legend()
    axis.axhline(0,c='black')
    axis.axvline(0,c='black')
    axis.set_xlabel(r'Integrated Lobe Energy $U \left[ PJ\right]$')
    axis.set_ylabel(r'AL $\left[ nT\right]$')
    scatterAL.tight_layout(pad=1)
    figurename = path+'/scatter_AL.png'
    scatterAL.savefig(figurename)
    plt.close(scatterAL)
    print('\033[92m Created\033[00m',figurename)

def scatter_TVexternal_K1(tv,tave,path):
    #############
    #setup figure
    scatterK1,(axis) =plt.subplots(1,1,figsize=[20,20])
    #Plot
    shapes=['o','<','X','+','>','^']
    all_X = np.array([])
    all_Y = np.array([])
    for i,case in enumerate(tv.keys()):
        #Trim > 2std fromt the mean for each case
        mean = tv[case]['K1'][tv[case]['K1']<tv[case]['K1'].max()].mean()
        std  = tv[case]['K1'][tv[case]['K1']<tv[case]['K1'].max()].std()
        cond = tv[case]['K1']<(mean+2*std)
        variation = tv[case][cond]
        average = tave[case][cond]
        sc = axis.scatter(variation['Ulobes']/1e15,(variation['K1']/1e12),
                          label=case,
                          marker=shapes[i],
                          s=200)
        all_X = np.append(all_X,variation['Ulobes'].values/1e15)
        all_Y = np.append(all_Y,variation['K1'].values/1e12)
    #axis.set_ylim(0,100)
    slope,intercept,r,p,stderr = linregress(all_X,all_Y)
    linelabel = (f'K1 T.V.:{slope:.2f}Ulobes T.V., r={r:.2f}')
    axis.plot(all_X,(intercept+all_X*slope),
                      label=linelabel,color='grey', ls='--')

    #Decorations
    axis.legend()
    axis.axhline(0,c='black')
    #axis.axvline(0,c='black')
    axis.set_xlabel(r'T.V. Lobe Energy $U \left[ PJ\right]$')
    axis.set_ylabel(r'T.V. LobeSheath Flux K1 $\left[ TW\right]$')
    scatterK1.tight_layout(pad=1)
    figurename = path+'/scatter_K1_TV.png'
    scatterK1.savefig(figurename)
    plt.close(scatterK1)
    print('\033[92m Created\033[00m',figurename)

def scatter_TVexternal_K5(tv,tave,path):
    #############
    #setup figure
    scatterK5,(axis) =plt.subplots(1,1,figsize=[20,20])
    #Plot
    shapes=['o','<','X','+','>','^']
    all_X = np.array([])
    all_Y = np.array([])
    for i,case in enumerate(tv.keys()):
        #Trim > 2std fromt the mean for each case
        mean = tv[case]['K1'][tv[case]['K1']<tv[case]['K1'].max()].mean()
        std  = tv[case]['K1'][tv[case]['K1']<tv[case]['K1'].max()].std()
        cond = tv[case]['K1']<(mean+2*std)
        variation = tv[case][cond]
        average = tave[case][cond]
        sc = axis.scatter(variation['Ulobes']/1e15,(variation['K1'])/1e12,
                          label=case,
                          marker=shapes[i],
                          s=200)
        all_X = np.append(all_X,variation['Ulobes'].values/1e15)
        all_Y = np.append(all_Y,variation['K5'].values/1e12)
    #axis.set_ylim(0,100)
    slope,intercept,r,p,stderr = linregress(all_X,all_Y)
    linelabel = (f'K1 T.V.:{slope:.2f}Ulobes T.V., r={r:.2f}')
    axis.plot(all_X,(intercept+all_X*slope),
                      label=linelabel,color='grey', ls='--')

    #Decorations
    axis.legend()
    axis.axhline(0,c='black')
    #axis.axvline(0,c='black')
    axis.set_xlabel(r'T.V. Lobe Energy $U \left[ PJ\right]$')
    axis.set_ylabel(r'T.V. ClosedSheath Flux K5 $\left[ TW\right]$')
    scatterK5.tight_layout(pad=1)
    figurename = path+'/scatter_K5_TV.png'
    scatterK5.savefig(figurename)
    plt.close(scatterK5)
    print('\033[92m Created\033[00m',figurename)

def scatter_externalFlux(tave):
    #############
    #setup figure
    scatterK1,(axis) =plt.subplots(1,1,figsize=[20,20])
    #Plot
    shapes=['o','<','X','+','>','^']
    all_X = np.array([])
    all_Y = np.array([])
    for i,case in enumerate(tave.keys()):
        print(case, shapes[i])
        ev = tave[case]
        sc = axis.scatter(ev['U']/1e15,(ev['K1'])/1e12,
                          label=case,
                          marker=shapes[i],
                          s=200)
                          #cmap='twilight',
                          #c=(np.rad2deg(ev['clock'])+360)%360)
        all_X = np.append(all_X,ev['U'].values/1e15)
        all_Y = np.append(all_Y,ev['K1'].values/1e12)
    slope,intercept,r,p,stderr = linregress(all_X,all_Y)
    linelabel = (f'K1 Flux [TW]:{slope:.2f}U [PJ], r={r:.2f}')
    axis.plot(all_X,(intercept+all_X*slope),
                      label=linelabel,color='grey', ls='--')

    #cbar = plt.colorbar(sc)
    #cbar.set_label(r' $\theta_{c}\left[ deg\right]$')
    #Decorations
    axis.legend()
    axis.axhline(0,c='black')
    axis.axvline(0,c='black')
    axis.set_xlabel(r'Integrated Energy $U \left[ PJ\right]$')
    axis.set_ylabel(r'Integrated LobeSheath Flux K1 $\left[ TW\right]$')
    scatterK1.tight_layout(pad=1)
    figurename = path+'/scatter_K1.png'
    scatterK1.savefig(figurename)
    plt.close(scatterK1)
    print('\033[92m Created\033[00m',figurename)
    #############
    #setup figure
    scatterK5,(axis) =plt.subplots(1,1,figsize=[20,20])
    #Plot
    all_X = np.array([])
    all_Y = np.array([])
    shapes=['o','<','X','+','>','^']
    for i,case in enumerate(tave.keys()):
        print(case, shapes[i])
        ev = tave[case]
        sc = axis.scatter(ev['U']/1e15,(ev['K5'])/1e12,
                          label=case,
                          marker=shapes[i],
                          s=200)
                          #cmap='twilight',
                          #c=(np.rad2deg(ev['clock'])+360)%360)
        all_X = np.append(all_X,ev['U'].values/1e15)
        all_Y = np.append(all_Y,ev['K5'].values/1e12)
    slope,intercept,r,p,stderr = linregress(all_X,all_Y)
    linelabel = (f'K5 Flux [TW]:{slope:.2f}U [PJ], r={r:.2f}')
    axis.plot(all_X,(intercept+all_X*slope),
                      label=linelabel,color='grey', ls='--')
    #cbar = plt.colorbar(sc)
    #cbar.set_label(r' $\theta_{c}\left[ deg\right]$')
    #Decorations
    axis.legend()
    axis.axhline(0,c='black')
    axis.axvline(0,c='black')
    axis.set_xlabel(r'Integrated Energy $U \left[ PJ\right]$')
    axis.set_ylabel(r'Integrated ClosedSheath Flux K1 $\left[ TW\right]$')
    scatterK5.tight_layout(pad=1)
    figurename = path+'/scatter_K5.png'
    scatterK5.savefig(figurename)
    plt.close(scatterK5)
    print('\033[92m Created\033[00m',figurename)
    #############

def scatter_cuspFlux(tave):
    #############
    #setup figure
    scatterCusp,(axis) =plt.subplots(1,1,figsize=[20,20])
    #Plot
    shapes=['o','<','X','+','>','^']
    for i,case in enumerate(tave.keys()):
        print(case, shapes[i])
        ev = tave[case]
        sc = axis.scatter(ev['Ulobes']/1e15,(ev['Ks2ac']+ev['M2a'])/1e12,
                          label=case,
                          marker=shapes[i],
                          s=200)
                          #cmap='twilight',
                          #c=(np.rad2deg(ev['clock'])+360)%360)
    #cbar = plt.colorbar(sc)
    #cbar.set_label(r' $\theta_{c}\left[ deg\right]$')
    #Decorations
    axis.legend()
    axis.axhline(0,c='black')
    axis.axvline(0,c='black')
    axis.set_xlabel(r'Integrated Lobe Energy $U \left[ PJ\right]$')
    axis.set_ylabel(r'Integrated Cusp Flux 2a $\left[ TW\right]$')
    scatterCusp.tight_layout(pad=1)
    figurename = path+'/scatter_Cusp.png'
    scatterCusp.savefig(figurename)
    plt.close(scatterCusp)
    print('\033[92m Created\033[00m',figurename)
    #############

def innerLobeFlux(tave):
    #############
    #setup figure
    scatterLobe,(axis) =plt.subplots(1,1,figsize=[20,20])
    #Plot
    shapes=['o','<','X','+','>','^']
    for i,case in enumerate(tave.keys()):
        print(case, shapes[i])
        ev = tave[case]
        sc = axis.scatter(ev['U']/1e15,(ev['Ks3'])/1e12,label=case,
                          marker=shapes[i],
                          s=200,cmap='twilight',
                          c=(np.rad2deg(ev['clock'])+360)%360)
        '''
        sc = axis.scatter(ev['bz'],(ev['K5'])/1e12,label=case,marker='o',
                        s=200,cmap='plasma',
                          #ec=ev['B_T']*1e9,
                          ec='red',fc='none')
        '''
    cbar = plt.colorbar(sc)
    #cbar.set_label('Energy [J]')
    #cbar.set_label(r'$B_{T}\left[ nT\right]$')
    cbar.set_label(r' $\theta_{c}\left[ deg\right]$')
    #Decorations
    #axis.set_xlim([0,360])
    #axis.set_ylim([-5,15])
    axis.axhline(0,c='black')
    axis.axvline(0,c='black')
    #axis.set_xlabel(r'Integrated K1 Flux $\left[ TW\right]$')
    #axis.set_xlabel(r'IMF Clock$\left[ TW\right]$')
    axis.set_xlabel(r'Integrated Energy $U \left[ PJ\right]$')
    #axis.set_ylabel(r'-Integrated K1+K5 Flux $\left[ TW\right]$')
    #axis.set_ylabel(r'-Integrated K Flux $\left[ TW\right]$')
    axis.set_ylabel(r'Integrated Inner Lobe Flux K3 $\left[ TW\right]$')
    scatterLobe.tight_layout(pad=1)
    figurename = path+'/scatter_Lobe.png'
    scatterLobe.savefig(figurename)
    plt.close(scatterLobe)
    print('\033[92m Created\033[00m',figurename)
    #############

def corr_alldata_K1(raw,path):
    #############
    #setup figures
    allscatter,(axis) =plt.subplots(1,1,figsize=[20,20])
    gridmultiplot = plt.figure(figsize=[28,28])
    grid = plt.GridSpec(3,3,hspace=0.10,top=0.95,figure=gridmultiplot)
    #Plot
    shapes=['o','<','X','+','>','^']
    all_X = np.array([])
    all_Y = np.array([])
    for i,case in enumerate(corr.keys()):
        if False:#ignore this for now
        #if case=='LOWnLOWu':
            ev = {}
            banlist = ['lobes','closed','mp','inner','dt',
                       'sim','sw','times','simt','swt','dDstdt_sim',
                       'ie_surface_north','ie_surface_south',
                       'term_north','term_south','ie_times']
            keylist = [k for k in raw[case].keys() if k not in banlist]
            for key in keylist:
                cond = raw[case][key].index>dt.datetime(2022,6,6,5)
                ev[key] = raw[case][key][cond]
        else:
            ev = raw[case]
        '''
        sc = axis.scatter(ev['RXN_Day']/1e3,(ev['K1'])/1e12,
                          label=case,
                          marker=shapes[i],
                          s=200)
        sc_color = list(plt.rcParams['axes.prop_cycle'])[i]['color']
        '''
        # Individual grid plot
        grid_axis = gridmultiplot.add_subplot(grid[i])
        for i,interv in enumerate(ev):
            grid_axis.plot(lags,interv,label=i)
        # Individual grid decorations
        grid_axis.axvline(0,c='black')
        grid_axis.title.set_text(case)
    # Save the Grid result
    figurename = path+'/gridmultiplot_correlation_K1.png'
    gridmultiplot.savefig(figurename)
    plt.close(gridmultiplot)
    print('\033[92m Created\033[00m',figurename)

def scatter_alldata_K1(raw,path):
    #############
    #setup figures
    allscatter,(axis) =plt.subplots(1,1,figsize=[20,20])
    gridscatter = plt.figure(figsize=[28,28])
    grid = plt.GridSpec(3,3,hspace=0.10,top=0.95,figure=gridscatter)
    #Plot
    shapes=['o','<','X','+','>','^']
    all_X = np.array([])
    all_Y = np.array([])
    for i,case in enumerate(raw.keys()):
        if case=='LOWnLOWu':
            ev = {}
            banlist = ['lobes','closed','mp','inner','dt',
                       'sim','sw','times','simt','swt','dDstdt_sim',
                       'ie_surface_north','ie_surface_south',
                       'term_north','term_south','ie_times']
            keylist = [k for k in raw[case].keys() if k not in banlist]
            for key in keylist:
                cond = raw[case][key].index>dt.datetime(2022,6,6,5)
                ev[key] = raw[case][key][cond]
        else:
            ev = raw[case]
        sc = axis.scatter(ev['RXN_Day']/1e3,(ev['K1'])/1e12,
                          label=case,
                          marker=shapes[i],
                          s=200)
        sc_color = list(plt.rcParams['axes.prop_cycle'])[i]['color']
        all_X = np.append(all_X,ev['RXN_Day'].values/1e3)
        all_Y = np.append(all_Y,ev['K1'].values/1e12)
        # Individual grid plot
        grid_axis = gridscatter.add_subplot(grid[i])
        grid_axis.scatter(ev['RXN_Day']/1e3,(ev['K1'])/1e12,
                          label=case,
                          marker=shapes[i],
                          c=sc_color,
                          s=200)
        # Individual grid stats
        slope,intercept,r,p,stderr = linregress(ev['RXN_Day']/1e3,
                                                ev['K1']/1e12)
        linelabel = (f'DayRXN: {slope:.2f}K1, r={r:.2f}')
        grid_axis.plot(ev['RXN_Day']/1e3,(intercept+ev['RXN_Day']/1e3*slope),
                      label=linelabel,color='grey', ls='--')
        # Individual grid decorations
        grid_axis.legend()
        grid_axis.axhline(0,c='black')
        grid_axis.axvline(0,c='black')
        grid_axis.set_ylim(-20,3)
        grid_axis.set_xlim(-750,750)
    # Save the Grid result
    figurename = path+'/gridscatter_alldata_K1.png'
    gridscatter.savefig(figurename)
    plt.close(gridscatter)
    print('\033[92m Created\033[00m',figurename)
    # Global fits
    slope,intercept,r,p,stderr = linregress(all_X,all_Y)
    linelabel = (f'DayRXN: {slope:.2f}K1, r={r:.2f}')
    axis.plot(all_X,(intercept+all_X*slope),
                      label=linelabel,color='grey', ls='--')

    #Global Decorations
    axis.legend()
    axis.axhline(0,c='black')
    axis.axvline(0,c='black')
    axis.set_ylim(-20,3)
    axis.set_xlim(-750,750)
    axis.set_xlabel(r'Day Reconnection $\frac{d\phi}{dt} \left[ kWb/s\right]$')
    axis.set_ylabel(r'LobeSheath Flux K1 $\left[ TW\right]$')
    #Global Save
    allscatter.tight_layout(pad=1)
    figurename = path+'/scatter_alldata_K1.png'
    allscatter.savefig(figurename)
    plt.close(allscatter)
    print('\033[92m Created\033[00m',figurename)


def scatters(tave):
    #############
    #setup figure
    scatter2,(axis) =plt.subplots(1,1,figsize=[20,20])
    #Plot
    shapes=['o','<','X','+','>','^']
    for i,case in enumerate(tave.keys()):
        print(case, shapes[i])
        ev = tave[case]
        sc = axis.scatter(ev['U']/1e15,(ev['Ks7'])/1e12,label=case,
                          marker=shapes[i],
                          s=200,cmap='twilight',
                          c=(np.rad2deg(ev['clock'])+360)%360)
        '''
        sc = axis.scatter(ev['bz'],(ev['K5'])/1e12,label=case,marker='o',
                        s=200,cmap='plasma',
                          #ec=ev['B_T']*1e9,
                          ec='red',fc='none')
        '''
    cbar = plt.colorbar(sc)
    #cbar.set_label('Energy [J]')
    #cbar.set_label(r'$B_{T}\left[ nT\right]$')
    cbar.set_label(r' $\theta_{c}\left[ deg\right]$')
    #Decorations
    #axis.set_xlim([0,360])
    #axis.set_ylim([-5,15])
    axis.axhline(0,c='black')
    axis.axvline(0,c='black')
    #axis.set_xlabel(r'Integrated K1 Flux $\left[ TW\right]$')
    #axis.set_xlabel(r'IMF Clock$\left[ TW\right]$')
    axis.set_xlabel(r'Integrated Energy $U \left[ PJ\right]$')
    #axis.set_ylabel(r'-Integrated K1+K5 Flux $\left[ TW\right]$')
    #axis.set_ylabel(r'-Integrated K Flux $\left[ TW\right]$')
    axis.set_ylabel(r'Integrated Inner Closed Flux K7 $\left[ TW\right]$')
    scatter2.tight_layout(pad=1)
    figurename = path+'/scatter2.png'
    scatter2.savefig(figurename)
    plt.close(scatter2)
    print('\033[92m Created\033[00m',figurename)
    #############
    #setup figure
    scatter3,(axis) =plt.subplots(1,1,figsize=[20,20])
    #Plot
    for case in tave.keys():
        print(case)
        print(np.min((np.rad2deg(ev['clock'])+360)%360))
        print(np.max((np.rad2deg(ev['clock'])+360)%360),'\n')
        ev = tave[case]
        sc = axis.scatter((np.rad2deg(ev['clock'])+360)%360,
                         (ev['Ks2ac']+ev['M2a'])/1e12,label=case,
                          s=200,cmap='plasma',c=ev['U']*1e9)
    cbar = plt.colorbar(sc)
    cbar.set_label('Energy [J]')
    #cbar.set_label(r'$B_{T}\left[ nT\right]$')
    #Decorations
    axis.set_xlim([0,360])
    #axis.set_ylim([-5,15])
    axis.axhline(0,c='black')
    axis.axvline(0,c='black')
    #axis.set_xlabel(r'Integrated K1 Flux $\left[ TW\right]$')
    axis.set_xlabel(r'IMF Clock$\left[ TW\right]$')
    axis.set_ylabel(r'Wang et. al 2014 $E_{in}\left[TW\right]$')
    #axis.set_ylabel(r'-Integrated K1+K5 Flux $\left[ TW\right]$')
    #axis.set_ylabel(r'-Integrated K Flux $\left[ TW\right]$')
    scatter3.tight_layout(pad=1)
    figurename = path+'/scatter3.png'
    scatter3.savefig(figurename)
    plt.close(scatter3)
    print('\033[92m Created\033[00m',figurename)
    #############

def energy_vs_polarcap(ev,event,path):
    interval_list = build_interval_list(TSTART,DT,TJUMP,
                                        ev['mp'].index)
    #############
    #setup figure
    Ulobe_PCflux,(Ulobe,PCflux,K3) = plt.subplots(3,1,figsize=[20,16],
                                                  sharex=True)
    #Plot
    Ulobe.plot(ev['times'],ev['Ulobes']/1e15,label='Utot')
    PCflux.plot(ev['ie_times'],ev['ie_flux']/1e9,label='PCFlux')
    K3.plot(ev['times'],ev['Ks3']/1e12,label='K3')
    #Decorate
    for interv in interval_list:
        Ulobe.axvline(float(pd.Timedelta(interv[0]-TSTART).to_numpy()),
                      c='grey')
        PCflux.axvline(float(pd.Timedelta(interv[0]-TSTART).to_numpy()),
                      c='grey')
        K3.axvline(float(pd.Timedelta(interv[0]-TSTART).to_numpy()),c='grey')
        Ulobe.axhline(0,c='black')
        PCflux.axhline(0,c='black')
        K3.axhline(0,c='black')
    general_plot_settings(Ulobe,do_xlabel=False,legend=True,
                          ylabel=r'Energy $\left[PJ\right]$',
                          timedelta=True)
    general_plot_settings(PCflux,do_xlabel=False,legend=True,
                          ylabel=r'Magnetic Flux $\left[MWb\right]$',
                          timedelta=True)
    general_plot_settings(K3,do_xlabel=True,legend=True,
                          ylabel=r'Energy Flux $\left[TW\right]$',
                          timedelta=True)
    Ulobe.margins(x=0.01)
    PCflux.margins(x=0.01)
    K3.margins(x=0.01)
    Ulobe_PCflux.tight_layout(pad=1)
    #Save
    figurename = path+'/Ulobe_PCflux_'+event+'.png'
    Ulobe_PCflux.savefig(figurename)
    plt.close(Ulobe_PCflux)
    print('\033[92m Created\033[00m',figurename)

def mpflux_vs_rxn(ev,event,path):
    interval_list = build_interval_list(TSTART,DT,TJUMP,
                                        ev['mp'].index)
    #############
    #setup figure
    Kmp_rxn,(K5_K1,DayRxn,NightRxn) = plt.subplots(3,1,figsize=[20,16],
                                                  sharex=True)
    #Plot
    K5_K1.plot(ev['times'],ev['K5']/1e12,label='K5')
    K5_K1.plot(ev['times'],ev['K1']/1e12,label='K1')
    DayRxn.plot(ev['ie_times'],ev['RXN_Day']/1e3,label='Day')
    NightRxn.plot(ev['ie_times'],ev['RXN_Night']/1e3,label='Night')
    #Decorate
    for interv in interval_list:
        K5_K1.axvline(float(pd.Timedelta(interv[0]-TSTART).to_numpy()),
                      c='grey')
        DayRxn.axvline(float(pd.Timedelta(interv[0]-TSTART).to_numpy()),
                      c='grey')
        NightRxn.axvline(float(pd.Timedelta(interv[0]-TSTART).to_numpy()),
                      c='grey')
        K5_K1.axhline(0,c='black')
        DayRxn.axhline(0,c='black')
        NightRxn.axhline(0,c='black')
    general_plot_settings(K5_K1,do_xlabel=False,legend=True,
                          ylabel=r'Int. Energy Flux $\left[TW\right]$',
                          timedelta=True)
    general_plot_settings(DayRxn,do_xlabel=False,legend=True,
                          ylabel=r'Reconnection $\left[kV\right]$',
                          ylim=[-700,700],
                          timedelta=True)
    general_plot_settings(NightRxn,do_xlabel=True,legend=True,
                          ylabel=r'Reconnection $\left[kV\right]$',
                          ylim=[-700,700],
                          timedelta=True)
    K5_K1.margins(x=0.01)
    DayRxn.margins(x=0.01)
    NightRxn.margins(x=0.01)
    Kmp_rxn.tight_layout(pad=1)
    #Save
    figurename = path+'/Kmp_rxn_'+event+'.png'
    Kmp_rxn.savefig(figurename)
    plt.close(Kmp_rxn)
    print('\033[92m Created\033[00m',figurename)

def internalflux_vs_rxn(ev,event,path,**kwargs):
    interval_list = build_interval_list(TSTART,DT,TJUMP,
                                        ev['mp'].index)
    #############
    #setup figure
    Kinternal_rxn,(K15,K2a_K2b,DayRxn,NightRxn,NetRxn,al) = plt.subplots(6,1,
                                                              figsize=[20,28],
                                                              sharex=True)
    inddelta = [t-T0 for t in dataset[event]['obs']['swmf_index'].index]
    indtimes = [float(n.to_numpy()) for n in inddelta]
    al_values = dataset[event]['obs']['swmf_index']['AL']
    if 'zoom' in kwargs:
        #zoom
        zoom = kwargs.get('zoom')
        zoomed = {}
        for key in ev.keys():
            if len(zoom)==len(ev[key]):
                zoomed[key] = np.array(ev[key])[zoom]
        ev = zoomed
        inddelta = [t-T0 for t in dataset[event]['obs']['swmf_index'].index if
                 (t>dt.datetime(2022,6,7,8,0))and(t<dt.datetime(2022,6,7,10))]
        indtimes = [float(n.to_numpy()) for n in inddelta]
        al_values = dataset[event]['obs']['swmf_index']['AL']
        al_values = al_values[(al_values.index>dt.datetime(2022,6,7,8))&
                              (al_values.index<dt.datetime(2022,6,7,10))]
    #Plot
    K15.plot(ev['times'],ev['K5']/1e12,label='K5 (ClosedMP)')
    K15.plot(ev['times'],ev['K1']/1e12,label='K1 (OpenMP)')
    K2a_K2b.plot(ev['times'],ev['K2a']/1e12,label='K2a (Cusp)')
    K2a_K2b.plot(ev['times'],ev['K2b']/1e12,label='K2b (Plasmasheet)')
    DayRxn.fill_between(ev['ie_times'],ev['RXN_Day']/1e3,label='Day',color='dimgrey')
    NightRxn.fill_between(ev['ie_times'],ev['RXN_Night']/1e3,label='Night',color='purple')
    NetRxn.fill_between(ev['ie_times'],ev['RXN']/1e3,label='NetRxn',color='black')
    al.plot(indtimes,al_values,label=event)
    #Decorate
    if 'zoom' not in kwargs:
        for interv in interval_list:
            K15.axvline(float(pd.Timedelta(interv[0]-TSTART).to_numpy()),
                            c='grey')
            K2a_K2b.axvline(float(pd.Timedelta(interv[0]-TSTART).to_numpy()),
                            c='grey')
            DayRxn.axvline(float(pd.Timedelta(interv[0]-TSTART).to_numpy()),
                            c='grey')
            NightRxn.axvline(float(pd.Timedelta(interv[0]-TSTART).to_numpy()),
                            c='grey')
            NetRxn.axvline(float(pd.Timedelta(interv[0]-TSTART).to_numpy()),
                            c='grey')
            al.axvline(float(pd.Timedelta(interv[0]-TSTART).to_numpy()),
                            c='grey')
    K15.axhline(0,c='black')
    K2a_K2b.axhline(0,c='black')
    DayRxn.axhline(0,c='black')
    NightRxn.axhline(0,c='black')
    NetRxn.axhline(0,c='black')
    al.axhline(0,c='black')
    general_plot_settings(K15,do_xlabel=False,legend=True,
                          ylabel=r'Int. Energy Flux $\left[TW\right]$',
                          timedelta=True,legend_loc='upper left')
    general_plot_settings(K2a_K2b,do_xlabel=False,legend=True,
                          ylabel=r'Int. Energy Flux $\left[TW\right]$',
                          timedelta=True)
    general_plot_settings(DayRxn,do_xlabel=False,legend=True,
                          ylabel=r'Reconnection $\left[kV\right]$',
                          ylim=[-500,400],
                          timedelta=True)
    general_plot_settings(NightRxn,do_xlabel=False,legend=True,
                          ylabel=r'Reconnection $\left[kV\right]$',
                          ylim=[-1000,1000],
                          timedelta=True)
    general_plot_settings(NetRxn,do_xlabel=False,legend=True,
                          ylabel=r'Reconnection $\left[kV\right]$',
                          ylim=[-1000,1000],
                          timedelta=True)
    general_plot_settings(al,do_xlabel=True,legend=True,
                          ylabel=r'AL $\left[nT\right]$',
                          timedelta=True)
    K15.margins(x=0.01)
    K2a_K2b.margins(x=0.01)
    DayRxn.margins(x=0.01)
    NightRxn.margins(x=0.01)
    NetRxn.margins(x=0.01)
    Kinternal_rxn.tight_layout(pad=1)
    #Save
    if 'zoom' in kwargs:
        figurename = path+'/Kinternal_rxn_'+event+'_zoomed.png'
    else:
        figurename = path+'/Kinternal_rxn_'+event+'.png'
    Kinternal_rxn.savefig(figurename)
    plt.close(Kinternal_rxn)
    print('\033[92m Created\033[00m',figurename)

def errors(ev,event,path,**kwargs):
    interval_list = build_interval_list(TSTART,DT,TJUMP,
                                        ev['mp'].index)
    if 'zoom' in kwargs:
        zoom = kwargs.get('zoom')
        window = [float(pd.Timedelta(n-TSTART).to_numpy()) for n in zoom]
    else:
        window = None
    #############
    #setup figure
    errors,(fluxes,inside) = plt.subplots(2,1,figsize=[24,16],sharex=True)
    # Get time markings that match the format
    #Plot
    # Dayside/nightside reconnection rates
    fluxes.axhline(0,c='black')
    fluxes.fill_between(ev['times'],ev['K_cdiff_mp']/1e12,label='Cdiff',
                        fc='grey')
    fluxes.plot(ev['times'],ev['Ksum']/1e12,label='Summed',c='dodgerblue',lw=3)
    fluxes.plot(ev['times'],ev['Kstatic']/1e12,label='Static',c='navy')
    #fluxes.plot(ev['times'],ev['Kstatic2']/1e12,label='Static',c='red')
    fluxes.plot(ev['times'],ev['M']/1e12,label='Motion',c='green')
    fluxes.plot(ev['times'],ev['dUdt']/1e12,label='dUdt',c='red',ls='--')
    fluxes.plot(ev['times'],(ev['dUdt']+ev['M'])/1e12,label='allVol',c='gold',
                ls='--')
    # Dayside/nightside reconnection rates
    inside.axhline(0,c='black')
    inside.plot(ev['times'],(ev['Ks3']+ev['Ks7'])/1e12,label='Inner',
                c='navy')
    inside.plot(ev['times'],(ev['Ks1']+ev['Ks5'])/1e12,label='Outer',
                c='dodgerblue')
    inside.plot(ev['times'],(ev['Ks4']+ev['Ks6'])/1e12,label='Cuttoffs',
                c='red')
    #Decorations
    general_plot_settings(fluxes,do_xlabel=True,legend=True,
          ylabel=r'$\int_{MP}{\mathbf{K}\cdot\mathbf{n}} \left[TW\right]$',
                          xlim = window,
                          ylim=[-10,5],
                          timedelta=True)
    general_plot_settings(inside,do_xlabel=True,legend=True,
          ylabel=r'$\int_{MP}{\mathbf{K}\cdot\mathbf{n}} \left[TW\right]$',
                          xlim = window,
                          ylim=[-10,5],
                          timedelta=True)
    for interv in interval_list:
        fluxes.axvline(float(pd.Timedelta(interv[0]-TSTART).to_numpy()),
                          c='grey')
    fluxes.margins(x=0.01)
    errors.tight_layout()
    #Save
    if 'zoom' in kwargs:
        figurename = (path+'/errors_'+event+'_'+
                      kwargs.get('tag','zoomed')+'.png')
    else:
        figurename = path+'/errors_'+event+'.png'
    # Save in pieces
    errors.savefig(figurename)
    print('\033[92m Created\033[00m',figurename)
    plt.close(errors)

def rxn(ev,event,path,**kwargs):
    interval_list = build_interval_list(TSTART,DT,TJUMP,
                                        ev['mp'].index)
    if 'zoom' in kwargs:
        zoom = kwargs.get('zoom')
        window = [float(pd.Timedelta(n-TSTART).to_numpy()) for n in zoom]
    else:
        window = None
    #############
    #setup figure
    RXN,(daynight) = plt.subplots(1,1,figsize=[24,8],
                                                    sharex=True)
    # Get time markings that match the format
    #Plot
    # Dayside/nightside reconnection rates
    daynight.axhline(0,c='black')
    daynight.fill_between(ev['ie_times'],ev['RXN']/1e3,label='Net',fc='grey')
    daynight.plot(ev['ie_times'],ev['RXNm_Day']/1e3,label='Day',
                  c='dodgerblue',lw=3)
    daynight.plot(ev['ie_times'],ev['RXNm_Night']/1e3,label='Night',c='navy')
    daynight.plot(ev['ie_times'],ev['RXNs']/1e3,label='Static',c='red',ls='--')
    daynight.plot(ev['ie_times'],(ev['cdiffRXN']/1e3),label='cdiff',
                  c='gold',ls='--')
    #Decorations
    general_plot_settings(daynight,do_xlabel=True,legend=True,
                          ylabel=r'$d\phi/dt \left[kV\right]$',
                          xlim = window,
                          timedelta=True)
    if 'zoom' in kwargs:
        daynight.set_ylim([ev['RXN'][(ev['RXN'].index<zoom[1])&
                                     (ev['RXN'].index>zoom[0])].min()/1e3,
                           ev['RXN'][(ev['RXN'].index<zoom[1])&
                                     (ev['RXN'].index>zoom[0])].max()/1e3])
    for interv in interval_list:
        daynight.axvline(float(pd.Timedelta(interv[0]-TSTART).to_numpy()),
                          c='grey')
    daynight.margins(x=0.01)
    RXN.tight_layout()
    #Save
    if 'zoom' in kwargs:
        figurename = (path+'/RXN_'+event+'_'+
                      kwargs.get('tag','zoomed')+'.png')
    else:
        figurename = path+'/RXN_'+event+'.png'
    # Save in pieces
    RXN.savefig(figurename)
    print('\033[92m Created\033[00m',figurename)
    plt.close(RXN)

def all_fluxes(ev,event,path,**kwargs):
    interval_list = build_interval_list(TSTART,DT,TJUMP,
                                        ev['mp'].index)
    #############
    #setup figure
    Fluxes,(Kexternal,Energy_dst,al) = plt.subplots(3,1,figsize=[24,22],
                                                    sharex=True)
    test1,(Kinternal) = plt.subplots(1,1,figsize=[24,28],sharex=True)
    # Tighten up the window
    al_values = dataset[event]['obs']['swmf_index']['AL']
    dst_values = dataset[event]['obs']['swmf_log']['dst_sm']
    if 'zoom' in kwargs:
        #zoom
        zoom = kwargs.get('zoom')
        mp_window = ((ev['mp'].index>zoom[0])&(ev['mp'].index<zoom[1]))
        index_window = (
                (dataset[event]['obs']['swmf_index']['AL'].index>zoom[0])&
                (dataset[event]['obs']['swmf_index']['AL'].index<zoom[1]))
        log_window = (
                (dataset[event]['obs']['swmf_log']['dst_sm'].index>zoom[0])&
                (dataset[event]['obs']['swmf_log']['dst_sm'].index<zoom[1]))
        zoomed = {}
        for key in ev.keys():
            if len(mp_window)==len(ev[key]):
                zoomed[key] = np.array(ev[key])[mp_window]
        ev = zoomed
        al_values = dataset[event]['obs']['swmf_index']['AL'][index_window]
        dst_values = dataset[event]['obs']['swmf_log']['dst_sm'][log_window]
    # Get time markings that match the format
    inddelta = [t-T0 for t in al_values.index]
    indtimes = [float(n.to_numpy()) for n in inddelta]
    logdelta = [t-T0 for t in dst_values.index]
    logtimes = [float(n.to_numpy()) for n in logdelta]
    #Plot
    # External Energy Flux
    Kexternal.fill_between(ev['times'],ev['K1']/1e12,label='K1 (OpenMP)',
                   fc='blue')
    Kexternal.fill_between(ev['times'],ev['K5']/1e12,label='K5 (ClosedMP)',
                   fc='red')
    #Kexternal.plot(ev['times'],ev['Ks4']/1e12,label='K4 (OpenTail)',
    #               color='grey')
    #Kexternal.plot(ev['times'],ev['Ks6']/1e12,label='K6 (ClosedTail)',
    #               color='black')
    Kexternal.plot(ev['times'],-ev['sw']['EinWang']/1e12,
                   c='black',lw='4',label='Wang2014')
    Kexternal.plot(ev['times'],ev['sw']['Pstorm']/1e12,
                   c='grey',lw='4',label='Tenfjord and Østgaard 2013')
    # Internal Energy Flux
    Kinternal.plot(ev['times'],ev['K2a']/1e12,label='K2a (Cusp)',
                   color='magenta')
    Kinternal.plot(ev['times'],ev['K2b']/1e12,label='K2b (Plasmasheet)',
                   color='dodgerblue')
    Kinternal.plot(ev['times'],ev['Ks3']/1e12,label='K3 (OpenIB)',
                   color='darkslategrey')
    Kinternal.plot(ev['times'],ev['Ks7']/1e12,label='K7 (ClosedIB)',
                   color='brown')
    # Energy and Dst
    Energy_dst.fill_between(ev['times'],-ev['U']/1e15,
                            label=r'-$\int_VU\left[\frac{J}{m^3}\right]$',
                            fc='blue',alpha=0.4)
    rax = Energy_dst.twinx()
    rax.plot(logtimes,dst_values,label='Dst (simulated)',color='black')
    # AL and GridL
    al.plot(indtimes,al_values,label='AL (simulated)',color='black')
    al.plot(ev['times'],ev['GridL'],label='GridL',color='purple')
    #Decorations
    general_plot_settings(Kexternal,do_xlabel=False,legend=True,
                          ylabel=r' $\int_S$Energy Flux $\left[TW\right]$',
                          ylim=[-25,17],
                          timedelta=True,legend_loc='lower left')
    general_plot_settings(Kinternal,do_xlabel=False,legend=True,
                          ylabel=r' $\int_S$Energy Flux $\left[TW\right]$',
                          ylim=[-30,10],
                          timedelta=True,legend_loc='lower left')
    general_plot_settings(Energy_dst,do_xlabel=False,legend=True,
                          ylabel=r'Energy $\left[PJ\right]$',
                          timedelta=True,legend_loc='lower left')
    general_plot_settings(al,do_xlabel=True,legend=True,
                          ylabel=r'$\Delta B \left[nT\right]$',
                          timedelta=True,legend_loc='lower left')
    rax.set_ylabel(r'$\Delta B \left[nT\right]$')
    rax.legend(loc='lower right')
    rax.spines
    Energy_dst.spines['left'].set_color('slateblue')
    Energy_dst.tick_params(axis='y',colors='slateblue')
    Energy_dst.yaxis.label.set_color('slateblue')
    if 'zoom' in kwargs:
        rax.set_ylim([dst_values.min(),0])
        pass
    for interv in interval_list:
        Kexternal.axvline(float(pd.Timedelta(interv[0]-TSTART).to_numpy()),
                          c='grey')
        Kinternal.axvline(float(pd.Timedelta(interv[0]-TSTART).to_numpy()),
                          c='grey')
        Energy_dst.axvline(float(pd.Timedelta(interv[0]-TSTART).to_numpy()),
                          c='grey')
        al.axvline(float(pd.Timedelta(interv[0]-TSTART).to_numpy()),
                          c='grey')
    Kexternal.axhline(0,c='black')
    Kinternal.axhline(0,c='black')
    Energy_dst.axhline(0,c='black')
    al.axhline(0,c='black')
    Kexternal.margins(x=0.01)
    Kinternal.margins(x=0.01)
    Energy_dst.margins(x=0.01)
    al.margins(x=0.01)
    Fluxes.tight_layout()
    #Save
    if 'zoom' in kwargs:
        figurename = (path+'/Fluxes_'+event+'_'+
                      kwargs.get('tag','zoomed')+'.png')
    else:
        figurename = path+'/Fluxes_'+event+'.png'
    # Save in pieces
    Fluxes.savefig(figurename)
    print('\033[92m Created\033[00m',figurename)
    '''
    axes = [al,Energy_dst,Kexternal]#from bot to top
    height = 22
    for i,ax in enumerate(axes[0:-1]):
        #axes[i+1].set_xticklabels(ax.get_xticklabels(),visible=True)
        axes[i+1].xaxis.set_tick_params(which='both', labelbottom=True)
        axes[i+1].xaxis.set_major_formatter(ax.xaxis.get_major_formatter())
        ax.remove()
        if i==1: rax.remove()
        axes[i+1].set_xlabel(r'Time $\left[ hr\right]$')
        height = height-6
        subname = figurename.replace('.png',f'_{i}.png')
        #Fluxes.set_size_inches(24,height,forward=True)
        Fluxes.savefig(subname)
        print('\033[92m Created\033[00m',subname)
    '''
    plt.close(Fluxes)

def build_events(ev,run,**kwargs):
    events = pd.DataFrame()
    ## ID types of events
    # Construction (test matrix) signatures
    events['imf_transients'] = ID_imftransient(ev,**kwargs)
    # Internal process signatures
    events['DIP'] = ID_dipolarizations(ev,**kwargs)
    events['plasmoids_volume'] = ID_plasmoids(ev,mode='volume')
    events['plasmoids_mass'] = ID_plasmoids(ev,mode='mass')
    events['plasmoids'] = events['plasmoids_mass']*events['plasmoids_volume']
    events['ALbays'],events['ALonsets'],events['ALpsuedos'] = ID_ALbays(ev)
    events['MGLbays'],events['MGLonsets'],events['MGLpsuedos'] = ID_ALbays(ev,
                                                              al_series='MGL')
    # ID MPBs
    events['substorm'] = np.ceil((events['DIP']+
                                  events['plasmoids_volume']+
                                  events['plasmoids_mass']+
                                  events['MGLbays']+
                                  events['ALbays'])/5)
    # Coupling variability signatures
    events['K1var'],events['K1unsteady'] = ID_variability(ev['K1'])
    events['K5var'],events['K5unsteady'] = ID_variability(ev['K5'])
    events['K15var'],events['K15unsteady'] = ID_variability(ev['K1']+ev['K5'])
    events['both'] = np.ceil((events['substorm']+events['imf_transients'])/2)
    # other combos
    return events

def ID_imftransient(ev,window=30,**kwargs):
    """Function that puts a flag for when the imf change is affecting the
        integrated results
    Inputs
        ev
        window (float) - default 30min
        kwargs:
            None
    """
    # find the times when imf change has occured
    times = ev['mp'].index
    intervals = build_interval_list(TSTART,dt.timedelta(minutes=window),TJUMP,
                                    times)
    #   add time lag from kwargs
    imftransients = np.zeros(len(times))
    for start,end in intervals:
        # mark all these as "change times"
        imftransients[(times>start) & (times<end)] = 1
    return imftransients

def ID_variability(in_signal,**kwargs):
    dt = [t.seconds for t in in_signal.index[1::]-in_signal.index[0:-1]]
    signal = in_signal.copy(deep=True).reset_index(drop=True)
    lookahead = kwargs.get('lookahead',5)
    lookbehind = kwargs.get('lookbehind',5)
    threshold = kwargs.get('threshold',56.24)
    unsteady = np.zeros(len(signal))
    var = np.zeros(len(signal))
    relvar = np.zeros(len(signal))
    for i in range(lookbehind+1,len(signal)-lookahead-1):
        # Measure the variability within a given window for each point
        var[i] = np.sum([abs(signal[k+1]-signal[k-1])/120 for k in
                                        range(i-lookbehind,i+lookahead+1)])*60
        relvar[i] = var[i]/abs(signal[i])*100
        # Assign 1/0 to if the window variability is > threshold
        unsteady[i] = var[i]>abs(signal[i])*(threshold/100)
    return relvar,unsteady

'''
def ID_ALbays(ev,**kwargs):
    if kwargs.get('criteria','BandY2017')=='BandY2017':
        # see BOROVSKY AND YAKYMENKO 2017 doi:10.1002/2016JA023625
        #   find period where SML decreases by >=150nT in 15min
        #   onset if:
        #       drops by >10nT in 2min AND
        #       >15min from last onset time
        #       Then for each onset:
        #           integrate SML for 45min forward
        #           integrate SML for 45min pior
        #           if fwd < 1.5*prior:
        #               reject as true onset
        #           NOTE (my addition)else:
        #               mark as psuedobreakup instead
        #       Keep only the first onset

        if kwargs.get('al_series','AL')=='AL':
            al_series=ev['index']['AL'].copy(deep=True).reset_index(drop=True)
        elif kwargs.get('al_series','AL')=='MGL':
            al_series=ev['maggrid']['dBmin'].copy(deep=True).reset_index(
                                                                    drop=True)
        lookahead = kwargs.get('al_lookahead',15)
        fwd_period= kwargs.get('al_fwdperiod',45)
        prior_period= fwd_period
        albay  = np.zeros(len(al_series))
        onset  = np.zeros(len(al_series))
        psuedo = np.zeros(len(al_series))
        last_i = 0
        for i,testpoint in enumerate(al_series.values[prior_period:-
                                                      fwd_period]):
            al = al_series[i]
            # find period where SML decreases by >=150nT in 15min
            if (al-al_series[i:i+lookahead].min())>150:
                # drops by >10nT in 2min AND >15min from last onset time
                if (not any(onset[i-15:i]) and
                    (al-al_series[i:i+2].min()>10)):
                    # integrate SML for 45min forward
                    fwd = np.trapz(al_series[i:i+fwd_period],dx=60)
                    # integrate SML for 45min pior
                    prior = np.trapz(al_series[i-prior_period:i],dx=60)
                    if fwd < 1.5*prior:
                        onset[i] = 1
                        isonset=True
                    else:
                        psuedo[i] = 1#NOTE
                        isonset=False
                    # If we've got one need to see how far it extends
                    i_min = al_series[i:i+lookahead].idxmin()
                    albay[i:i_min+1] = 1
                    # If it's at the end of the window, check if its continuing
                    if i_min==i+lookahead-1:
                        found_min = False
                    else:
                        found_min = True
                    while not found_min:
                        if al_series[i_min+1]<al_series[i_min]:
                            albay[i_min+1] = 1
                            i_min +=1
                            if i_min==len(al_series):
                                found_min = True
                        else:
                            found_min = True
    return albay,onset,psuedo
'''

def ID_plasmoids(ev,**kwargs):
    """Function finds plasmoid release events in timeseries
    Inputs
        ev
        kwargs:
            plasmoid_lookahead (int)- number of points to look ahead
            volume_reduction_percent (float)-
            mass_reduction_percent (float)-
    Returns
        list(bools)
    """
    lookahead = kwargs.get('plasmoid_ahead',10)
    volume = ev['closed']['Volume [Re^3]'].copy(deep=True).reset_index(
                                                                    drop=True)
    mass = ev['closed']['M [kg]'].copy(deep=True).reset_index(drop=True)
    R1 = kwargs.get('volume_reduction_percent',15)
    R2 = kwargs.get('mass_reduction_percent',10)
    # 1st measure: closed_nightside volume timeseries
    # R1% reduction in volume
    volume_reduction = np.zeros([len(volume)])
    if 'volume' in kwargs.get('mode','volume_mass'):
        for i,testpoint in enumerate(volume.values[0:-10]):
            v = volume[i]
            # Skip point if we've already got it or the volume isnt shrinking
            if not volume_reduction[i] and volume[i+1]<volume[i]:
                # Check xmin loc against lookahead points
                if (v-volume[i:i+lookahead].min())/(v)>(R1/100):
                    # If we've got one need to see how far it extends
                    i_min = volume[i:i+lookahead].idxmin()
                    volume_reduction[i:i_min+1] = 1
                    # If it's at the end of the window, check if its continuing
                    if i_min==i+lookahead-1:
                        found_min = False
                    else:
                        found_min = True
                    while not found_min:
                        if volume[i_min+1]<volume[i_min]:
                            volume_reduction[i_min+1] = 1
                            i_min +=1
                            if i_min==len(volume):
                                found_min = True
                        else:
                            found_min = True
    # 2nd measure: volume integral of density (mass) on nightside timeseries
    # R2% reduction in mass
    mass_reduction = np.zeros([len(mass)])
    if 'mass' in kwargs.get('mode','volume_mass'):
        for i,testpoint in enumerate(mass.values[0:-10]):
            m = mass[i]
            # Skip point if we've already got it or the mass isnt shrinking
            if not mass_reduction[i] and mass[i+1]<mass[i]:
                # Check xmin loc against lookahead points
                if (m-mass[i:i+lookahead].min())/(m)>(R2/100):
                    # If we've got one need to see how far it extends
                    i_min = mass[i:i+lookahead].idxmin()
                    mass_reduction[i:i_min+1] = 1
                    # If it's at the end of the window, check if its continuing
                    if i_min==i+lookahead-1:
                        found_min = False
                    else:
                        found_min = True
                    while not found_min:
                        if mass[i_min+1]<mass[i_min]:
                            mass_reduction[i_min+1] = 1
                            i_min +=1
                            if i_min==len(mass):
                                found_min = True
                        else:
                            found_min = True
    return [y1 or y2 for y1,y2 in zip(volume_reduction,mass_reduction)]

def ID_dipolarizations(ev,**kwargs):
    """Function finds dipolarizations in timeseries
    Inputs
        ev
        kwargs:
            DIP_ahead (int)- number of points to look ahead
            xline_reduction_percent (float)-
            B1_reduction_percent (float)-
    Returns
        list(bools)
    """
    lookahead = kwargs.get('DIP_ahead',10)
    xline = ev['mp']['X_NEXL [Re]'].copy(deep=True).reset_index(drop=True)
    R1 = kwargs.get('xline_reduction_percent',15)
    R2 = kwargs.get('B1_reduction_percent',15)
    # 1st measure: closed[X].min() timeseries
    # R1% reduction in -X_min distance at ANY point in the interval
    xline_reduction = np.zeros([len(xline)])
    for i,testpoint in enumerate(xline.values[0:-10]):
        x = xline[i]
        # Skip point if we've already got it or the distance isnt moving in
        if not xline_reduction[i] and xline[i+1]>xline[i]:
            # Check xmin loc against lookahead points
            if (-x+xline[i:i+lookahead].max())/(-x)>(R1/100):
                # If we've got one need to see how far it extends
                i_max = xline[i:i+lookahead].idxmax()
                xline_reduction[i:i_max+1] = 1
                # If it's at the end of the window, check if its continuing
                if i_max==i+lookahead-1:
                    found_max = False
                else:
                    found_max = True
                while not found_max:
                    if xline[i_max+1]>xline[i_max]:
                        xline_reduction[i_max+1] = 1
                        i_max +=1
                        if i_max==len(xline):
                            found_max = True
                    else:
                        found_max = True
    # 2nd measure: volume_int{(B-Bdipole)} on nightside timeseries
    # R2% reduction in volume_int{B-Bd} at ANY point in the interval
    #TODO
    b1_reduction = np.zeros([len(xline)])
    return [yes1 or yes2 for yes1,yes2 in zip(xline_reduction,b1_reduction)]

def tshift_scatter(ev,xkey,ykey,run,path):
    X = ev[xkey]
    Y = ev[ykey]/1e12
    slope,intercept,r,p,stderr = linregress(X,Y)
    # Find time lag
    best_lag = -30
    best_corr = 0
    corr = np.zeros(len(range(-30,90)))
    for i,lag in enumerate(range(-30,90)):
        if lag>0:
            x = X[lag::]
            y = Y[0:-lag]
        elif lag<0:
            x = X[0:lag]
            y = Y[-lag::]
        slope,intercept,r,p,stderr = linregress(x,y)
        corr[i] = r**2
        if r**2>best_corr**2:
            best_corr = r
            best_lag = lag
            best_x = x
            best_y = y
            best_intercept = intercept
            best_slope = slope
    #setup figure
    #scatter,(shifted,unshifted) =plt.subplots(1,2,figsize=[30,20])
    scatter = plt.figure(figsize=[20,20],layout="constrained")
    spec = scatter.add_gridspec(3,2)
    unshifted = scatter.add_subplot(spec[0:2,0])
    shifted = scatter.add_subplot(spec[0:2,1])
    corrs = scatter.add_subplot(spec[2,0:2])
    #Plot
    # original
    unshifted.scatter(X,Y,s=200,c='magenta',alpha=0.3)
    uR2 = r**2
    linelabel = (f'Slope={slope:.2e} [TW/nT]\n r2={uR2:.2f},'+
                 f'shift=0min')
    unshifted.plot(X,(intercept+X*slope),
                      label=linelabel,color='grey', ls='--')
    # shifted
    shifted.scatter(best_x,best_y,s=200,c='blue',alpha=0.3)
    R2 = best_corr**2
    linelabel = (f'Slope={best_slope:.2e} [TW/nT]\n r2={R2:.2f},'+
                 f'shift={best_lag:.0f}min')
    shifted.plot(best_x,(best_intercept+best_x*best_slope),
                      label=linelabel,color='grey', ls='--')
    # R2 correlations
    corrs.plot(range(-30,90),corr,c='black')

    #Decorations
    unshifted.axhline(0,c='black')
    unshifted.axvline(0,c='black')
    unshifted.set_xlabel(xkey)
    unshifted.set_ylabel(ykey)
    unshifted.legend()
    shifted.axhline(0,c='black')
    shifted.axvline(0,c='black')
    shifted.set_xlabel(xkey)
    shifted.set_ylabel(ykey)
    shifted.legend()
    corrs.axvline(0,c='magenta',ls='--')
    corrs.axvline(best_lag,c='blue',ls='--')
    corrs.set_xlabel(r'Timeshift $\left[min\right]$')
    corrs.set_ylabel(r'$r^2$')

    # Save
    #scatter.tight_layout(pad=1)
    figurename = path+'/'+xkey+ykey+'scatter'+run+'.png'
    scatter.savefig(figurename)
    plt.close(scatter)
    print('\033[92m Created\033[00m',figurename)

def hide_zeros(values):
    return np.array([float('nan') if x==0 else x for x in values])

def show_event_hist(ev,run,events,path,**kwargs):
    #############
    #setup figure
    fig1,(k1) = plt.subplots(1,1,figsize=[10,10])

    # Plot
    bins = np.linspace(events[run]['K1var'].quantile(0.00),
                       events[run]['K1var'].quantile(0.95),51)
    q75 =events[run]['K1var'].quantile(0.75)
    mean =events[run]['K1var'].mean()
    k1.hist(events[run]['K1var'],bins=bins,fc='green')
    k1.axvline(events[run]['K1var'].quantile(0.75),c='black',lw=4)
    k1q75 = k1.text(1,0.94,r'$75^{th}$ Percentile'+f'={q75:.1f}%',
                     transform=k1.transAxes,
                     horizontalalignment='right')
    k1mean = k1.text(1,0.88,r'Mean'+f'={mean:.1f}%',
                     transform=k1.transAxes,c='grey',
                     horizontalalignment='right')
    # Decorate
    k1.set_xlabel('Total Variation of \n'+
                 r'Integrated K1 Flux $\left[\%\right]$')
    k1.set_ylabel('Counts')

    fig1.tight_layout(pad=1)
    figurename = path+'/hist_events1_'+run+'.png'
    fig1.savefig(figurename)
    plt.close(fig1)
    print('\033[92m Created\033[00m',figurename)

def show_events(ev,run,events,path,**kwargs):
    sw_intervals = build_interval_list(TSTART,DT,TJUMP,ev['mp'].index)
    interval_list =build_interval_list(T0,dt.timedelta(minutes=15),
                                      dt.timedelta(minutes=15),ev['mp'].index)
    #Set the xlimits if zooming in
    if 'zoom' in kwargs:
        window = kwargs.get('zoom')
        zdelta = [t-T0 for t in window]
        ztimes = [float(pd.Timedelta(t-T0).to_numpy()) for t in window]
    else:
        ztimes = [ev['times'][0],ev['times'][-1]]
    #Create handy variables for marking found points on curves
    foundDIP = hide_zeros(ev['mp']['X_NEXL [Re]']*events[run]['DIP'].values)
    foundK1 = hide_zeros(ev['K1']*events[run]['K1unsteady'].values)
    foundVMOID = hide_zeros(ev['closed']['Volume [Re^3]']*
                            events[run]['plasmoids_volume'].values)
    foundMMOID = hide_zeros(ev['closed']['M [kg]']*
                            events[run]['plasmoids_mass'].values)
    foundAL = hide_zeros(ev['index']['AL']*
                            events[run]['ALbays'].values)
    foundGridL = hide_zeros(ev['GridL']*
                            events[run]['MGLbays'].values)
    #############
    #setup figure
    fig1,(nexl) = plt.subplots(1,1,figsize=[24,10],sharex=True)
    fig2,(v_moids,m_moids) = plt.subplots(2,1,figsize=[24,20],
                               sharex=True)
    fig3,(albays) = plt.subplots(1,1,figsize=[24,20],sharex=True)
    fig4,(k1var,k1) = plt.subplots(2,1,figsize=[24,20],sharex=True)
    #Plot
    nexl.fill_between(ev['times'],ev['mp']['X_NEXL [Re]'],color='black')
    v_moids.fill_between(ev['times'],ev['closed']['Volume [Re^3]']/1e3,
                         color='grey')
    v_moids.fill_between(ev['times'],foundVMOID/1e3,color='green')
    m_moids.fill_between(ev['times'],ev['closed']['M [kg]']/1e3,color='purple')
    m_moids.fill_between(ev['times'],foundMMOID/1e3,color='green')
    albays.fill_between(ev['times'],ev['index']['AL'],color='grey')
    albays.fill_between(ev['times'],foundAL,color='green')
    k1.fill_between(ev['times'],ev['K1']/1e12,fc='blue')
    k1var.set_ylim([0,200])
    k1var.plot(ev['times'],events[run]['K1var'],color='green')
    #k5.plot(ev['times'],ev['K5']/1e12,color='black')
    #k5.scatter(ev['times'],ev['K5']/1e12,
    #               c=mpl.cm.viridis(events[run]['K5unsteady'].values))
    #k5rax = k5.twinx()
    #k5rax.plot(ev['times'],events[run]['K5var'],color='grey',ls='--')
    #k5rax.set_ylim([0,200])
    #k5rax.axhline(50,c='red')
    #k5rax.set_ylabel(r'10min Total Variation $\left[\%\right]$')
    # Mark onset and psuedobreakup times- AL
    '''
    i_ALonsets = (events[run]['ALonsets']==1).values
    i_ALpsuedos = (events[run]['ALpsuedos']==1).values
    ALonsets = ev['index'].loc[i_ALonsets,'AL']
    ALpsuedos = ev['index'].loc[i_ALpsuedos,'AL']
    ALonsettdelta = [t-T0 for t in ALonsets.index]
    ALonset_times = [float(n.to_numpy()) for n in ALonsettdelta]
    ALpsuedotdelta = [t-T0 for t in ALpsuedos.index]
    ALpsuedo_times = [float(n.to_numpy()) for n in ALpsuedotdelta]
    albays.scatter(ALonset_times,ALonsets,marker='X',s=200)
    albays.scatter(ALpsuedo_times,ALpsuedos,marker='+',s=200)
    # Mark onset and psuedobreakup times- AL
    i_MGLonsets = (events[run]['MGLonsets']==1).values
    i_MGLpsuedos = (events[run]['MGLpsuedos']==1).values
    MGLonsets = ev['maggrid'].loc[i_MGLonsets,'dBmin']
    MGLpsuedos = ev['maggrid'].loc[i_MGLpsuedos,'dBmin']
    MGLonsettdelta = [t-T0 for t in MGLonsets.index]
    MGLonset_times = [float(n.to_numpy()) for n in MGLonsettdelta]
    MGLpsuedotdelta = [t-T0 for t in MGLpsuedos.index]
    MGLpsuedo_times = [float(n.to_numpy()) for n in MGLpsuedotdelta]
    albays.scatter(MGLonset_times,MGLonsets,marker='X',s=200)
    albays.scatter(MGLpsuedo_times,MGLpsuedos,marker='+',s=200)
    '''
    #Decorate
    for i,(start,end) in enumerate(interval_list):
        interv = (ev['mp'].index>start)&(ev['mp'].index<end)
        tstart = float(pd.Timedelta(start-T0).to_numpy())
        tend = float(pd.Timedelta(end-T0).to_numpy())
        if any(events[run].loc[interv,'DIP']):
            #nexl.axvline(tstart,c='blue')
            #nexl.axvspan(tstart,tend,alpha=0.2,fc='green')
            #nexl.axvline(tend,c='lightblue')
            pass
        if any(events[run].loc[interv,'plasmoids_volume']):
            #v_moids.axvline(tstart,c='darkorange')
            #v_moids.axvline(tend,c='orange')
            pass
        if any(events[run].loc[interv,'plasmoids_mass']):
            #m_moids.axvline(tstart,c='darkorange')
            #m_moids.axvline(tend,c='orange')
            pass
        if (any(events[run].loc[interv,'plasmoids_volume'])and
            any(events[run].loc[interv,'plasmoids_mass'])):
            #v_moids.axvspan(tstart,tend,alpha=0.2,fc='grey')
            #m_moids.axvspan(tstart,tend,alpha=0.2,fc='grey')
            pass
        elif any(events[run].loc[interv,'plasmoids_volume']):
            #v_moids.axvspan(tstart,tend,alpha=0.2,fc='blue')
            #m_moids.axvspan(tstart,tend,alpha=0.2,fc='red')
            pass
        elif any(events[run].loc[interv,'plasmoids_mass']):
            #v_moids.axvspan(tstart,tend,alpha=0.2,fc='red')
            #m_moids.axvspan(tstart,tend,alpha=0.2,fc='blue')
            pass
        if (any(events[run].loc[interv,'ALbays'])and
            any(events[run].loc[interv,'MGLbays'])):
            #albays.axvspan(tstart,tend,alpha=0.1,fc='grey')
            #mglbays.axvspan(tstart,tend,alpha=0.1,fc='grey')
            pass
        elif any(events[run].loc[interv,'ALbays']):
            #albays.axvspan(tstart,tend,alpha=0.1,fc='blue')
            pass
        elif any(events[run].loc[interv,'MGLbays']):
            #albays.axvspan(tstart,tend,alpha=0.1,fc='blue')
            pass
        '''
        if any(events[run].loc[interv,'K1unsteady']):
            k1.axvline(tstart,c='blue')
            k1.axvspan(tstart,tend,alpha=0.2,fc='green')
            k1.axvline(tend,c='lightblue')
        if any(events[run].loc[interv,'K5unsteady']):
            k5.axvline(tstart,c='blue')
            k5.axvspan(tstart,tend,alpha=0.2,fc='green')
            k5.axvline(tend,c='lightblue')
        '''
    for i,(start,end) in enumerate(sw_intervals):
        tstart = float(pd.Timedelta(start-T0).to_numpy())
        for ax in [nexl,v_moids,m_moids,albays]:
            ax.axvline(tstart,c='grey')
        for ax in [k1var,k1]:
            ax.axvline(tstart,c='grey')
            #window = dt.timedelta(minutes=30).seconds*1e9
            #ax.axvspan(tstart,tstart+window,fc='red')
    general_plot_settings(nexl,do_xlabel=True,legend=False,
                          ylabel=r'Near Earth X Line $\left[R_e\right]$',
                          xlim=ztimes,
                          timedelta=True)
    general_plot_settings(v_moids,do_xlabel=False,legend=False,
                          ylabel=r'Closed Region Volume $\left[R_e^3\right]$',
                          xlim=ztimes,ylim=[0,70],
                          timedelta=True)
    general_plot_settings(m_moids,do_xlabel=True,legend=False,
                          ylabel=r'Closed Region Mass $\left[Mg\right]$',
                          xlim=ztimes,ylim=[0,250],
                          timedelta=True)
    general_plot_settings(albays,do_xlabel=True,legend=False,
                          ylabel=r'AL $\left[nT\right]$',
                          xlim=ztimes,ylim=[-2000,0],
                          timedelta=True)
    general_plot_settings(k1var,do_xlabel=False,legend=False,
                          ylabel=r'10min Total Variation $\left[\%\right]$',
                          xlim=ztimes,
                          timedelta=True)
    general_plot_settings(k1,do_xlabel=True,legend=False,
                          ylabel=r'$\int_S$K1(OpenMP) Flux$\left[TW\right]$',
                          xlim=ztimes,
                          timedelta=True)
    #general_plot_settings(k5,do_xlabel=True,legend=False,
    #                      ylabel=r'$\int_S$K5(ClosedMP) Flux$\left[TW\right]$',
    #                      timedelta=True)
    #general_plot_settings(mglbays,do_xlabel=True,legend=False,
    #                      ylabel=r'MGL $\left[nT\right]$',
    #                      timedelta=True)
    #dips.margins(x=0.1)
    v_moids.margins(x=0.1)
    m_moids.margins(x=0.1)
    albays.margins(x=0.1)
    k1.margins(x=0.1)
    #k5.margins(x=0.1)
    #mglbays.margins(x=0.1)
    #Save
    fig1.tight_layout(pad=1)
    figurename = path+'/vis_events_'+run+kwargs.get('tag','')+'.png'
    fig1.savefig(figurename)
    fill = nexl.fill_between(ev['times'],foundDIP,fc='green')
    nexl.plot(ev['times'],foundDIP,c='lightgreen',lw=4)
    fig1.savefig(figurename.replace('.png','_0.png'))
    plt.close(fig1)
    print('\033[92m Created\033[00m',figurename)

    fig2.tight_layout(pad=1)
    figurename = path+'/vis_events2_'+run+kwargs.get('tag','')+'.png'
    fig2.savefig(figurename)
    plt.close(fig2)
    print('\033[92m Created\033[00m',figurename)

    fig3.tight_layout(pad=1)
    figurename = path+'/vis_events3_'+run+kwargs.get('tag','')+'.png'
    fig3.savefig(figurename)
    albays.fill_between(ev['times'],ev['index']['AL'],ev['GridL'],
                        color='purple',alpha=0.4)
    albays.plot(ev['times'],ev['GridL'],
                        color='black',lw=6)
    fig3.savefig(figurename.replace('.png','_1.png'))
    albays.fill_between(ev['times'],ev['index']['AL'],foundGridL,
                        color='lime',alpha=0.4)
    fig3.savefig(figurename.replace('.png','_2.png'))
    plt.close(fig3)
    print('\033[92m Created\033[00m',figurename)

    #Save in pieces
    fig4.tight_layout(pad=1)
    figurename = path+'/vis_events4_'+run+kwargs.get('tag','')+'.png'
    fig4.savefig(figurename)
    # Save one with just var extras
    k1var.axhline(56.24,c='black')
    fig4.savefig(figurename.replace('.png','_2.png'))
    # Save one with just all extras
    fill = k1.fill_between(ev['times'],foundK1/1e12,fc='green')
    fig4.savefig(figurename.replace('.png','_1.png'))
    fill.remove()
    # Save one without top axis
    k1var.remove()
    fig4.savefig(figurename.replace('.png','_0.png'))
    # Save one without top axis
    plt.close(fig4)
    print('\033[92m Created\033[00m',figurename)

def coupling_scatter(events,path):
    interval_list =build_interval_list(TSTART,DT,TJUMP,
                                       dataset['stretched_LOWnLOWu']['time'])
    #############
    #setup figure
    scatterCoupling,(axis) =plt.subplots(1,1,figsize=[15,15])
    colors = ['#80b3ffff','#0066ffff','#0044aaff',
              '#80ffb3ff','#2aff80ff','#00aa44ff',
              '#ffe680ff','#ffcc00ff','#806600ff']
    testpoints = ['stretched_LOWnLOWu',
                  'stretched_MEDnLOWu',
                  'stretched_HIGHnLOWu',
                  'stretched_LOWnMEDu',
                  'stretched_MEDnMEDu',
                  'stretched_HIGHnMEDu',
                  'stretched_LOWnHIGHu',
                  'stretched_MEDnHIGHu',
                  'stretched_HIGHnHIGHu']
    #Plot
    for i,testpoint in enumerate(testpoints):
        if testpoint in dataset.keys():
            sw = dataset[testpoint]['obs']['swmf_sw']
            Ein,Pstorm = np.zeros(23),np.zeros(23)
            for k,tsample in enumerate([j[1] for j in interval_list][0:-1]):
                Ein[k],Pstorm[k] = sw.loc[tsample,['EinWang','Pstorm']]
            axis.scatter(Ein/1e12,-Pstorm/1e12,s=200,c=colors[i],
                         label=str(i+1))
    axis.set_xlabel(r'$E_{in} \left(TW\right)$, (Wang2014)')
    axis.set_ylabel(r'$P_{storm} \left(TW\right)$, '+
                                                '(Tenfjord and Østgaard 2013)')
    #axis.legend()
    scatterCoupling.tight_layout(pad=1)
    figurename = path+'/couplingScatter.png'
    scatterCoupling.savefig(figurename)
    plt.close(scatterCoupling)
    print('\033[92m Created\033[00m',figurename)

def tab_contingency(events,path):
    transitions = {}
    substorms = {}
    for run in events.keys():
        # count for all events
        n = len(events[run])
        for xkey,ykey in [['MGLbays','K1unsteady'],
                          ['ALbays','K1unsteady'],
                          ['plasmoids','K1unsteady'],
                          ['DIP','K1unsteady'],
                          ['substorm','K1unsteady'],
                          #['substorm','K5unsteady'],
                          ['imf_transients','K1unsteady'],
                          ['both','K1unsteady']]:
            #NOTE trying 'clean' version
            #X = events[run][xkey].values*-1*(events[run]['imf_transients']-1)
            #Y = events[run][ykey].values*-1*(events[run]['imf_transients']-1)
            #TODO: combine transient and substorm for "best case"
            X = events[run][xkey].values
            Y = events[run][ykey].values
            best_skill = -1e12
            best_lag = -30
            skills = np.zeros(len(range(-30,90)))-1e12
            for i,lag in enumerate(range(-30,90)):
                if lag>0:
                    x = X[lag::]
                    y = Y[0:-lag]
                elif lag<0:
                    x = X[0:lag]
                    y = Y[-lag::]
                hit = np.sum(x*y)
                miss = np.sum(x*abs(y-1))
                false = np.sum(abs(x-1)*y)
                no = np.sum(abs(x-1)*abs(y-1))
                skill = (2*(hit*no-false*miss)/
                                ((hit+miss)*(miss+no)+(hit+false)*(false+no)))
                skills[i] = skill
                if skill>best_skill:
                    best_skill = skill
                    best_lag = lag
            # print results
            print('{:<15}{:<15}{:<15}{:<15}'.format('',xkey,'',''))
            print('{:<15}{:<15}{:<15}{:<15}'.format(ykey,'Yes','No',''))
            print('{:<15}{:<15}{:<15}{:<15}'.format('Yes',hit,false,hit+false))
            print('{:<15}{:<15}{:<15}{:<15}'.format('No',miss,no,miss+no))
            print('{:<15}{:<15}{:<15}{:<15}'.format('',hit+miss,false+no,n))
            print('\nHSS: ',best_skill,'\nLag: ',best_lag,'\n')
            if xkey=='imf_transients':
                transitions[run] = best_skill
            elif xkey=='substorm':
                substorms[run] = best_skill
    '''
    transition_x = [0,3,6,0,3,6,0,3,6]
    transition_y = [0,0,0,2,2,2,4,4,4]
    substorms_x = [1,4,7,1,4,7,1,4,7]
    substorms_y = [0,0,0,2,2,2,4,4,4]
    '''
    transition_x = [5,10,20,5,10,20,5,10,20]
    transition_y = [-400,-400,-400,-600,-600,-600,-800,-800,-800]
    substorms_x = [7,12,22,7,12,22,7,12,22]
    substorms_y = [-400,-400,-400,-600,-600,-600,-800,-800,-800]
    transition_top = [transitions.get('stretched_LOWnLOWu',0),
                      transitions.get('stretched_MEDnLOWu',0),
                      transitions.get('stretched_HIGHnLOWu',0),
                      transitions.get('stretched_LOWnMEDu',0),
                      transitions.get('stretched_MEDnMEDu',0),
                      transitions.get('stretched_HIGHnMEDu',0),
                      transitions.get('stretched_LOWnHIGHu',0),
                      transitions.get('stretched_MEDnHIGHu',0),
                      transitions.get('stretched_HIGHnHIGHu',0)]
    substorms_top = [substorms.get('stretched_LOWnLOWu',0),
                    substorms.get('stretched_MEDnLOWu',0),
                    substorms.get('stretched_HIGHnLOWu',0),
                    substorms.get('stretched_LOWnMEDu',0),
                    substorms.get('stretched_MEDnMEDu',0),
                    substorms.get('stretched_HIGHnMEDu',0),
                    substorms.get('stretched_LOWnHIGHu',0),
                    substorms.get('stretched_MEDnHIGHu',0),
                    substorms.get('stretched_HIGHnHIGHu',0)]
    # Setup figure
    old_params = plt.rcParams
    params = {"ytick.color" : "w",
              "xtick.color" : "w",
              "axes.labelcolor" : "w",
              "axes.edgecolor" : "w"}
    plt.rcParams.update(params)#NOTE
    fig = plt.figure(figsize=[12,12])
    ax = fig.add_subplot(111, projection='3d')
    tt = ax.bar3d(transition_x, transition_y, 0, 2, 60, transition_top,
             label='SW Transition',alpha=0.5,ec='black',
             shade=True)
    #ax.legend()
    # Decorate
    ax.set_title('Skill',c='w')
    ax.set_zlim([0,1])
    ax.set_xticks([5,10,20])
    ax.set_yticks([-800,-600,-400])
    ax.set_ylabel('Velocity [km/s]',labelpad=20)
    ax.set_xlabel('Density [amu/cc]',labelpad=20)
    fig.tight_layout(pad=1)
    figurename = path+'/HSS_3d.png'
    fig.savefig(figurename,transparent=True)
    ax.bar3d(substorms_x, substorms_y, 0, 2, 60, substorms_top, shade=True,
             label='Substorm',alpha=0.5,ec='black')
    fig.savefig(figurename.replace('.png','_0.png'),transparent=True)
    tt.remove()
    fig.savefig(figurename.replace('.png','_1.png'),transparent=True)
    plt.close(fig)
    print('\033[92m Created\033[00m',figurename)
    plt.rcParams.update(old_params)#NOTE
    #TODO:
    #   Consider how to automate the threshold of detection to improve scores?
    #   Also look into baselining what a 'good' skill is
    #from IPython import embed; embed()

def tab_ranges(dataset):
    events = dataset.keys()
    results_min = {}
    results_max = {}
    swvals = ['pdyn','Beta','Beta*','Ma','r_shue98','B_T','EinWang','Pstorm']
    for val in swvals:
        results_min[val] = min([dataset[e]['obs']['swmf_sw'][val].min() for
                           e in events])
        results_max[val] = max([dataset[e]['obs']['swmf_sw'][val].max() for
                           e in events])
    mpvals = ['Utot [J]']
    for val in mpvals:
        results_min[val] = min([dataset[e]['mpdict']['ms_full'][val].min() for
                           e in events])
        results_max[val] = max([dataset[e]['mpdict']['ms_full'][val].max() for
                           e in events])

def initial_figures(dataset):
    path = unfiled
    tave,tv,corr,raw,events = {},{},{},{},{}
    for i,run in enumerate(dataset.keys()):
        print(run)
        ev = refactor(dataset[run],dt.datetime(2022,6,6,0))
        if 'iedict' in dataset[run].keys():
            ev2 = gmiono_refactor(dataset[run]['iedict'],
                                  dt.datetime(2022,6,6,0))
            for key in ev2.keys():
                ev[key] = ev2[key]
        #events[run] = build_events(ev,run)
        #tave[run] = interval_average(ev)
        #tv[run] = interval_totalvariation(ev)
        #corr[run],lags = interval_correlation(ev,'RXN_Day','K1',xfactor=1e3,
        #                                        yfactor=1e12)
        #raw[run] = ev
        #TODO plot and corellate ALL K1vsGridL, K1vsClosedMass, etc.
        # use this to justify the ~0.2 range for the "skill" result
        # Are there clear signatures for:
        #   Which one affects it most?
        #   Which one affects it least?
        #   How does the total event count affect this?
        if 'iedict' in dataset[run].keys():
            #Zoomed versions
            #window = ((ev['mp'].index>dt.datetime(2022,6,7,8,0))&
            #          (ev['mp'].index<dt.datetime(2022,6,7,10,0)))
            #energy_vs_polarcap(ev,run,path,zoom=window)
            #mpflux_vs_rxn(ev,run,path,zoom=window)
            #internalflux_vs_rxn(ev,run,path,zoom=window)
            pass
        #mpflux_vs_rxn(ev,run,path)
        #test_matrix(event,ev,path)
        #internalflux_vs_rxn(ev,run,path)
        #mpflux_vs_rxn(ev,event,path)
        #all_fluxes(ev,run,path)
        #Zoomed versions
        steady_window = (dt.datetime(2022,6,6,16,0),
                         dt.datetime(2022,6,6,18,0))
        unsteady_window = (dt.datetime(2022,6,7,0,0),
                           dt.datetime(2022,6,7,2,0))
        #all_fluxes(ev,event,path,zoom=steady_window,tag='steady')
        #all_fluxes(ev,event,path,zoom=unsteady_window,tag='unsteady')
        example_window = (dt.datetime(2022,6,6,14,0),
                          dt.datetime(2022,6,7,4,0))
        small_window =   (dt.datetime(2022,6,6,22,18),
                          dt.datetime(2022,6,6,22,25))
        errors(ev,run,path)
        errors(ev,run,path,zoom=small_window,tag='closezoom')
        #all_fluxes(ev,event,path,zoom=example_window,tag='midzoom')
        #rxn(ev,run,path,zoom=example_window,tag='midzoom')
        #show_event_hist(ev,run,events,path)
        #show_events(ev,run,events,path)
        #show_events(ev,run,events,path,zoom=example_window,tag='midzoom')
        #tshift_scatter(ev,'GridL','K1',run,path)
        #tshift_scatter(ev,'closedVolume','K1',run,path)
        #tshift_scatter(ev,'K5','K1',run,path)
    #plot_indices(dataset,path)
    #coupling_scatter(dataset,path)
    #tab_contingency(events,path)

if __name__ == "__main__":
    T0 = dt.datetime(2022,6,6,0,0)
    TSTART = dt.datetime(2022,6,6,0,0)
    DT = dt.timedelta(hours=2)
    TJUMP = dt.timedelta(hours=2)
    #Need input path, then create output dir's
    inBase = sys.argv[-1]
    inLogs = os.path.join(sys.argv[-1],'data/logs/')
    inAnalysis = os.path.join(sys.argv[-1],'data/analysis/')
    outPath = os.path.join(inBase,'figures')
    unfiled = os.path.join(outPath,'unfiled')
    for path in [outPath,unfiled,]:
        os.makedirs(path,exist_ok=True)

    #setting pyplot configurations
    plt.rcParams.update(pyplotsetup(mode='print'))

    # Event list
    #events = ['MEDnHIGHu','HIGHnHIGHu','LOWnLOWu','LOWnHIGHu','HIGHnLOWu']
    events =['stretched_LOWnLOWu',
             'stretched_LOWnMEDu',
             'stretched_LOWnHIGHu',
             #
             'stretched_HIGHnLOWu',
             'stretched_HIGHnHIGHu',
             #
             'stretched_MEDnMEDu',
             'stretched_MEDnHIGHu',
             'stretched_test']
             #'stretched_LOWnLOWucontinued']
    #events = ['stretched_test']

    ## Analysis Data
    dataset = {}
    for event in events:
        GMfile = os.path.join(inAnalysis,event+'.h5')
        # GM data
        if os.path.exists(GMfile):
            dataset[event] = load_hdf_sort(GMfile)

    '''
    #HOTFIX duplicate LOWLOW values
    M5 = dataset['LOWnLOWu']['mpdict']['ms_full']['UtotM5 [W]'].copy()/1e12
    drops = np.where(abs(M5)>15)
    droptimes = dataset['LOWnLOWu']['time'][drops]
    dataset['LOWnLOWu']['time'] = dataset['LOWnLOWu']['time'].drop(droptimes)
    keylist = dataset['LOWnLOWu']['msdict'].keys()
    for key in keylist:
        df = dataset['LOWnLOWu']['msdict'][key]
        dataset['LOWnLOWu']['msdict'][key] = df.drop(index=droptimes)
    keylist = dataset['LOWnLOWu']['mpdict'].keys()
    for key in keylist:
        df = dataset['LOWnLOWu']['mpdict'][key]
        dataset['LOWnLOWu']['mpdict'][key] = df.drop(index=droptimes)
    '''

    #from IPython import embed; embed()
    ## Log Data
    '''
    for event in events:
        prefix = event.split('_')[1]+'_'
        dataset[event]['obs'] = read_indices(inLogs,prefix=prefix,
                                        start=dataset[event]['time'][0],
                 end=dataset[event]['time'][-1]+dt.timedelta(seconds=1),
                                             read_supermag=False)
    '''
    #dataset['stretched_LOWnLOWu_continued']['obs'] = read_indices(inLogs,
    #                                    prefix='continued_LOWnLOWu_',
    #                                    start=dt.datetime(2022,6,8,0),
    #                                    end=dt.datetime(2022,6,9,0),
    #                                         read_supermag=False)
    ######################################################################
    ##Quicklook timeseries figures
    initial_figures(dataset)
