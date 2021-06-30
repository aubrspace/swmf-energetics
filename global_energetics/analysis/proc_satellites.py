#!/usr/bin/env python3
"""module processes observation/simulation satellite traces
"""
import os
import sys
import glob
import time
import numpy as np
from numpy import abs, pi, cos, sin, sqrt, rad2deg, matmul, deg2rad
import datetime as dt
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
import swmfpy
import spacepy
from spacepy import coordinates as coord
from spacepy import time as spacetime
#interpackage imports
from global_energetics.analysis.proc_temporal import read_energetics
from global_energetics.analysis.proc_indices import (read_indices,
                                                     datetimeparser,
                                                     datetimeparser2,
                                                     datetimeparser3,
                                                     datetimeparser4,
                                                     df_coord_transform)
def mark_cross_themis(axis, crossingdata, *, probe='a',
                      timerange=[dt.datetime(2014,2,18,6),
                                 dt.datetime(2014,2,20,0)]):
    """Function marks themis crossings in time range for given probe based
        on crossing data input
    Input
        axis- pyplot axis object
        crossingdata- pandas DataFrame with all crossings
        probe, timerange- optional inputs for specific probe and time range
    """
    data = crossingdata[(crossingdata['UT']<timerange[1]) &
                        (crossingdata['UT']>timerange[0]) &
                        (crossingdata['PROBE']==probe)]
    for cross in data['UT'].values:
        axis.axvline(cross)
def mark_cross_geotail(axis, crossingdata, *,
                      timerange=[dt.datetime(2014,2,18,6),
                                 dt.datetime(2014,2,20,0)]):
    """Function marks geotail crossings in time range for given probe based
        on crossing data input
    Input
        axis- pyplot axis object
        crossingdata- pandas DataFrame with all crossings
        probe, timerange- optional inputs for specific probe and time range
    """
    data = crossingdata[(crossingdata['UT']<timerange[1]) &
                        (crossingdata['UT']>timerange[0])]
    for cross in data['UT'].values:
        axis.axvline(cross)
def plot_Betastar(axis, dflist, ylabel, *,
             xlim=None, ylim=None, Color=None, Size=4, ls=None,
             use_inner=False, use_shield=False):
    """Function plots B field magnitude for trajectories
    Inputs
        axis- object plotted on
        dflist- datasets
        dflabels- labels used for legend
        timekey- used to located column with time and the qt to plot
        ylabel, xlim, ylim, Color, Size, ls,- plot/axis settings
    """
    simkeys = ['themisa','themisb','themisc','themisd','themise','geotail',
               'cluster1', 'cluster2', 'cluster3', 'cluster4']
    for df in dflist:
        name = df['name'].iloc[-1]
        if name.find('TH')!=-1:
            probe = name.split('_obs')[0].split('TH')[-1]
            axis.plot(df['UT'],df['Betastar'],
                      label=r'\textit{Themis}$\displaystyle_'+probe+'$',
                      linewidth=Size, linestyle=ls,color='coral')
        elif name.find('GE')!=-1:
            pass
        elif (name.find('C')!=-1) and (name.find('_obs')!=-1):
            probe = name.split('_obs')[0].split('C')[-1]
            axis.plot(df['UT'], df['Betastar'],
                      label=r'\textit{Cluster}$\displaystyle_'+probe+'$',
                      linewidth=Size, linestyle=ls,color='coral')
        elif any([name.find(key)!=-1 for key in simkeys]):
            if name.find('themis')!=-1:
                probe = name.split('themis')[-1].upper()
                axis.plot(df['Time [UTC]'],df['Betastar'],
                          label=r'\textit{Sim}$\displaystyle_'+probe+'$',
                       linewidth=Size, linestyle=ls,color='lightsteelblue')
            elif name.find('cluster')!=-1:
                probe = name.split('cluster')[-1].upper()
                axis.plot(df['Time [UTC]'],df['Betastar'],
                          label=r'\textit{Sim}$\displaystyle_'+probe+'$',
                       linewidth=Size, linestyle=ls,color='lightsteelblue')
            else:
                axis.plot(df['Time [UTC]'],df['Betastar'],
                          label=r'\textit{Sim}$\displaystyle$',
                       linewidth=Size, linestyle=ls,color='lightsteelblue')
    if xlim!=None:
        axis.set_xlim(xlim)
    if ylim!=None:
        axis.set_ylim(ylim)
    else:
        axis.set_ylim([0,5])
    axis.set_xlabel(r'\textit{Time (UT)}')
    axis.set_ylabel(ylabel)
    axis.legend(loc='upper left', facecolor='gray')
