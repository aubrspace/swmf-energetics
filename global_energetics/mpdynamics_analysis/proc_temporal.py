#!/usr/bin/env python3
"""Functions for handling and processing time varying magnetopause surface
    data that is spatially averaged, reduced, etc
"""
import logging as log
import os
import sys
import glob
import time
from array import array
import numpy as np
from numpy import abs, pi, cos, sin, sqrt, rad2deg, matmul, deg2rad
import scipy as sp
from scipy import integrate
import datetime as dt
import pandas as pd
import matplotlib.pyplot as plt
from progress.bar import Bar
from progress.spinner import Spinner
import spacepy
#from spacepy import coordinates as coord
from spacepy import time as spacetime
import tecplot as tp
from tecplot.constant import *
from tecplot.exception import *

def plot_all_runs_1Qty(axis, dflist, dflabels, timekey, qtkey, ylabel, *,
                       xlim=None, ylim=None, Color=None):
    """Function plots cumulative energy over time on axis with lables
    Inputs
        axis- object plotted on
        dflist- datasets
        dflabels- labels used for legend
        timekey, qtkey- used to located column with time and the qt to plot
    """
    for data in enumerate(dflist):
        if Color == None:
            axis.plot(data[1][timekey],data[1][qtkey],
                  label=qtkey+dflabels[data[0]])
            legend_loc = 'lower left'
        else:
            axis.plot(data[1][timekey],data[1][qtkey],
                  label=qtkey+dflabels[data[0]], color=Color)
            legend_loc = 'lower right'
        '''
        if dflabels[data[0]].find('flow') != -1:
            axis.plot(data[1][timekey],data[1][qtkey],color='orange',
                      label='Flowline')
        if dflabels[data[0]].find('shue') != -1:
            axis.plot(data[1][timekey],data[1][qtkey],color='black',
                      label='Shue98')
        if dflabels[data[0]].find('field') != -1:
            axis.plot(data[1][timekey],data[1][qtkey],color='blue',
                      label='Fieldline')
        if dflabels[data[0]].find('hybrid') != -1:
            axis.plot(data[1][timekey],data[1][qtkey],color='green',
                      label='Hybrid')
        '''
    if xlim!=None:
        axis.set_xlim(xlim)
    if ylim!=None:
        axis.set_ylim(ylim)
    axis.set_xlabel(timekey)
    axis.set_ylabel(ylabel)
    axis.legend(loc=legend_loc)

def get_energy_dataframes(dflist, dfnames):
    """Function adds cumulative energy columns based on power columns
        assuming a constant dt
    Inputs
        dflist, dfnames- list and corresponding names of dataframes
    Outputs
        use_dflist, use_dfnames
    """
    use_dflist, use_dflabels = [], []
    totalE0 = (dflist[0]['Total [J]'].loc[dflist[0].index[0]]+
               dflist[1]['Total [J]'].loc[dflist[1].index[1]])
    dflist[0].loc[:,'K_net_minus_bound [W]'] = (dflist[0]['K_net [W]']-
                                                dflist[1]['K_net [W]'])
    dflist[1].loc[:,'K_net_minus_bound [W]'] = (dflist[1]['K_net [W]']-
                                                dflist[1]['K_net [W]'])
    dflist[2].loc[:,'K_net_minus_bound [W]'] = (dflist[2]['K_net [W]']-
                                                dflist[1]['K_net [W]'])
    for df in enumerate(dflist):
        if not df[1].empty & (dfnames[df[0]].find('stat')==-1):
            if len(df[1]) > 1:
                ###Add cumulative energy terms
                #Compute cumulative energy In, Out, and Net
                start = df[1].index[0]
                totalE = df[1]['Total [J]']
                delta_t = (df[1]['Time [UTC]'].loc[start+1]-
                        df[1]['Time [UTC]'].loc[start]).seconds
                #use pandas cumulative sum method
                cumu_E_net = df[1]['K_net [W]'].cumsum()*delta_t*-1
                adjust_cumu_E_net = df[1]['K_net_minus_bound [W]'].cumsum()*delta_t*-1
                cumu_E_in = df[1]['K_injection [W]'].cumsum()*delta_t*-1
                cumu_E_out = df[1]['K_escape [W]'].cumsum()*delta_t*-1
                #readjust to initialize error to 0 at start
                cumu_E_net = (cumu_E_net+totalE.loc[start]-
                              cumu_E_net.loc[start])
                adjust_cumu_E_net = (adjust_cumu_E_net+totalE.loc[start]-
                                     adjust_cumu_E_net.loc[start])
                E_net_error = adjust_cumu_E_net - totalE
                E_net_rel_error = E_net_error/totalE*100
                #Add column to dataframe
                dflist[df[0]].loc[:,'CumulE_net [J]'] = cumu_E_net
                dflist[df[0]].loc[:,'Adjusted_CumulE_net [J]'] = adjust_cumu_E_net
                dflist[df[0]].loc[:,'CumulE_injection [J]'] = cumu_E_in
                dflist[df[0]].loc[:,'CumulE_escape [J]'] = cumu_E_out
                dflist[df[0]].loc[:,'Energy_error [J]'] = E_net_error
                dflist[df[0]].loc[:,'RelativeE_error [%]'] =E_net_rel_error
                ###Add modified dataframe to list
                use_dflist.append(dflist[df[0]])
                use_dflabels.append(dfnames[df[0]])
    return use_dflist, use_dflabels