def plot_Magnetosphere(axis, dflist, ylabel, *,
             xlim=None, ylim=None, Color=None, Size=4, ls=None,
             use_inner=False, use_shield=False):
    """Function plots B field magnitude for trajectories
    Inputs
        axis- object plotted on
        dflist- datasets
        dflabels- labels used for legend
        timekey- used to located column with time and the qt to plot
        ylabel, xlim, ylim, Color, Size, ls,- plot/axis settings
    """
    simkeys = ['themisa','themisb','themisc','themisd','themise','geotail',
               'cluster1', 'cluster2', 'cluster3', 'cluster4']
    for df in dflist:
        name = df['name'].iloc[-1]
        if name.find('TH')!=-1:
            probe = name.split('_obs')[0].split('TH')[-1]
            axis.plot(df['UT'],df['Magnetosphere_state'],
                      label=r'\textit{Themis}$\displaystyle_'+probe+'$',
                      linewidth=Size, linestyle=ls,color='coral')
        elif name.find('GE')!=-1:
            pass
        elif (name.find('C')!=-1) and (name.find('_obs')!=-1):
            probe = name.split('_obs')[0].split('C')[-1]
            axis.plot(df['UT'], df['Magnetosphere_state'],
                      label=r'\textit{Cluster}$\displaystyle_'+probe+'$',
                      linewidth=Size, linestyle=ls,color='coral')
        elif any([name.find(key)!=-1 for key in simkeys]):
            if name.find('themis')!=-1:
                probe = name.split('themis')[-1].upper()
                axis.plot(df['Time [UTC]'],df['Magnetosphere_state'],
                          label=r'\textit{Sim}$\displaystyle_'+probe+'$',
                       linewidth=Size, linestyle=ls,color='lightsteelblue')
            elif name.find('cluster')!=-1:
                probe = name.split('cluster')[-1].upper()
                axis.plot(df['Time [UTC]'],df['Magnetosphere_state'],
                          label=r'\textit{Sim}$\displaystyle_'+probe+'$',
                       linewidth=Size, linestyle=ls,color='lightsteelblue')
            else:
                axis.plot(df['Time [UTC]'],df['Magnetosphere_state'],
                          label=r'\textit{Sim}$\displaystyle$',
                       linewidth=Size, linestyle=ls,color='lightsteelblue')
    if xlim!=None:
        axis.set_xlim(xlim)
    if ylim!=None:
        axis.set_ylim(ylim)
    else:
        #axis.set_ylim([0,200])
        pass
    axis.set_xlabel(r'\textit{Time (UT)}')
    axis.set_ylabel(ylabel)
    axis.legend(loc='upper left', facecolor='gray')
def plot_Bmag(axis, dflist, ylabel, *,
             xlim=None, ylim=None, Color=None, Size=4, ls=None,
             use_inner=False, use_shield=False):
    """Function plots B field magnitude for trajectories
    Inputs
        axis- object plotted on
        dflist- datasets
        dflabels- labels used for legend
        timekey- used to located column with time and the qt to plot
        ylabel, xlim, ylim, Color, Size, ls,- plot/axis settings
    """
    simkeys = ['themisa','themisb','themisc','themisd','themise','geotail',
               'cluster1', 'cluster2', 'cluster3', 'cluster4']
    for df in dflist:
        name = df['name'].iloc[-1]
        if name.find('TH')!=-1:
            probe = name.split('_obs')[0].split('TH')[-1]
            axis.plot(df['UT'],df['FGS-D_B_TOTAL'],
                      label=r'\textit{Themis}$\displaystyle_'+probe+'$',
                      linewidth=Size, linestyle=ls,color='coral')
        elif name.find('GE')!=-1:
            axis.plot(df['UT'], df['IB']*0.1,
                      label=r'\textit{Geotail}$\displaystyle$',
                      linewidth=Size, linestyle=ls,color='coral')
        elif (name.find('C')!=-1) and (name.find('_obs')!=-1):
            probe = name.split('_obs')[0].split('C')[-1]
            axis.plot(df['UT'], df['B'],
                      label=r'\textit{Cluster}$\displaystyle_'+probe+'$',
                      linewidth=Size, linestyle=ls,color='coral')
        elif any([name.find(key)!=-1 for key in simkeys]):
            if name.find('themis')!=-1:
                probe = name.split('themis')[-1].upper()
                axis.plot(df['Time [UTC]'],df['Bmag [nT]'],
                          label=r'\textit{Sim}$\displaystyle_'+probe+'$',
                       linewidth=Size, linestyle=ls,color='lightsteelblue')
            elif name.find('cluster')!=-1:
                probe = name.split('cluster')[-1].upper()
                axis.plot(df['Time [UTC]'],df['Bmag [nT]'],
                          label=r'\textit{Sim}$\displaystyle_'+probe+'$',
                       linewidth=Size, linestyle=ls,color='lightsteelblue')
            else:
                axis.plot(df['Time [UTC]'],df['Bmag [nT]'],
                          label=r'\textit{Sim}$\displaystyle$',
                       linewidth=Size, linestyle=ls,color='lightsteelblue')
    if xlim!=None:
        axis.set_xlim(xlim)
    if ylim!=None:
        axis.set_ylim(ylim)
    else:
        axis.set_ylim([0,200])
    axis.set_xlabel(r'\textit{Time (UT)}')
    axis.set_ylabel(ylabel)
    axis.legend(loc='upper left', facecolor='gray')
def add_derived_variables(dflist, *, obs=False):
    """Function adds columns of data by performing simple operations
    Inputs
        dflist- dataframe
    Outputs
        dflist- dataframe with modifications
    """
    for df in enumerate(dflist):
        if (not df[1].empty) and (not obs):
            ###B field
            B = sqrt(df[1]['Bx']**2+df[1]['By']**2+df[1]['Bz']**2)
            dflist[df[0]]['Bmag [nT]'] = B
            ###Flow field
            U = sqrt(df[1]['Ux']**2+df[1]['Uy']**2+df[1]['Uz']**2)
            dflist[df[0]]['Umag [km/s]'] = U
            ###Betastar
            Dp = df[1]['Rho']*1e6*1.6605e-27*U**2*1e6*1e9
            dflist[df[0]]['Betastar'] =(df[1]['P']+Dp)/(
                                        B**2/(2*4*pi*1e-7)*1e-9)
            ###Magnetosphere state
            state=[]
            for index in df[1].index:
                if dflist[df[0]]['Betastar'].iloc[index]>0.7:
                    if df[1]['status'].iloc[index]!=1:
                        state.append(0)
                    else:
                        state.append(1)
                else:
                    state.append(1)
            dflist[df[0]]['Magnetosphere_state']=state
        elif not df[1].empty:
            name = df[1]['name'].iloc[-1]
            if name.find('TH')!=-1:
                #Get P, Dp, B in J/m^3 and T
                probe = name.split('_obs')[0].split('TH')[-1]
                Ptot = df[1]['P_ION_MOM_ESA-'+probe] #eV/cm^3
                N = df[1]['N_ION_MOM_ESA-'+probe]*1e6*1.6726e-27 #kg/m^3
                Vx = df[1]['VX_ION_GSM_MOM_ESA-'+probe] #km/s
                Vy = df[1]['VY_ION_GSM_MOM_ESA-'+probe] #km/s
                Vz = df[1]['VZ_ION_GSM_MOM_ESA-'+probe] #km/s
                V = np.sqrt(Vx**2+Vy**2+Vz**2)*1000 #m/s
                Dp = V**2 * N #J/m^3
                P = Ptot*1.6022e-13-Dp/2 #J/m^3
                B = df[1]['FGS-D_B_TOTAL']*1e-9 #T
            elif name.find('C4')!=-1:
                #Get P, Dp, B in J/m^3 and T
                probe = 4
                N = df[1]['N(P)']*1e6*1.6726e-27 #kg/m^3
                Vx = df[1]['VX_P_GSE'] #km/s
                Vy = df[1]['VY_P_GSE'] #km/s
                Vz = df[1]['VZ_P_GSE'] #km/s
                V = np.sqrt(Vx**2+Vy**2+Vz**2)*1000 #m/s
                T =np.sqrt(df[1]['T(P)_PAR']**2+(2*df[1]['T(P)_PERP'])**2)/1e6 #K
                P = N*1.3807e-23*T
                Dp = V**2 * N #J/m^3
                B = df[1]['B']*1e-9 #T
            else:
                P, Dp, B = 0, 0, 1
            dflist[df[0]]['Betastar'] = (P+Dp)/(B**2/(2*4*pi*1e-7))
            ###Magnetosphere state
            state=[]
            for index in df[1].index:
                if dflist[df[0]]['Betastar'].iloc[index]>0.7:
                    state.append(0)
                else:
                    state.append(1)
            dflist[df[0]]['Magnetosphere_state']=state
    return dflist
def split_geotail(dflist):
    """Function splits themis satellite data in big list into each probe
    Inputs
        dflist
    Outputs
        themis_a.. themis_e
    """
    geotail, cross = [], []
    for df in dflist:
        name = df['name'].iloc[-1]
        if (name.find('GE')!=-1) or (name.find('geotail')!=-1):
            geotail.append(df)
            if (name.find('GE')!=-1) and (len(geotail)>1):
                geotail = [interp_combine_dfs(geotail[0],geotail[-1],
                                              'UT', 'UT')]
        elif (name.find('crossing')!=-1):
            cross.append(df)
    return geotail, cross