def prepare_figures(dflist, dfnames, outpath):
    """Function calls which figures to be plotted
    Inputs
        dfilist- list object containing dataframes
        dfnames- names of each dataset
    """
    for df in enumerate(dflist):
        dflist[df[0]] = df[1][(df[1]['Time [UTC]'] > dt.datetime(2014,2,18,8))]
    energy_dfs, energy_dfnames= get_energy_dataframes(dflist, dfnames)
    stats_dfs, stats_dfnames = [], []
    for df in enumerate(dflist):
        if dfnames[df[0]].find('stat') != -1:
            stats_dfs.append(df[1])
            stats_dfnames.append(dfnames[df[0]])
    if energy_dfs != []:
        ###################################################################
        #Cumulative Energy
        if True:
            figname = 'EnergyAccumulation'
            #quick manipulation
            isodfs = energy_dfs[0:1]
            isodfnames = energy_dfnames[0:1]
            spdfs = energy_dfs[2::]
            spdfnames = energy_dfnames[2::]
            coredfs = energy_dfs[1:2]
            coredfnames = energy_dfnames[1:2]
            #figure settings
            cumulative_E, (ax1,ax2,ax3) = plt.subplots(nrows=3,ncols=1,
                                               sharex=True, figsize=[18,6])
            #axes
            timekey = 'Time [UTC]'
            ylabel = 'Energy [J]'
            qtykey = 'Total [J]'
            plot_all_runs_1Qty(ax2, isodfs, isodfnames, timekey,
                               qtykey, ylabel)
            qtykey = 'Adjusted_CumulE_net [J]'
            plot_all_runs_1Qty(ax2, isodfs, isodfnames, timekey,
                               qtykey, ylabel)
            qtykey = 'RelativeE_error [%]'
            ylabel = 'Error'
            plot_all_runs_1Qty(ax2.twinx(), isodfs, isodfnames, timekey,
                               qtykey, ylabel, Color='green')
            qtykey = 'Total [J]'
            plot_all_runs_1Qty(ax1, spdfs, spdfnames, timekey,
                               qtykey, ylabel)
            '''
            qtykey = 'CumulE_net [J]'
            plot_all_runs_1Qty(ax2, spdfs, spdfnames, timekey,
                               qtykey, ylabel)
            '''
            qtykey = 'Total [J]'
            plot_all_runs_1Qty(ax3, coredfs, coredfnames, timekey,
                               qtykey, ylabel)
            qtykey = 'CumulE_net [J]'
            plot_all_runs_1Qty(ax3, coredfs, coredfnames, timekey,
                               qtykey, ylabel)
            cumulative_E.savefig(outpath+'{}.png'.format(figname))
            #plt.show()
            #plt.close(cumulative_E)
        ###################################################################
        #Power- surface compare
        if True:
            figname = 'Power_surface_compare'
            #quick manipulation
            dfs = energy_dfs[0:1]
            dfnames = energy_dfnames[0:1]
            #figure settings
            power, (ax1,ax2,ax3) = plt.subplots(nrows=3,ncols=1,
                                               sharex=True, figsize=[18,6])
            #axes
            timekey = 'Time [UTC]'
            ylabel = 'Power [W]'
            #mp
            qtykey = 'K_injection [W]'
            plot_all_runs_1Qty(ax1, isodfs, isodfnames, timekey,
                               qtykey, ylabel)
            qtykey = 'K_escape [W]'
            plot_all_runs_1Qty(ax2, isodfs, isodfnames, timekey,
                               qtykey, ylabel)
            qtykey = 'K_net [W]'
            plot_all_runs_1Qty(ax3, isodfs, isodfnames, timekey,
                               qtykey, ylabel)
            #sphere
            qtykey = 'K_injection [W]'
            plot_all_runs_1Qty(ax1, spdfs, spdfnames, timekey,
                               qtykey, ylabel)
            qtykey = 'K_escape [W]'
            plot_all_runs_1Qty(ax2, spdfs, spdfnames, timekey,
                               qtykey, ylabel)
            qtykey = 'K_net [W]'
            plot_all_runs_1Qty(ax3, spdfs, spdfnames, timekey,
                               qtykey, ylabel)
            #core
            qtykey = 'K_injection [W]'
            plot_all_runs_1Qty(ax1, coredfs, coredfnames, timekey,
                               qtykey, ylabel)
            qtykey = 'K_escape [W]'
            plot_all_runs_1Qty(ax2, coredfs, coredfnames, timekey,
                               qtykey, ylabel)
            qtykey = 'K_net [W]'
            plot_all_runs_1Qty(ax3, coredfs, coredfnames, timekey,
                               qtykey, ylabel)
            power.savefig(outpath+'{}.png'.format(figname))
            #plt.show()
            #plt.close(power)
        ###################################################################
        #Power
        if True:
            figname = 'PoyntingPower'
            #quick manipulation
            dfs = energy_dfs[0:1]
            dfnames = energy_dfnames[0:1]
            #figure settings
            power, (ax1,ax2,ax3) = plt.subplots(nrows=3,ncols=1,
                                               sharex=True, figsize=[18,6])
            #axes
            timekey = 'Time [UTC]'
            ylabel = 'Power [W]'
            #mp
            qtykey = 'ExB_injection [W]'
            plot_all_runs_1Qty(ax1, isodfs, isodfnames, timekey,
                               qtykey, ylabel)
            qtykey = 'ExB_escape [W]'
            plot_all_runs_1Qty(ax1, isodfs, isodfnames, timekey,
                               qtykey, ylabel)
            qtykey = 'ExB_net [W]'
            plot_all_runs_1Qty(ax1, isodfs, isodfnames, timekey,
                               qtykey, ylabel)
            #sphere
            qtykey = 'ExB_injection [W]'
            plot_all_runs_1Qty(ax2, spdfs, spdfnames, timekey,
                               qtykey, ylabel)
            qtykey = 'ExB_escape [W]'
            plot_all_runs_1Qty(ax2, spdfs, spdfnames, timekey,
                               qtykey, ylabel)
            qtykey = 'ExB_net [W]'
            plot_all_runs_1Qty(ax2, spdfs, spdfnames, timekey,
                               qtykey, ylabel)
            #core
            qtykey = 'ExB_injection [W]'
            plot_all_runs_1Qty(ax3, coredfs, coredfnames, timekey,
                               qtykey, ylabel)
            qtykey = 'ExB_escape [W]'
            plot_all_runs_1Qty(ax3, coredfs, coredfnames, timekey,
                               qtykey, ylabel)
            qtykey = 'ExB_net [W]'
            plot_all_runs_1Qty(ax3, coredfs, coredfnames, timekey,
                               qtykey, ylabel)
            #Fill between to distinguish +/- net powers
            ax1.fill_between(isodfs[0]['Time [UTC]'], 0,
                             isodfs[0]['ExB_net [W]'])
            ax2.fill_between(spdfs[0]['Time [UTC]'], 0,
                             spdfs[0]['ExB_net [W]'])
            ax3.fill_between(coredfs[0]['Time [UTC]'], 0,
                             coredfs[0]['ExB_net [W]'])
            power.savefig(outpath+'{}.png'.format(figname))
            #plt.show()
            #plt.close(power)
        ###################################################################
        #Power
        if True:
            figname = 'Power'
            #quick manipulation
            dfs = energy_dfs[0:1]
            dfnames = energy_dfnames[0:1]
            #figure settings
            power, (ax1,ax2,ax3) = plt.subplots(nrows=3,ncols=1,
                                               sharex=True, figsize=[18,6])
            #axes
            timekey = 'Time [UTC]'
            ylabel = 'Power [W]'
            #mp
            qtykey = 'K_injection [W]'
            plot_all_runs_1Qty(ax1, isodfs, isodfnames, timekey,
                               qtykey, ylabel)
            qtykey = 'K_escape [W]'
            plot_all_runs_1Qty(ax1, isodfs, isodfnames, timekey,
                               qtykey, ylabel)
            qtykey = 'K_net_minus_bound [W]'
            plot_all_runs_1Qty(ax1, isodfs, isodfnames, timekey,
                               qtykey, ylabel)
            #sphere
            qtykey = 'K_injection [W]'
            plot_all_runs_1Qty(ax2, spdfs, spdfnames, timekey,
                               qtykey, ylabel)
            qtykey = 'K_escape [W]'
            plot_all_runs_1Qty(ax2, spdfs, spdfnames, timekey,
                               qtykey, ylabel)
            qtykey = 'K_net_minus_bound [W]'
            plot_all_runs_1Qty(ax2, spdfs, spdfnames, timekey,
                               qtykey, ylabel)
            #core
            qtykey = 'K_injection [W]'
            plot_all_runs_1Qty(ax3, coredfs, coredfnames, timekey,
                               qtykey, ylabel)
            qtykey = 'K_escape [W]'
            plot_all_runs_1Qty(ax3, coredfs, coredfnames, timekey,
                               qtykey, ylabel)
            qtykey = 'K_net [W]'
            plot_all_runs_1Qty(ax3, coredfs, coredfnames, timekey,
                               qtykey, ylabel)
            #Fill between to distinguish +/- net powers
            ax1.fill_between(isodfs[0]['Time [UTC]'], 0,
                             isodfs[0]['K_net [W]'])
            ax2.fill_between(spdfs[0]['Time [UTC]'], 0,
                             spdfs[0]['K_net [W]'])
            ax3.fill_between(coredfs[0]['Time [UTC]'], 0,
                             coredfs[0]['K_net [W]'])
            power.savefig(outpath+'{}.png'.format(figname))
            #plt.show()
            #plt.close(power)
        ###################################################################
        #Normalized Power
        if True:
            figname = 'AveragePower'
            #quick manipulation
            dfs = energy_dfs[0:1]
            dfnames = energy_dfnames[0:1]
            #figure settings
            power, (ax1,ax2,ax3) = plt.subplots(nrows=3,ncols=1,
                                               sharex=True, figsize=[18,6])
            #axes
            timekey = 'Time [UTC]'
            ylabel = 'Average Power [W/Re^2]'
            #mp
            qtykey = 'Average K_injection [W/Re^2]'
            plot_all_runs_1Qty(ax1, isodfs, isodfnames, timekey,
                               qtykey, ylabel)
            qtykey = 'Average K_escape [W/Re^2]'
            plot_all_runs_1Qty(ax1, isodfs, isodfnames, timekey,
                               qtykey, ylabel)
            qtykey = 'Average K_net [W/Re^2]'
            plot_all_runs_1Qty(ax1, isodfs, isodfnames, timekey,
                               qtykey, ylabel)
            #sphere
            qtykey = 'Average K_injection [W/Re^2]'
            plot_all_runs_1Qty(ax2, spdfs, spdfnames, timekey,
                               qtykey, ylabel)
            qtykey = 'Average K_escape [W/Re^2]'
            plot_all_runs_1Qty(ax2, spdfs, spdfnames, timekey,
                               qtykey, ylabel)
            qtykey = 'Average K_net [W/Re^2]'
            plot_all_runs_1Qty(ax2, spdfs, spdfnames, timekey,
                               qtykey, ylabel)
            #core
            qtykey = 'Average K_injection [W/Re^2]'
            plot_all_runs_1Qty(ax3, coredfs, coredfnames, timekey,
                               qtykey, ylabel)
            qtykey = 'Average K_escape [W/Re^2]'
            plot_all_runs_1Qty(ax3, coredfs, coredfnames, timekey,
                               qtykey, ylabel)
            qtykey = 'Average K_net [W/Re^2]'
            plot_all_runs_1Qty(ax3, coredfs, coredfnames, timekey,
                               qtykey, ylabel)
            #Fill between to distinguish +/- net powers
            ax1.fill_between(isodfs[0]['Time [UTC]'], 0,
                             isodfs[0]['Average K_net [W/Re^2]'])
            ax2.fill_between(spdfs[0]['Time [UTC]'], 0,
                             spdfs[0]['Average K_net [W/Re^2]'])
            ax3.fill_between(coredfs[0]['Time [UTC]'], 0,
                             coredfs[0]['Average K_net [W/Re^2]'])
            power.savefig(outpath+'{}.png'.format(figname))
            #plt.show()
            #plt.close(power)
        ###################################################################
        #Volume and Surface Area
        if True:
            figname = 'VolumeSurfaceArea'
            #quick manipulation
            energy_dfs[0].loc[:,'V/SA [Re]'] = energy_dfs[0]['Volume [Re^3]']/energy_dfs[0]['Area [Re^2]']
            dfs = energy_dfs[0:1]
            dfnames = energy_dfnames[0:1]
            #figure settings
            VolArea, (ax1,ax2) = plt.subplots(nrows=2,ncols=1,
                                               sharex=True, figsize=[18,6])
            #axes
            timekey = 'Time [UTC]'
            qtykey = 'Area [Re^2]'
            ylabel = 'Surface Area [Re^2]'
            plot_all_runs_1Qty(ax1, dfs, dfnames, timekey,
                               qtykey, ylabel)
            qtykey = 'Volume [Re^3]'
            ylabel = 'Volume [Re^3]'
            plot_all_runs_1Qty(ax1.twinx(), dfs, dfnames, timekey,
                               qtykey, ylabel, Color='orange')
            qtykey = 'V/SA [Re]'
            ylabel = 'Volume/SurfaceArea [Re]'
            plot_all_runs_1Qty(ax2, dfs, dfnames, timekey,
                               qtykey, ylabel)
            qtykey = 'X_subsolar [Re]'
            ylabel = 'Subsolar Distance [Re]'
            plot_all_runs_1Qty(ax2.twinx(), dfs, dfnames, timekey,
                               qtykey, ylabel, Color='orange')
            VolArea.savefig(outpath+'{}.png'.format(figname))
            #plt.show()
            #plt.close(VolArea)
        ###################################################################
        '''
        #Other Energies
        if True:
            figname = 'VolumeEnergies'
            dfs = energy_dfs[1::]
            dfnames = energy_dfnames[1::]
            Volume_E, (ax1,ax2,ax3,ax4,ax5) = plt.subplots(nrows=5,ncols=1,
                                               sharex=True, figsize=[20,10])
            timekey = 'Time [UTC]'
            qtykey = 'uB [J]'
            ylabel = 'Magnetic Energy [J]'
            plot_all_runs_1Qty(ax1, dfs, dfnames, timekey,
                               qtykey, ylabel)
            timekey = 'Time [UTC]'
            qtykey = 'uE [J]'
            ylabel = 'Electric Energy [J]'
            plot_all_runs_1Qty(ax5, dfs, dfnames, timekey,
                               qtykey, ylabel)
            qtykey = 'KEpar [J]'
            ylabel = 'Parallel Kinetic Energy [J]'
            plot_all_runs_1Qty(ax2, dfs, dfnames, timekey,
                               qtykey, ylabel)
            qtykey = 'KEperp [J]'
            ylabel = 'Perpendicular Kinetic Energy [J]'
            plot_all_runs_1Qty(ax3, dfs, dfnames, timekey,
                               qtykey, ylabel)
            qtykey = 'Etherm [J]'
            ylabel = 'Thermal Energy [J]'
            plot_all_runs_1Qty(ax4, dfs, dfnames, timekey,
                               qtykey, ylabel)
            Volume_E.savefig(outpath+'{}.png'.format(figname))
        '''
        ###################################################################
        #Other Energies
        if True:
            figname = 'VolumeEnergies'
            #quick manipulations
            dfs = energy_dfs[0:1]
            dfnames = energy_dfnames[0:1]
            #figure settings
            Volume_E, (ax1,ax2,ax3,ax4,ax5) = plt.subplots(nrows=5,ncols=1,
                                               sharex=True, figsize=[20,10])
            #axes
            timekey = 'Time [UTC]'
            qtykey = 'uB [J]'
            ylabel = 'Magnetic Energy [J]'
            plot_all_runs_1Qty(ax1, dfs, dfnames, timekey,
                               qtykey, ylabel)
            timekey = 'Time [UTC]'
            qtykey = 'uE [J]'
            ylabel = 'Electric Energy [J]'
            plot_all_runs_1Qty(ax5, dfs, dfnames, timekey,
                               qtykey, ylabel)
            qtykey = 'KEpar [J]'
            ylabel = 'Parallel Kinetic Energy [J]'
            plot_all_runs_1Qty(ax2, dfs, dfnames, timekey,
                               qtykey, ylabel)
            qtykey = 'KEperp [J]'
            ylabel = 'Perpendicular Kinetic Energy [J]'
            plot_all_runs_1Qty(ax3, dfs, dfnames, timekey,
                               qtykey, ylabel)
            qtykey = 'Etherm [J]'
            ylabel = 'Thermal Energy [J]'
            plot_all_runs_1Qty(ax4, dfs, dfnames, timekey,
                               qtykey, ylabel)
            Volume_E.savefig(outpath+'{}.png'.format(figname))
            #plt.show()
            #plt.close(Volume_E)
        ###################################################################
        #Energy split
        if True:
            figname = 'VolumeEnergyBreakdown'
            #quick manipulation
            data = energy_dfs[0]
            uB = data['uB [J]']
            uE = data['uE [J]']
            Etherm = data['Etherm [J]']
            KEpar = data['KEpar [J]']
            KEperp = data['KEperp [J]']
            total = uE+uB+Etherm+KEpar+KEperp
            energy_dfs[0].loc[:,'total energy'] = total.values
            energy_dfs[0].loc[:,'uB partition'] = uB/total*100
            energy_dfs[0].loc[:,'uE partition'] = uE/total*100
            energy_dfs[0].loc[:,'Etherm partition'] = Etherm/total*100
            energy_dfs[0].loc[:,'KEpar partition'] = KEpar/total*100
            energy_dfs[0].loc[:,'KEperp partition'] = KEperp/total*100
            dfs = energy_dfs[0:1]
            dfnames = energy_dfnames[0:1]
            #figure settings
            Volume_Ebreakdown, (ax1) = plt.subplots(nrows=1,ncols=1,
                                               sharex=True, figsize=[20,10])
            #axes
            timekey = 'Time [UTC]'
            qtykey = 'uB partition'
            ylabel = 'Magnetic Energy [J]'
            plot_all_runs_1Qty(ax1, dfs, dfnames, timekey,
                               qtykey, ylabel)
            timekey = 'Time [UTC]'
            qtykey = 'uE partition'
            ylabel = 'Electric Energy [J]'
            plot_all_runs_1Qty(ax1, dfs, dfnames, timekey,
                               qtykey, ylabel)
            qtykey = 'Etherm partition'
            ylabel = 'Parallel Kinetic Energy [J]'
            plot_all_runs_1Qty(ax1, dfs, dfnames, timekey,
                               qtykey, ylabel)
            qtykey = 'KEpar partition'
            ylabel = 'Perpendicular Kinetic Energy [J]'
            plot_all_runs_1Qty(ax1, dfs, dfnames, timekey,
                               qtykey, ylabel)
            qtykey = 'KEperp partition'
            ylabel = 'Energy fraction [%]'
            plot_all_runs_1Qty(ax1, dfs, dfnames, timekey,
                               qtykey, ylabel, ylim=[0,5])
            Volume_Ebreakdown.savefig(outpath+'{}.png'.format(figname))
            #plt.show()
            #plt.close(Volume_E)
        ###################################################################
    else:
        print('Unable to create ___ plot, data missing!')
    pass

def process_temporal_mp(data_path_list, outputpath):
    """Top level function handles time varying magnetopause data and
        generates figures according to settings set by inputs
    Inputs
        data_path_list- paths to the data, default will skip
        outputpaht
    """
    if data_path_list == []:
        print('Nothing to do, no data_paths were given!')
    else:
        approved = ['stats', 'shue', 'shue98', 'shue97', 'flow', 'hybrid', 'field', 'iso_rho', 'box', 'sphere']
        dflist, dfnames = [], []
        spin = Spinner('finding available temporal data ')
        for path in data_path_list:
            if path != None:
                for datafile in glob.glob(path+'/*.h5'):
                    with pd.HDFStore(datafile) as hdf_file:
                        for key in hdf_file.keys():
                            if any([key.find(match)!=-1
                                   for match in approved]):
                                dflist.append(hdf_file[key])
                                dfnames.append(key)
                            else:
                                print('key {} not understood!'.format(key))
                            spin.next()
        prepare_figures(dflist, dfnames, outputpath)

if __name__ == "__main__":
    datapath = os.getcwd()+'/output/mpdynamics/betastar/'
    print(datapath)
    process_temporal_mp([datapath],datapath+'figures/')