def split_themis(dflist):
    """Function splits themis satellite data in big list into each probe
    Inputs
        dflist
    Outputs
        themis_a.. themis_e
    """
    themis_a,themis_b,themis_c,themis_d,themis_e,cross=[],[],[],[],[],[]
    for df in dflist:
        name = df['name'].iloc[-1]
        if (name.find('THA')!=-1) or (name.find('themisa')!=-1):
            themis_a.append(df)
            if (name.find('THA')!=-1) and (len(themis_a)>1):
                themis_a = [interp_combine_dfs(themis_a[0],themis_a[-1],
                                              'UT', 'UT')]
        elif (name.find('THB')!=-1) or (name.find('themisb')!=-1):
            themis_b.append(df)
            if (name.find('THB')!=-1) and (len(themis_b)>1):
                themis_b = [interp_combine_dfs(themis_b[0],themis_b[-1],
                                              'UT', 'UT')]
        elif (name.find('THC')!=-1) or (name.find('themisc')!=-1):
            themis_c.append(df)
            if (name.find('THC')!=-1) and (len(themis_c)>1):
                themis_c = [interp_combine_dfs(themis_c[0],themis_c[-1],
                                              'UT', 'UT')]
        elif (name.find('THD')!=-1) or (name.find('themisd')!=-1):
            themis_d.append(df)
            if (name.find('THD')!=-1) and (len(themis_d)>1):
                themis_d = [interp_combine_dfs(themis_d[0],themis_d[-1],
                                              'UT', 'UT')]
        elif (name.find('THE')!=-1) or (name.find('themise')!=-1):
            themis_e.append(df)
            if (name.find('THE')!=-1) and (len(themis_e)>1):
                themis_e = [interp_combine_dfs(themis_e[0],themis_e[-1],
                                              'UT', 'UT')]
        elif (name.find('crossing')!=-1):
            cross.append(df)
    return themis_a, themis_b, themis_c, themis_d, themis_e, cross
def split_cluster(dflist):
    """Function splits themis satellite data in big list into each probe
    Inputs
        dflist
    Outputs
        themis_a.. themis_e
    """
    cluster1,cluster2,cluster3,cluster4=[],[],[],[]
    for df in dflist:
        name = df['name'].iloc[-1]
        if (name.find('C1')!=-1) or (name.find('cluster1')!=-1):
            cluster1.append(df)
            if (name.find('C1')!=-1) and (len(cluster1)>1):
                cluster1 = [interp_combine_dfs(cluster1[0],cluster1[-1],
                                              'UT', 'UT')]
        elif (name.find('C2')!=-1) or (name.find('cluster2')!=-1):
            cluster2.append(df)
            if (name.find('C2')!=-1) and (len(cluster2)>1):
                cluster2 = [interp_combine_dfs(cluster2[0],cluster2[-1],
                                              'UT', 'UT')]
        elif (name.find('C3')!=-1) or (name.find('cluster3')!=-1):
            cluster3.append(df)
            if (name.find('C3')!=-1) and (len(cluster3)>1):
                cluster3 = [interp_combine_dfs(cluster3[0],cluster3[-1],
                                              'UT', 'UT')]
        elif (name.find('C4')!=-1) or (name.find('cluster4')!=-1):
            cluster4.append(df)
            if (name.find('C4')!=-1) and (len(cluster4)>1):
                cluster4 = [interp_combine_dfs(cluster4[0],cluster4[-1],
                                              'UT', 'UT')]
    return cluster1, cluster2, cluster3, cluster4
def geotail_to_df(obsdict, *, satkey='geotail', crosskey='crossings'):
    """Function returns data frame using dict to find file and satkey for
        which satellite data to pull
    Inputs
        obsdict- dictionary with filepaths for different satellites
        satkey- satellite key for dictionary
        crosskey- crossing file indication key for dictionary
    Outputs
        dflist
    """
    dflist = []
    for satfile in obsdict.get(satkey,[]):
        if os.path.exists(satfile):
            name = satfile.split('/')[-1].split('_')[1]
            if (satfile.find(crosskey)!=-1) and (
                                     satfile.lower().find(satkey)!=-1):
                df = pd.read_csv(satfile, header=0, sep='\s+',
                                parse_dates={'TIME':['YYYYMMDD', 'UT']},
                                date_parser=datetimeparser4,
                                infer_datetime_format=True,index_col=False)
                df = df.rename(columns={'TIME':'UT'})
                nametag = pd.Series({'name':(name+'_crossings').lower()})
            elif (satfile.find('MGF')!=-1) or (satfile.find('CPI')!=-1):
                heads, feet, skiplen, total_len = [], [], 0, 0
                headerlines = []
                with open(satfile,'r') as mgffile:
                    for line in enumerate(mgffile):
                        if line[1].find('@')!=-1:
                            heads.append([line[0]-1,line[0]+1])
                            feet.append(skiplen)
                            skiplen=0
                            headerlines.append(prev_line)
                        elif line[1].find('#')!=-1:
                            skiplen+=1
                        total_len +=1
                        prev_line = line[1]
                    feet.append(skiplen)
                    for head in enumerate(heads[0:-1]):
                        df=pd.read_csv(satfile,header=head[1][-1],sep='\s+',
                                skipfooter=(total_len-heads[head[0]+1][0]+
                                         feet[head[0]+1]),engine='python',
                                parse_dates={'Time [UT]':['dd-mm-yyyy',
                                                          'hh:mm:ss.ms']},
                                date_parser=datetimeparser2,
                                infer_datetime_format=True,index_col=False)
                        df.columns = pd.Index(headerlines[head[0]].split())
                        nametag = pd.Series({'name':name+'_ELEC'})
                        dflist.append(df.append(nametag,ignore_index=True))
                    #last dataset in the file
                    df = pd.read_csv(satfile, header=heads[-1][-1],
                                     engine='python', sep='\s+',
                                     skipfooter=feet[-1],
                                parse_dates={'Time [UT]':['dd-mm-yyyy',
                                                          'hh:mm:ss.ms']},
                                date_parser=datetimeparser2,
                                infer_datetime_format=True,index_col=False)
                    df.columns = pd.Index(headerlines[-1].split())
                    if (satfile.find('MGF')!=-1):
                        name = name+'_MGF'
                        df = df.rename(columns={'EPOCH':'UT'})
                    elif (satfile.find('CPI')!=-1):
                        name = name+'_CPI'
                        df = df.rename(columns={'CDF_EPOCH':'UT'})
                    nametag = pd.Series({'name':name})
            else:
                df = pd.DataFrame()
            dflist.append(df.append(nametag,ignore_index=True))
            print('{} loaded'.format(nametag))
    return dflist
def cluster_to_df(obsdict, *, satkey='cluster', crosskey='crossings'):
    """Function returns data frame using dict to find file and satkey for
        which satellite data to pull
    Inputs
        obsdict- dictionary with filepaths for different satellites
        satkey- satellite key for dictionary
        crosskey- crossing file indication key for dictionary
    Outputs
        dflist
    """
    dflist = []
    for satfile in obsdict.get(satkey,[]):
        if os.path.exists(satfile):
            name = satfile.split('/')[-1].split('_')[1]
            if (satfile.find(crosskey)!=-1) and (
                                     satfile.lower().find(satkey)!=-1):
                df = pd.read_csv(satfile, header=0, sep='\s+',
                                parse_dates={'TIME':['YYYYMMDD', 'UT']},
                                date_parser=datetimeparser4,
                                infer_datetime_format=True,index_col=False)
                df = df.rename(columns={'TIME':'UT'})
                nametag = pd.Series({'name':(name+'_crossings').lower()})
            elif (satfile.find('PP')!=-1) or (satfile.find('CP')!=-1):
                heads, feet, skiplen, total_len = [], [], 0, 0
                headerlines = []
                with open(satfile,'r') as clfile:
                    for line in enumerate(clfile):
                        if line[1].find('@')!=-1:
                            heads.append([line[0]-1,line[0]+1])
                            feet.append(skiplen)
                            skiplen=0
                            headerlines.append(prev_line)
                        elif line[1].find('#')!=-1:
                            skiplen+=1
                        total_len +=1
                        prev_line = line[1]
                    feet.append(skiplen)
                    df = pd.read_csv(satfile, header=heads[-1][-1],
                                     engine='python', sep='\s+',
                                     skipfooter=feet[-1],
                                parse_dates={'Time [UT]':['dd-mm-yyyy',
                                                          'hh:mm:ss.ms']},
                                date_parser=datetimeparser2,
                                infer_datetime_format=True,index_col=False)
                    df.columns = pd.Index(headerlines[-1].split())
                    if (satfile.find('PP')!=-1):
                        name = name+'_PP'
                        df = df.rename(columns={'EPOCH':'UT'})
                    elif (satfile.find('CP')!=-1):
                        name = name+'_CP'
                    nametag = pd.Series({'name':name})
            else:
                df = pd.DataFrame()
            dflist.append(df.append(nametag,ignore_index=True))
            print('{} loaded'.format(nametag))
    return dflist
def themis_to_df(obsdict, *, satkey='themis', crosskey='crossings'):
    """Function returns data frame using dict to find file and satkey for
        which satellite data to pull
    Inputs
        obsdict- dictionary with filepaths for different satellites
        satkey- satellite key for dictionary
        crosskey- crossing file indication key for dictionary
    Outputs
        dflist
    """
    dflist = []
    for satfile in obsdict.get(satkey,[]):
        if os.path.exists(satfile):
            name = satfile.split('/')[-1].split('_')[1]
            if (satfile.find(crosskey)!=-1) and (satfile.find(satkey)!=-1):
                df = pd.read_csv(satfile, header=42, sep='\s+',
                                parse_dates={'UT':['TIMESTAMP']},
                                date_parser=datetimeparser3,
                                infer_datetime_format=True,index_col=False)
                nametag = pd.Series({'name':(name+'_crossings').lower()})
            elif (satfile.find('MOM')!=-1) or (satfile.find('FGM')!=-1):
                heads, feet, skiplen, total_len = [], [], 0, 0
                headerlines = []
                with open(satfile,'r') as momfile:
                    for line in enumerate(momfile):
                        if line[1].find('@')!=-1:
                            heads.append([line[0]-1,line[0]+1])
                            feet.append(skiplen)
                            skiplen=0
                            headerlines.append(prev_line)
                        elif line[1].find('#')!=-1:
                            skiplen+=1
                        total_len +=1
                        prev_line = line[1]
                    feet.append(skiplen)
                    '''
                    for head in enumerate(heads[0:-1]):
                        df=pd.read_csv(satfile,header=head[1][-1],sep='\s+',
                                skipfooter=(total_len-heads[head[0]+1][0]+
                                         feet[head[0]+1]),engine='python',
                                parse_dates={'Time [UT]':['dd-mm-yyyy',
                                                          'hh:mm:ss.ms']},
                                date_parser=datetimeparser2,
                                infer_datetime_format=True,index_col=False)
                        df.columns = pd.Index(headerlines[head[0]].split())
                        nametag = pd.Series({'name':name+'_ELEC'})
                        dflist.append(df.append(nametag,ignore_index=True))
                        print('{} loaded'.format(nametag))
                    '''
                    df = pd.read_csv(satfile, header=heads[-1][-1],
                                     engine='python', sep='\s+',
                                     skipfooter=feet[-1],
                                parse_dates={'Time [UT]':['dd-mm-yyyy',
                                                          'hh:mm:ss.ms']},
                                date_parser=datetimeparser2,
                                infer_datetime_format=True,index_col=False)
                    df.columns = pd.Index(headerlines[-1].split())
                    df = df.rename(columns={'Time [UT]':'UT'})
                    if satfile.find('FGM')!=-1:
                        name = name+'_FGM'
                    elif satfile.find('MOM')!=-1:
                        name = name+'_MOM'
                    nametag = pd.Series({'name':name})
            else:
                df = pd.DataFrame()
            dflist.append(df.append(nametag,ignore_index=True))
            print('{} loaded'.format(nametag))
    return dflist
def simdata_to_df(simdict, satkey):
    """Function returns data frame using dict to find file and satkey for
        which satellite data to pull
    Inputs
        simdict- dictionary with filepaths for different satellites
        satkey- satellite key for dictionary
    Outputs
        dflist
    """
    dflist = []
    for satfile in simdict.get(satkey,[]):
        if os.path.exists(satfile):
            df = pd.read_csv(satfile, sep='\s+', skiprows=1,
                          parse_dates={'Time [UTC]':['year','mo','dy','hr',
                                                         'mn','sc','msc']},
                          date_parser=datetimeparser,
                          infer_datetime_format=True, keep_date_col=True)
            name = satfile.split('/')[-1].split('_')[1]
            nametag = pd.Series({'name':name})
            dflist.append(df.append(nametag,ignore_index=True))
    return dflist
def interp_combine_dfs(from_df,to_df, from_xkey, to_xkey, *,
                       using_datetimes=True):
    """Function combines two dataframes by interpolating based on given
        x_keys and adding remaining columns from the from_df to to_df
    Inputs
        from_df, to_df- pandas dataframe objects to be combined
        from_xkey, to_xkey- keys used to ID column to interpolate on
        using_datetimes- default true, otw interp should be easier
    Outputs
        combo_df- combined dataframe
    """
    #sort by given keys
    from_df = from_df.sort_values(by=from_xkey)
    to_df = to_df.sort_values(by=to_xkey)
    #pop name to give back later
    name, _ = from_df.pop('name'), to_df.pop('name')
    from_df = from_df.dropna().reset_index(drop=True)
    to_df = to_df.dropna().reset_index(drop=True)
    if using_datetimes:
        #starting time
        starttime = min(to_df[to_xkey].loc[0], from_df[from_xkey].loc[0])
        dfs, xkeys = [from_df, to_df], [from_xkey, to_xkey]
        for df in enumerate([from_df, to_df]):
            #turn xdata into timedelta
            dfs[df[0]]['delta'] = df[1][xkeys[df[0]]]-starttime
        for key in from_df:
            if key!='UT':
                to_df[key]=np.interp(to_df['delta'].values.astype('float'),
                                   from_df['delta'].values.astype('float'),
                                   from_df[key].values.astype('float'))
        to_df['name'] = name.iloc[-1].split('_')[0]+'_obs'
    return to_df
def determine_satelliteIDs(pathtofiles, *,keylist=['cluster','geotail',
                                                 'goes','themis','rbspb']):
    """Function returns dict w/ sat filepaths for each type of satellite
    Inputs
        pathtofiles- can be simulation or observation files
        keylist- used to construct dict, what satellites are expected
    Outputs
        satfiledict- dict with entries for each type, none if not found
    """
    satfiledict = dict.fromkeys(keylist,[])
    for satfile in glob.glob(pathtofiles+'/*'):
        for satkey in keylist:
            if satfile.lower().find(satkey)!=-1:
                satfiledict.update({satkey:satfiledict[satkey]+[satfile]})
    return satfiledict
if __name__ == "__main__":
    datapath = sys.argv[1]
    print('processing satellite output at {}'.format(datapath))
    obspath = os.path.join(datapath, 'observation')
    simpath = os.path.join(datapath, 'simulation')
    outpath = os.path.join(datapath, 'figures')
    obsdict = determine_satelliteIDs(obspath)
    simdict = determine_satelliteIDs(simpath)
    #geotail
    geo_dfs_sim = simdata_to_df(simdict, 'geotail')
    geo_dfs_sim = add_derived_variables(geo_dfs_sim)
    geo_dfs_obs = geotail_to_df(obsdict)
    [geo, geo_cross] = split_geotail(geo_dfs_obs)
    [sgeo, _] = split_geotail(geo_dfs_sim)
    #themis
    themis_dfs_sim = simdata_to_df(simdict, 'themis')
    themis_dfs_sim = add_derived_variables(themis_dfs_sim)
    themis_dfs_obs = themis_to_df(obsdict)
    [th_a,th_b,th_c,th_d,th_e,th_cross] = split_themis(themis_dfs_obs)
    [sth_a,sth_b,sth_c,sth_d,sth_e,_] = split_themis(themis_dfs_sim)
    #cluster
    cluster_dfs_sim = simdata_to_df(simdict, 'cluster')
    cluster_dfs_sim = add_derived_variables(cluster_dfs_sim)
    cluster_dfs_obs = cluster_to_df(obsdict)
    [cl1,cl2,cl3,cl4] = split_cluster(cluster_dfs_obs)
    [scl1,scl2,scl3,scl4] = split_cluster(cluster_dfs_sim)
    #Add derived variables for observation datasets
    [th_a,th_b,th_c,th_d,th_e] = add_derived_variables(
                                                [th_a[0],th_b[0],th_c[0],th_d[0],th_e[0]],
                                                obs=True)
    [cl1,cl2,cl3,cl4] = add_derived_variables([cl1[0],cl2[0],cl3[0],cl4[0]],obs=True)
    [geo] = add_derived_variables([geo[0]],obs=True)
    #combine simulation and observation into one list
    th_a = [th_a, sth_a[0]]
    th_b = [th_b, sth_b[0]]
    th_c = [th_c, sth_c[0]]
    th_d = [th_d, sth_d[0]]
    th_e = [th_e, sth_e[0]]
    geo = [geo, sgeo[0]]
    cl1 = [cl1, scl1[0]]
    cl2 = [cl2, scl2[0]]
    cl3 = [cl3, scl3[0]]
    cl4 = [cl4, scl4[0]]
    #set text settings
    plt.rcParams.update({
        "text.usetex": True,
        "font.family": "sans-serif",
        "font.size": 18,
        "font.sans-serif": ["Helvetica"]})
    ######################################################################
    #B magnitude
    if True:
        figname = 'Bmagnitude'
        Bmag_themis, (ax1,ax2,ax3,ax4,ax5) = plt.subplots(nrows=5, ncols=1,
                                                   sharex=True,
                                                   figsize=[12,20],
                                                   facecolor='gainsboro')
        Bmag_geo, (geoax1) = plt.subplots(nrows=1, ncols=1,
                                                   figsize=[12,4],
                                                   facecolor='gainsboro')
        Bmag_cluster, (clax1,clax2,clax3,clax4) = plt.subplots(nrows=4,
                                                   ncols=1,
                                                   sharex=True,
                                                   figsize=[12,16],
                                                   facecolor='gainsboro')
        Bmag_themis.tight_layout(pad=2)
        Bmag_geo.tight_layout(pad=2)
        Bmag_cluster.tight_layout(pad=2)
        ylabel = r'$\displaystyle B_{mag} (nT)$'
        plot_Bmag(ax1, th_a, ylabel)
        plot_Bmag(ax2, th_b, ylabel, ylim=[0,40])
        plot_Bmag(ax3, th_c, ylabel, ylim=[0,40])
        plot_Bmag(ax4, th_d, ylabel)
        plot_Bmag(ax5, th_e, ylabel)
        plot_Bmag(geoax1, geo, ylabel, ylim=[0,40])
        plot_Bmag(clax1, cl1, ylabel)
        plot_Bmag(clax2, cl2, ylabel)
        plot_Bmag(clax3, cl3, ylabel)
        plot_Bmag(clax4, cl4, ylabel)
        probe = ['a','b','c','d','e']
        for ax in enumerate([ax1,ax2,ax3,ax4,ax5]):
            ax[1].set_facecolor('olive')
            mark_cross_themis(ax[1], th_cross[0], probe=probe[ax[0]])
        for ax in enumerate([geoax1]):
            ax[1].set_facecolor('olive')
            mark_cross_geotail(ax[1], geo_cross[0])
        for ax in enumerate([clax1, clax2, clax3, clax4]):
            ax[1].set_facecolor('olive')
        Bmag_themis.savefig(outpath+'/{}_themis.png'.format(figname),
                      facecolor='gainsboro')
        Bmag_geo.savefig(outpath+'/{}_geo.png'.format(figname),
                      facecolor='gainsboro')
        Bmag_cluster.savefig(outpath+'/{}_cluster.png'.format(figname),
                      facecolor='gainsboro')
    ######################################################################
    # Betastar magnetosphere
    if True:
        figname = 'Magnetosphere'
        Mag_themis, (ax1,ax2,ax3,ax4,ax5) = plt.subplots(nrows=5, ncols=1,
                                                   sharex=True,
                                                   figsize=[12,20],
                                                   facecolor='gainsboro')
        Mag_geo, (geoax1) = plt.subplots(nrows=1, ncols=1,
                                                   figsize=[12,4],
                                                   facecolor='gainsboro')
        Mag_cluster, (clax1,clax2,clax3,clax4) = plt.subplots(nrows=4,
                                                   ncols=1,
                                                   sharex=True,
                                                   figsize=[12,16],
                                                   facecolor='gainsboro')
        Mag_themis.tight_layout(pad=2)
        Mag_geo.tight_layout(pad=2)
        Mag_cluster.tight_layout(pad=2)
        ylabel = r'$\textit{Magnetosphere}$'
        plot_Magnetosphere(ax1, th_a, ylabel)
        plot_Magnetosphere(ax2, th_b, ylabel)
        plot_Magnetosphere(ax3, th_c, ylabel)
        plot_Magnetosphere(ax4, th_d, ylabel)
        plot_Magnetosphere(ax5, th_e, ylabel)
        plot_Magnetosphere(geoax1, geo, ylabel)
        plot_Magnetosphere(clax1, cl1, ylabel)
        plot_Magnetosphere(clax2, cl2, ylabel)
        plot_Magnetosphere(clax3, cl3, ylabel)
        plot_Magnetosphere(clax4, cl4, ylabel)
        for ax in enumerate([ax1,ax2,ax3,ax4,ax5]):
            ax[1].set_facecolor('olive')
            mark_cross_themis(ax[1], th_cross[0], probe=probe[ax[0]])
        for ax in enumerate([geoax1]):
            ax[1].set_facecolor('olive')
            mark_cross_geotail(ax[1], geo_cross[0])
        for ax in enumerate([clax1, clax2, clax3, clax4]):
            ax[1].set_facecolor('olive')
        Mag_themis.savefig(outpath+'/{}_themis.png'.format(figname),
                      facecolor='gainsboro')
        Mag_geo.savefig(outpath+'/{}_geo.png'.format(figname),
                      facecolor='gainsboro')
        Mag_cluster.savefig(outpath+'/{}_cluster.png'.format(figname),
                      facecolor='gainsboro')
    ######################################################################
    # Betastar magnetosphere
    if True:
        figname = 'Betastar'
        Beta_themis, (ax1,ax2,ax3,ax4,ax5) = plt.subplots(nrows=5, ncols=1,
                                                   sharex=True,
                                                   figsize=[12,20],
                                                   facecolor='gainsboro')
        Beta_geo, (geoax1) = plt.subplots(nrows=1, ncols=1,
                                                   figsize=[12,4],
                                                   facecolor='gainsboro')
        Beta_cluster, (clax1,clax2,clax3,clax4) = plt.subplots(nrows=4,
                                                   ncols=1,
                                                   sharex=True,
                                                   figsize=[12,16],
                                                   facecolor='gainsboro')
        Beta_themis.tight_layout(pad=2)
        Beta_geo.tight_layout(pad=2)
        Beta_cluster.tight_layout(pad=2)
        ylabel = r'$\displaystyle \beta^{*}$'
        plot_Betastar(ax1, th_a, ylabel)
        plot_Betastar(ax2, th_b, ylabel)
        plot_Betastar(ax3, th_c, ylabel)
        plot_Betastar(ax4, th_d, ylabel)
        plot_Betastar(ax5, th_e, ylabel)
        plot_Betastar(geoax1, geo, ylabel)
        plot_Betastar(clax1, cl1, ylabel)
        plot_Betastar(clax2, cl2, ylabel)
        plot_Betastar(clax3, cl3, ylabel)
        plot_Betastar(clax4, cl4, ylabel)
        for ax in enumerate([ax1,ax2,ax3,ax4,ax5]):
            ax[1].set_facecolor('olive')
            mark_cross_themis(ax[1], th_cross[0], probe=probe[ax[0]])
        for ax in enumerate([geoax1]):
            ax[1].set_facecolor('olive')
            mark_cross_geotail(ax[1], geo_cross[0])
        for ax in enumerate([clax1, clax2, clax3, clax4]):
            ax[1].set_facecolor('olive')
        Beta_themis.savefig(outpath+'/{}_themis.png'.format(figname),
                      facecolor='gainsboro')
        Beta_geo.savefig(outpath+'/{}_geo.png'.format(figname),
                      facecolor='gainsboro')
        Beta_cluster.savefig(outpath+'/{}_cluster.png'.format(figname),
                      facecolor='gainsboro')
    ######################################################################