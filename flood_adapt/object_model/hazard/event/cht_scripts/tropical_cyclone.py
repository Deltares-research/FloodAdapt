# -*- coding: utf-8 -*-
"""
Tropical Cyclone Module in the Coastal Hazards Toolkit

Module supports two classes
    TropicalCyclone:             deterministic simulations
    TropicalCycloneEnsemble      probablistic simulations using the simplified DeMaria et al. (2009) approach

    To do list - priority
        netcdf spiderwebs

    To do list - 'nice to haves'
        make reading of ddb_cyc not file size related but using actual keywords (since format are changing)
        add more reading formats (e.g. NHC, JTWC, etc.)
        enable coordinate conversions; now it is all WGS 84
"""

# Modules needed
import os
import fiona
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from scipy.interpolate import interp1d, CubicSpline
from scipy.ndimage.filters import uniform_filter1d
from shapely.geometry import Point, LineString, MultiLineString, mapping

# Settings
dateformat_module   = "%Y%m%d %H%M%S"
knots_to_ms         = float(0.51444)
nm_to_km            = float(1.852)
nm_to_m             = float(1.852)*1000
pd.options.mode.chained_assignment = None

# Classes of the Tropical Cyclone module
class TropicalCyclone:
    
    # Init
    def __init__(self,name=None):
        
        # Header
        self.name                       = name                    # name of the tropical cyclone
        self.wind_profile               = 'holland2010'           # parametric wind profile: holland2010, holland2008, holland1980
        self.wind_pressure_relation     = 'holland2008'           # relationship used to determine pressure or wind speed if one is unknown
        self.rmw_relation               = 'nederhoff2019'         # relationship used to determine RMW (needed for most wind profiles)
        self.background_pressure        = 1012.0                  # background pressure in Pa
        self.phi_spiral                 = 20.0                    # phi spiral
        self.wind_conversion_factor     = 0.93                    # conversion factor from 1-min to 10-minute winds (if needed)
        self.spiderweb_radius           = 1000.0                  # radius in km
        self.nr_radial_bins             = int(500)                # number of radial bins
        self.nr_directional_bins        = int(36)                 # number of directional bins
        self.debug                      = 0                       # do not show prints =0; change to 1 to show prints
        
        self.low_wind_speeds_cut_off    = 0.0                     # float that is used to trim the track when making spiderwebs  
        self.extend_track               = 0.0                     # with certain amount of days
        self.rho_air                    = 1.15                    # used in the determination of parametric wind field
        self.asymmetry_option           = 'schwerdt1979'          # asymmetry_options: schwerdt1979, mvo, none
        self.reference_time             = datetime(1970,1,1)      # used when writing out spiderweb
        self.include_rainfall           = False                   # logic: 0 is no and 1 is yes
        self.rainfall_relationship      = 'ipet'                  # rainfall_relationship: ipet
        self.rainfall_factor            = 1.0                     # factor to calibrate rainfall

        # New keywords to keep track of units in intensity, wind radii and coordinate system
        self.unit_intensity             = 'knots'                 # float 
        self.unit_radii                 = 'nm'                    # nm
        self.EPSG                       = 4326
        
        # Track itself - create a dummy point
        point                           = Point(0,0)
        self.track  = gpd.GeoDataFrame({"datetime": [0], "geometry": [point] , "vmax": [0], "pc": [0], "RMW": [0],
                                        "R35_NE": [0], "R35_SE": [0],"R35_SW": [0],"R35_NW": [0],
                                        "R50_NE": [0], "R50_SE": [0],"R50_SW": [0],"R50_NW": [0],
                                        "R65_NE": [0], "R65_SE": [0],"R65_SW": [0],"R65_NW": [0],
                                        "R100_NE": [0], "R100_SE": [0],"R100_SW": [0],"R100_NW": [0]})        
        self.track.set_crs(epsg=self.EPSG, inplace=True)
        
        # Done 
        self.creation_time= datetime.now()
        
        
    # Reading
    def from_jmv30(self, filename):        
        self.read_track(filename, 'jmv30')

    def from_ddb_cyc(self, filename):        
        self.read_track(filename, 'ddb_cyc')

    def read_track(self, filename, fmt):
        
        # If ddb_cyc
        if fmt == 'ddb_cyc':
            
            # Read all the lines first
            with open(filename, 'r') as f:
                lines = f.readlines()
            
            
            # Define the name first
            for line in lines:
                if line[0:4] == 'Name':                    
                    string_value    = line[5:]
                    string_value    = ''.join(ch for ch in string_value if ch.isalnum())
                    self.name       = string_value
            
            
            # Define other variables names (if they exist)
            for i in range(len(lines)):
                line = lines[i]
                if line[0:11] == 'WindProfile':    
                    string_value                    = line[23:]
                    string_value                    = ''.join(ch for ch in string_value if ch.isalnum())
                    self.wind_profile               = string_value
                if line[0:20] == 'WindPressureRelation':    
                    string_value                    = line[23:]
                    string_value                    = ''.join(ch for ch in string_value if ch.isalnum())
                    self.wind_pressure_relation     = string_value
                if line[0:12] == 'RMaxRelation':    
                    string_value                    = line[23:]
                    string_value                    = ''.join(ch for ch in string_value if ch.isalnum())
                    self.rmw_relation               = string_value
                if line[0:18] == 'Backgroundpressure':    
                    string_value                    = line[23:]
                    string_value                    = ''.join(ch for ch in string_value if ch.isalnum())
                    self.background_pressure        = float(string_value)
                if line[0:9] == 'PhiSpiral':    
                    string_value                    = line[23:]
                    string_value                    = ''.join(ch for ch in string_value if ch.isalnum())
                    self.phi_spiral                 = float(string_value)
                if line[0:20] == 'WindConversionFactor':    
                    string_value                    = line[23:]
                    self.wind_conversion_factor     = float(string_value)
                if line[0:15] == 'SpiderwebRadius':    
                    string_value                    = line[23:]
                    string_value                    = ''.join(ch for ch in string_value if ch.isalnum())
                    self.spiderweb_radius           = float(string_value)
                if line[0:12] == 'NrRadialBins':    
                    string_value                    = line[23:]
                    string_value                    = ''.join(ch for ch in string_value if ch.isalnum())
                    self.nr_radial_bins             = int(string_value)
                if line[0:17] == 'NrDirectionalBins':    
                    string_value                    = line[23:]
                    string_value                    = ''.join(ch for ch in string_value if ch.isalnum())
                    self.nr_directional_bins        = int(string_value)
                    
                    
            # Read the track
            for i in range(len(lines)):
                line = lines[i]
                if line[0:8] == '#   Date':                    
                     break
            
            # Place coordinates in Tropical Cyclone Track 
            for j in range(i+2,len(lines)):
                
                # Get values
                line            = lines[j]
                line            = line.split()
                date_format     = "%Y%m%d %H%M%S"
                date_string     = line[0]  + ' ' + line[1] 
                tc_time         = datetime.strptime(date_string, date_format)
                tc_time_string  = tc_time.strftime(date_format)
                y               = float(line[2])
                x               = float(line[3])
                vmax            = float(line[4])
                pc              = float(line[5])
                RMW             = float(line[6])
                
                R35_NE          = float(line[7])
                R35_SE          = float(line[8])
                R35_SW          = float(line[9])
                R35_NW          = float(line[10])

                R50_NE          = float(line[11])
                R50_SE          = float(line[12])
                R50_SW          = float(line[13])
                R50_NW          = float(line[14])

                R65_NE          = float(line[15])
                R65_SE          = float(line[16])
                R65_SW          = float(line[17])
                R65_NW          = float(line[18])

                R100_NE         = float(line[19])
                R100_SE         = float(line[20])
                R100_SW         = float(line[21])
                R100_NW         = float(line[22])


                # Make GeoDataFrame     
                point       = Point(x,y)
                gdf         = gpd.GeoDataFrame({"datetime": [tc_time_string],"geometry": [point], "vmax": [vmax], "pc": [pc], "RMW": [RMW],
                                        "R35_NE":  [R35_NE],  "R35_SE":  [R35_SE], "R35_SW":  [R35_SW],  "R35_NW": [R35_NW],
                                        "R50_NE":  [R50_NE],  "R50_SE":  [R50_SE], "R50_SW":  [R50_SW],  "R50_NW": [R50_NW],
                                        "R65_NE":  [R65_NE],  "R65_SE":  [R65_SE], "R65_SW":  [R65_SW],  "R65_NW": [R65_NW],
                                        "R100_NE": [R100_NE], "R100_SE": [R100_SE],"R100_SW": [R100_SW], "R100_NW": [R100_NW]})    
                gdf.set_crs(epsg=self.EPSG, inplace=True)
               
                # Append self
                self.track = pd.concat([self.track,gdf]) 
            
            # Done with this
            self.track = self.track.reset_index(drop=True)
            self.track = self.track.drop([0])           # remove the dummy
            self.track = self.track.reset_index(drop=True)
            if self.debug == 1: print('Succesfully read track - ddb_cyc')

        elif fmt == 'jmv30':
            print("to do: work on progress")
        else: 
            raise Exception('This file format is not supported as read track!')


    # Writing 
    def write_track(self, filename, fmt):
        
        # If ddb_cyc
        if fmt == 'ddb_cyc':
            
            # Open file
            with open(filename, 'wt') as f:
                
                 # Print header
                f.writelines('# Tropical Cyclone Toolbox - Coastal Hazards Toolkit - ' + self.creation_time.strftime(dateformat_module) + '\n')
  
                # Print rest
                f.writelines('Name                   ' + self.name + '\n')
                f.writelines('WindProfile            ' + self.wind_profile + '\n')
                f.writelines('WindPressureRelation   ' + self.wind_pressure_relation + '\n')
                f.writelines('RMaxRelation           ' + self.rmw_relation + '\n')
                f.writelines('Backgroundpressure     ' + str(self.background_pressure) + '\n')
                f.writelines('PhiSpiral              ' + str(self.phi_spiral) + '\n')
                f.writelines('WindConversionFactor   ' + str(self.wind_conversion_factor) + '\n')
                f.writelines('SpiderwebRadius        ' + str(self.spiderweb_radius) + '\n')
                f.writelines('NrRadialBins           ' + str(self.nr_radial_bins) + '\n')
                f.writelines('NrDirectionalBins      ' + str(self.nr_directional_bins) + '\n')
                epsg        = self.track.crs.name
                f.writelines('EPSG                   ' + epsg + '\n')
                f.writelines('UnitIntensity          ' + str(self.unit_intensity) + '\n')
                f.writelines('UnitWindRadii          ' + str(self.unit_radii) + '\n')

                # Print header for the track
                f.writelines('#  \n')
                f.writelines('##    Datetime               Lat        Lon         Vmax       Pc          Rmax         R35(NE)      R35(SE)     R35(SW)     R35(NW)     R50(NE)     R50(SE)    R50(SW)    R50(NW)     R65(NE)     R65(SE)     R65(SW)     R65(NW)    R100(NE)    R100(SE)    R100(SW)    R100(NE)  \n')

                # Print the actual track
                for i in range(len(self.track)):
                    f.writelines(self.track.datetime[i].rjust(20))
                    coords = self.track.geometry[i]
                    f.writelines(str(round(coords.y,2)).rjust(12))
                    f.writelines(str(round(coords.x,2)).rjust(12))
                    
                    f.writelines(str(round(self.track.vmax[i],1)).rjust(12))
                    f.writelines(str(round(self.track.pc[i],1)).rjust(12))
                    f.writelines(str(round(self.track.RMW[i],1)).rjust(12))
                    
                    f.writelines(str(round(self.track.R35_NE[i],1)).rjust(12))
                    f.writelines(str(round(self.track.R35_SE[i],1)).rjust(12))
                    f.writelines(str(round(self.track.R35_SW[i],1)).rjust(12))
                    f.writelines(str(round(self.track.R35_NW[i],1)).rjust(12))
                    
                    f.writelines(str(round(self.track.R50_NE[i],1)).rjust(12))
                    f.writelines(str(round(self.track.R50_SE[i],1)).rjust(12))
                    f.writelines(str(round(self.track.R50_SW[i],1)).rjust(12))
                    f.writelines(str(round(self.track.R50_NW[i],1)).rjust(12))

                    f.writelines(str(round(self.track.R65_NE[i],1)).rjust(12))
                    f.writelines(str(round(self.track.R65_SE[i],1)).rjust(12))
                    f.writelines(str(round(self.track.R65_SW[i],1)).rjust(12))
                    f.writelines(str(round(self.track.R65_NW[i],1)).rjust(12))

                    f.writelines(str(round(self.track.R100_NE[i],1)).rjust(12))
                    f.writelines(str(round(self.track.R100_SE[i],1)).rjust(12))
                    f.writelines(str(round(self.track.R100_SW[i],1)).rjust(12))
                    f.writelines(str(round(self.track.R100_NW[i],1)).rjust(12))
                    
                    f.writelines('\n')

            if self.debug == 1: print('Succesfully written track - ddb_cyc')
        else: 
            print('For other methods of writing the track; please used the "tc.track.to_file" option')


    # Support functions for creating spiderweb
    # 1. estimate_missing_values => still assuming imperial system
    def estimate_missing_values(self):
        
        # Go over the track and determine missing values
        for it in range(len(self.track)):
            
            # Get coordinates
            coords_it       = self.track.geometry[it]            


            # determine wind speed
            if self.track.vmax[it] < 0:
                if self.wind_pressure_relation == 'holland2008':
                    
                    # estimate this: vmax is in m/s
                    vmax      =  wpr_holland2008(pc     = self.track.pc[it],
                                           pn           = self.background_pressure, 
                                           phi          = coords_it.y,
                                           dpcdt        = self.track.dpcdt[it],
                                           vt           = np.sqrt(self.track.vtx[it]**2 + self.track.vty[it]**2), 
                                           rhoa         = self.rho_air)
                    
                    # place this 
                    if self.unit_intensity == 'knots':
                        self.track.vmax[it] = vmax / knots_to_ms
                    else:
                        self.track.vmax[it] = vmax
 
            
            
            # determine pressure
            if self.track.pc[it] < 0:
                if self.wind_pressure_relation == 'holland2008':
                    
                    # estimate this
                    if self.unit_intensity == 'knots':
                        pc      =  wpr_holland2008(vmax     = self.track.vmax[it]*knots_to_ms,
                                                   pn       = self.background_pressure, 
                                                   phi      = coords_it.y,
                                                   dpcdt        = self.track.dpcdt[it],
                                                   vt           = np.sqrt(self.track.vtx[it]**2 + self.track.vty[it]**2), 
                                                   rhoa     = self.rho_air)
                    else:
                        pc      =  wpr_holland2008(vmax     = self.track.vmax[it],
                                                   pn       = self.background_pressure, 
                                                   phi      = coords_it.y,
                                                   dpcdt    = self.track.dpcdt[it],
                                                   vt       = np.sqrt(self.track.vtx[it]**2 + self.track.vty[it]**2), 
                                                   rhoa     = self.rho_air)
                            
                    # place this
                    self.track.pc[it] = pc


            # radius of maximum winds (RMW)
            if self.track.RMW[it] < 0:
                
                # Nederhoff et al. 2019
                if self.rmw_relation == 'nederhoff2019':
                    
                    # Estimate: relationship assume m/s
                    if self.unit_intensity == 'knots':
                        [rmax, dr35]        = wind_radii_nederhoff(self.track.vmax[it]/knots_to_ms, coords_it.y, 0, 0)
                    else:
                        [rmax, dr35]        = wind_radii_nederhoff(self.track.vmax[it], coords_it.y, 0, 0)
                        
                    # Place value: output is in km
                    if self.unit_radii == 'nm':
                        self.track.RMW[it]  = rmax['mode']/nm_to_km
                    else:
                        self.track.RMW[it]  = rmax['mode']
                
                
                # Gross et al. 2004
                elif self.rmw_relation == 'gross2004':
                    
                    # Estimate: relationship assume knots
                    if self.unit_radii == 'knots':
                        rmax                = 35.37 - 0.11100*self.track.vmax[it] + 0.5700*(abs(coords_it.y)-25)
                    else:
                        rmax                = 35.37 - 0.11100*self.track.vmax[it]*knots_to_ms + 0.5700*(abs(coords_it.y)-25)
                
                    # Place value: output is in nm
                    if self.unit_radii == 'nm':
                        self.track.RMW[it]  = rmax
                    else:
                        self.track.RMW[it]  = rmax*nm_to_km
                
                
                # Simple constant value of 25 nm    
                elif self.rmw_relation == 'constant_25nm':
                    
                    # Place 25 nm
                    if self.unit_radii == 'nm':
                        self.track.RMW[it]  = float(25)
                    else:
                        self.track.RMW[it]  = float(25)*nm_to_km
                    
                    
                    
            # radius of gale force winds (R35)
            if self.wind_profile == 'holland2010':
                if self.track.vmax[it] >= 35:
                    if (self.track.R35_NE[it] == -999) and (self.track.R35_SE[it] == -999) and (self.track.R35_SW[it] == -999) and (self.track.R35_NW[it] == -999) :
                        
                        # Estimate values
                        if self.unit_radii == 'knots':
                            [rmax, dr35]            = wind_radii_nederhoff(self.track.vmax[it]*knots_to_ms, coords_it.y, 0, 0)
                        else:
                            [rmax, dr35]        = wind_radii_nederhoff(self.track.vmax[it], coords_it.y, 0, 0)
                            
                        if self.unit_radii == 'nm':    
                            self.track.R35_NE[it]   = dr35['mode']/nm_to_km + self.track.RMW[it]
                            self.track.R35_SE[it]   = dr35['mode']/nm_to_km + self.track.RMW[it]
                            self.track.R35_SW[it]   = dr35['mode']/nm_to_km + self.track.RMW[it]
                            self.track.R35_NW[it]   = dr35['mode']/nm_to_km + self.track.RMW[it]
                        else:
                            self.track.R35_NE[it]   = dr35['mode'] + self.track.RMW[it]
                            self.track.R35_SE[it]   = dr35['mode'] + self.track.RMW[it]
                            self.track.R35_SW[it]   = dr35['mode'] + self.track.RMW[it]
                            self.track.R35_NW[it]   = dr35['mode'] + self.track.RMW[it]

    
    
    # 2A. cut_off_low_wind_speeds
    def cut_off_low_wind_speeds(self):
        
        # Only apply this when the cut_off wind is defined
        if self.low_wind_speeds_cut_off > 0.0:
        
            # Find first
            ifirst = []
            for it in range(len(self.track)):
                if self.track.vmax[it] >= self.low_wind_speeds_cut_off and not ifirst:
                    ifirst = it
                    break
            if ifirst>0:
                self.track = self.track.drop(list(range(0, ifirst)))
                self.track = self.track.reset_index(drop=True)
                
            # Find last
            ilast = []
            for it in range(len(self.track)-1, 0-1 , -1):
                if self.track.vmax[it] >= self.low_wind_speeds_cut_off and not ilast:
                    ilast = it
                    break
            if ilast:
                self.track = self.track.drop(list(range(ilast+1, len(self.track))))
                self.track = self.track.reset_index(drop=True)
            
            
        else:
            if self.debug == 1: print('No cut_off_low_wind_speeds since wind speed is zero or lower')


    # 2B. Extent track with certain number of days
    def extent_track(self):

        # Only apply this when the extend days are defined
        if self.extend_track > 0.0:

            # Compute last gradient
            it_last         = len(self.track)-1
            coords2         = self.track.geometry[it_last]   # last
            datetime2       = datetime.strptime(self.track.datetime[it_last], dateformat_module)

            it              = len(self.track)-2
            coords1         = self.track.geometry[it]   # first
            datetime1       = datetime.strptime(self.track.datetime[it], dateformat_module)
            dx              = (coords2.x - coords1.x) 
            dy              = (coords2.y - coords1.y) 
            dt              = datetime2 - datetime1

            # Extending the track
            for i in range(1,int(self.extend_track)):

                # Get location
                dt_factor       = 86400/dt.seconds  
                x               = coords2.x + dx*dt_factor*i
                y               = coords2.y + dy*dt_factor*i
                point           = Point(x,y)

                # Make time
                date_format     = "%Y%m%d %H%M%S"
                tc_time         = datetime.strptime(self.track.datetime[it_last], date_format)
                tc_time         = tc_time + timedelta(days=i)
                tc_time_string  = tc_time.strftime(date_format)
                # print(tc_time_string)

                # Make GeoDataFrame 
                gdf             = gpd.GeoDataFrame({"datetime": [tc_time_string],"geometry": [point], "vmax": [self.track.vmax[it_last]], "pc": [self.track.pc[it_last]], "RMW": [self.track.RMW[it_last]],
                                        "R35_NE":  [0],  "R35_SE":  [0], "R35_SW":  [0],  "R35_NW": [0],
                                        "R50_NE":  [0],  "R50_SE":  [0], "R50_SW":  [0],  "R50_NW": [0],
                                        "R65_NE":  [0],  "R65_SE":  [0], "R65_SW":  [0],  "R65_NW": [0],
                                        "R100_NE": [0], "R100_SE": [0],"R100_SW": [0], "R100_NW": [0]})    
                gdf.set_crs(epsg=self.EPSG, inplace=True)
               
                # Append self
                self.track = pd.concat([self.track,gdf]) 

            # Done
            self.track = self.track.reset_index(drop=True)
            if self.debug == 1: print('Succesfully extended track')

        else:
            if self.debug == 1: print('No extending since number of days is zero or lower')
    

    # 3A. convert_units_imperial_metric
    def convert_units_imperial_metric(self):
        
        # Convert wind speeds
        # from  knots   - typically 1-minute averaged 
        # to    m/s     - we account for conversion here
        if (self.unit_intensity == 'knots') and (self.unit_radii == 'nm'):
        
            # Intensity first
            self.track.vmax     = self.track.vmax * knots_to_ms * self.wind_conversion_factor
              
            # Convert radius of maximum winds
            self.track.RMW      = self.track.RMW * nm_to_km
    
            # Convert wind radii
            for it in range(len(self.track)):
                
                # R35
                if self.track.R35_NE[it] > 0:
                    self.track.R35_NE[it]  = self.track.R35_NE[it]* nm_to_km
                else:
                    self.track.R35_NE[it]  = np.NaN
            
                if self.track.R35_SE[it] > 0:
                    self.track.R35_SE[it]  = self.track.R35_SE[it]* nm_to_km
                else:
                    self.track.R35_SE[it]  = np.NaN
            
                if self.track.R35_SW[it] > 0:
                    self.track.R35_SW[it]  = self.track.R35_SW[it]* nm_to_km
                else:
                    self.track.R35_SW[it]  = np.NaN
            
                if self.track.R35_NW[it] > 0:
                    self.track.R35_NW[it]  = self.track.R35_NW[it]* nm_to_km
                else:
                    self.track.R35_NW[it]  = np.NaN
                    
                # R50
                if self.track.R50_NE[it] > 0:
                    self.track.R50_NE[it]  = self.track.R50_NE[it]* nm_to_km
                else:
                    self.track.R50_NE[it]  = np.NaN
            
                if self.track.R50_SE[it] > 0:
                    self.track.R50_SE[it]  = self.track.R50_SE[it]* nm_to_km
                else:
                    self.track.R50_SE[it]  = np.NaN
            
                if self.track.R50_SW[it] > 0:
                    self.track.R50_SW[it]  = self.track.R50_SW[it]* nm_to_km
                else:
                    self.track.R50_SW[it]  = np.NaN
            
                if self.track.R50_NW[it] > 0:
                    self.track.R50_NW[it]  = self.track.R50_NW[it]* nm_to_km
                else:
                    self.track.R50_NW[it]  = np.NaN
            
                # R65
                if self.track.R65_NE[it] > 0:
                    self.track.R65_NE[it]  = self.track.R65_NE[it]* nm_to_km
                else:
                    self.track.R65_NE[it]  = np.NaN
            
                if self.track.R65_SE[it] > 0:
                    self.track.R65_SE[it]  = self.track.R65_SE[it]* nm_to_km
                else:
                    self.track.R65_SE[it]  = np.NaN
            
                if self.track.R65_SW[it] > 0:
                    self.track.R65_SW[it]  = self.track.R65_SW[it]* nm_to_km
                else:
                    self.track.R65_SW[it]  = np.NaN
            
                if self.track.R65_NW[it] > 0:
                    self.track.R65_NW[it]  = self.track.R65_NW[it]* nm_to_km
                else:
                    self.track.R65_NW[it]  = np.NaN
            
                # R100
                if self.track.R100_NE[it] > 0:
                    self.track.R100_NE[it]  = self.track.R100_NE[it]* nm_to_km
                else:
                    self.track.R100_NE[it]  = np.NaN
            
                if self.track.R100_SE[it] > 0:
                    self.track.R100_SE[it]  = self.track.R100_SE[it]* nm_to_km
                else:
                    self.track.R100_SE[it]  = np.NaN
            
                if self.track.R100_SW[it] > 0:
                    self.track.R100_SW[it]  = self.track.R100_SW[it]* nm_to_km
                else:
                    self.track.R100_SW[it]  = np.NaN
            
                if self.track.R100_NW[it] > 0:
                    self.track.R100_NW[it]  = self.track.R100_NW[it]* nm_to_km
                else:
                    self.track.R100_NW[it]  = np.NaN
        
            # Done, so set variable 
            self.unit_intensity   = 'ms'             
            self.unit_radii       = 'km'     
            if self.debug == 1: print('convert units to metric system')
            
        else:
            if self.debug == 1: print('units are already in the metric system: no action')
 
        
        
    # 3B. convert_units_metric_imperial
    def convert_units_metric_imperial(self):
        
        # Convert wind speeds
        # from  m/s     - we account for conversion here
        # from  knots   - typically 1-minute averaged 
        
        if (self.unit_intensity == 'ms') and (self.unit_radii == 'km'):
        
            # Intensity first
            self.track.vmax     = self.track.vmax / knots_to_ms / self.wind_conversion_factor
              
            # Convert radius of maximum winds
            self.track.RMW      = self.track.RMW / nm_to_km
    
            # Convert wind radii
            for it in range(len(self.track)):
                
                # R35
                if self.track.R35_NE[it] > 0:
                    self.track.R35_NE[it]  = self.track.R35_NE[it]/ nm_to_km
                else:
                    self.track.R35_NE[it]  = -999
            
                if self.track.R35_SE[it] > 0:
                    self.track.R35_SE[it]  = self.track.R35_SE[it]/ nm_to_km
                else:
                    self.track.R35_SE[it]  = -999
            
                if self.track.R35_SW[it] > 0:
                    self.track.R35_SW[it]  = self.track.R35_SW[it]/ nm_to_km
                else:
                    self.track.R35_SW[it]  = -999
            
                if self.track.R35_NW[it] > 0:
                    self.track.R35_NW[it]  = self.track.R35_NW[it]/ nm_to_km
                else:
                    self.track.R35_NW[it]  = -999
                    
                # R50
                if self.track.R50_NE[it] > 0:
                    self.track.R50_NE[it]  = self.track.R50_NE[it]/ nm_to_km
                else:
                    self.track.R50_NE[it]  = -999
            
                if self.track.R50_SE[it] > 0:
                    self.track.R50_SE[it]  = self.track.R50_SE[it]/ nm_to_km
                else:
                    self.track.R50_SE[it]  = -999
            
                if self.track.R50_SW[it] > 0:
                    self.track.R50_SW[it]  = self.track.R50_SW[it]/ nm_to_km
                else:
                    self.track.R50_SW[it]  = -999
            
                if self.track.R50_NW[it] > 0:
                    self.track.R50_NW[it]  = self.track.R50_NW[it]/ nm_to_km
                else:
                    self.track.R50_NW[it]  = -999
            
                # R65
                if self.track.R65_NE[it] > 0:
                    self.track.R65_NE[it]  = self.track.R65_NE[it]/ nm_to_km
                else:
                    self.track.R65_NE[it]  = -999
            
                if self.track.R65_SE[it] > 0:
                    self.track.R65_SE[it]  = self.track.R65_SE[it]/ nm_to_km
                else:
                    self.track.R65_SE[it]  = -999
            
                if self.track.R65_SW[it] > 0:
                    self.track.R65_SW[it]  = self.track.R65_SW[it]/ nm_to_km
                else:
                    self.track.R65_SW[it]  = -999
            
                if self.track.R65_NW[it] > 0:
                    self.track.R65_NW[it]  = self.track.R65_NW[it]/ nm_to_km
                else:
                    self.track.R65_NW[it]  = -999
            
                # R100
                if self.track.R100_NE[it] > 0:
                    self.track.R100_NE[it]  = self.track.R100_NE[it]/ nm_to_km
                else:
                    self.track.R100_NE[it]  = -999
            
                if self.track.R100_SE[it] > 0:
                    self.track.R100_SE[it]  = self.track.R100_SE[it]/ nm_to_km
                else:
                    self.track.R100_SE[it]  = -999
            
                if self.track.R100_SW[it] > 0:
                    self.track.R100_SW[it]  = self.track.R100_SW[it]/ nm_to_km
                else:
                    self.track.R100_SW[it]  = -999
            
                if self.track.R100_NW[it] > 0:
                    self.track.R100_NW[it]  = self.track.R100_NW[it]/ nm_to_km
                else:
                    self.track.R100_NW[it]  = -999
            
            
            # Done, so set variable 
            self.unit_intensity   = 'knots'             
            self.unit_radii       = 'nm'       
            if self.debug == 1: print('convert units to imperial system')
            
        else:
            if self.debug == 1: print('units are already in the imperial system: no action')
        
        
    # 4. account_for_forward_speed
    def account_for_forward_speed(self):
        
        # Assign variables to geopandas dataframe
        nan_list    = [np.nan for _ in range(len(self.track))]
        self.track  = self.track.assign(vtx=nan_list)
        self.track  = self.track.assign(vty=nan_list)
        self.track  = self.track.assign(dpcdt=nan_list)
        self.track  = self.track.assign(vmax_rel=nan_list)
        
        # Same for 4 quadrants and 4 radii
        nan_array = [np.full((4,4), np.nan) for i in range(len(self.track))]
        self.track  = self.track.assign(quadrants_radii=nan_array)
        
        speeds      = np.array([[35, 35, 35, 35], [50, 50, 50, 50], [65, 65, 65, 65], [100, 100, 100, 100]])*knots_to_ms
        speed_array = [speeds for i in range(len(self.track))]
        self.track  = self.track.assign(quadrants_speed=speed_array)

        # Go over time steps
        for it in range(len(self.track)):
        
            # Get basics
            datetime_it     = datetime.strptime(self.track.datetime[it], dateformat_module)
            coords_it       = self.track.geometry[it]            
            geofacx         = 1
            geofacy         = 1
            
            # Determine geo factors (currently only geo support)
            if self.track.crs.name == 'WGS 84':
                geofacy = 111111
                geofacx = geofacy * np.cos(coords_it.y * np.pi/180)
        
            if it == 0:
                
                # Forward 
                datetime_forward    = datetime.strptime(self.track.datetime[it+1], dateformat_module)
                coords_forward      = self.track.geometry[it+1] 
                dt                  = datetime_forward - datetime_it
                dt                  = dt.total_seconds()
                dx                  = (coords_forward.x - coords_it.x) * geofacx
                dy                  = (coords_forward.y - coords_it.y) * geofacy
                dpc                 = self.track.pc[it+1] - self.track.pc[it] 
                
            elif it == len(self.track)-1:
                
                # Backward 
                datetime_backward   = datetime.strptime(self.track.datetime[it-1], dateformat_module)
                coords_backward     = self.track.geometry[it-1] 
                dt                  = datetime_it - datetime_backward
                dt                  = dt.total_seconds()
                dx                  = (coords_it.x - coords_backward.x) * geofacx
                dy                  = (coords_it.y - coords_backward.y) * geofacy
                dpc                 = self.track.pc[it] - self.track.pc[it-1] 
                
            else: 
    
                # Forward           
                datetime_forward    = datetime.strptime(self.track.datetime[it+1], dateformat_module)
                coords_forward      = self.track.geometry[it+1] 
                dt1                 = datetime_forward - datetime_it
                dt1                 = dt1.total_seconds()
                dx1                 = (coords_forward.x - coords_it.x) * geofacx
                dy1                 = (coords_forward.y - coords_it.y) * geofacy
                dpc1                = self.track.pc[it+1] - self.track.pc[it] 
                
                # Backward 
                datetime_backward   = datetime.strptime(self.track.datetime[it-1], dateformat_module)
                coords_backward     = self.track.geometry[it-1] 
                dt2                 = datetime_it - datetime_backward
                dt2                 = dt2.total_seconds()
                dx2                 = (coords_it.x - coords_backward.x) * geofacx
                dy2                 = (coords_it.y - coords_backward.y) * geofacy
                dpc2                = self.track.pc[it] - self.track.pc[it-1] 
                
                # Combined yields central differences
                dx                  = np.mean([dx1, dx2])
                dy                  = np.mean([dy1, dy2])
                dt                  = np.mean([dt1, dt2])
                dpc                 = np.mean([dpc1, dpc2])
                
                
            # Compute variables
            ux      = dx / dt               # speed in meter per seconds
            uy      = dy / dt   
            dpcdt   = dpc/ (dt   / 3600)    # pressure change per hour 
    
    
            # Check to limit dpc which happens when pc is not know
            if dpcdt > 100 or dpcdt < -100:
                dpcdt = 0
                if self.debug == 1: print(' limited dpcdt to zero for it', it)

            # Check if all is OK
            if ux == 0 and uy == 0:
                if self.debug == 1: print('ux or uy became 0, timestep it+1 and it-1 have exactly the same coordinate for it = ', it)
            
            
            # Estimate asymmetry
            if self.asymmetry_option == 'schwerdt1979':
                uabs    = np.sqrt(ux**2 + uy**2)    # forward speed using x and y components
                c       = uabs/knots_to_ms          # convert back to kts
                a       = 1.5*c**0.63               # Schwerdt (1979)
                a       = a*knots_to_ms             # Convert to m/s
                u_prop  = a*ux/uabs               
                v_prop  = a*uy/uabs
            elif self.asymmetry_option == 'mvo':
                uabs    = np.sqrt(ux**2 + uy**2)    # forward speed using x and y components
                c2      = 0.6
                u_prop  = a*ux/uabs               
                v_prop  = a*uy/uabs
            elif self.asymmetry_option == 'none':
                u_prop  = 0.0             
                v_prop  = 0.0
            else:
                raise Exception('This asymmetry_option is not supported')
            
            # Compute relative vmax
            vmax_rel= self.track.vmax[it] - np.sqrt(u_prop**2 + v_prop**2)
        
            # Save as part of the track
            self.track.vtx[it]          = ux            # forward speed in x
            self.track.vty[it]          = uy            # forward speed in y
            self.track.dpcdt[it]        = dpcdt         # pressure difference in time
            self.track.vmax_rel[it]     = vmax_rel      # vmax corrected for asymmetry
            
        
            # Place wind radii in special structure  (only if wind is high enough)
            if self.track.vmax[it] > 15:
                
                # Note  first dimension area different radii (R35, R50, etc)        - irad
                #       second dimension are the quadrants                          - iquad
                # Set values for R35
                if self.track.R35_NE[it] > 0:
                    self.track.quadrants_radii[it][0,0] = self.track.R35_NE[it]
                if self.track.R35_SE[it] > 0:
                    self.track.quadrants_radii[it][0,1] = self.track.R35_SE[it]
                if self.track.R35_SW[it] > 0:
                    self.track.quadrants_radii[it][0,2] = self.track.R35_SW[it]
                if self.track.R35_NW[it] > 0:
                    self.track.quadrants_radii[it][0,3] = self.track.R35_NW[it]
            
                # Set values R50
                if self.track.R50_NE[it] > 0:
                    self.track.quadrants_radii[it][1,0] = self.track.R50_NE[it]
                if self.track.R50_SE[it] > 0:
                    self.track.quadrants_radii[it][1,1] = self.track.R50_SE[it]
                if self.track.R50_SW[it] > 0:
                    self.track.quadrants_radii[it][1,2] = self.track.R50_SW[it]
                if self.track.R50_NW[it] > 0:
                    self.track.quadrants_radii[it][1,3] = self.track.R50_NW[it]
            
                # Set values R65
                if self.track.R65_NE[it] > 0:
                    self.track.quadrants_radii[it][2,0] = self.track.R65_NE[it]
                if self.track.R65_SE[it] > 0:
                    self.track.quadrants_radii[it][2,1] = self.track.R65_SE[it]
                if self.track.R65_SW[it] > 0:
                    self.track.quadrants_radii[it][2,2] = self.track.R65_SW[it]
                if self.track.R65_NW[it] > 0:
                    self.track.quadrants_radii[it][2,3] = self.track.R65_NW[it]
            
                # Set values R100
                if self.track.R100_NE[it] > 0:
                    self.track.quadrants_radii[it][3,0] = self.track.R100_NE[it]
                if self.track.R100_SE[it] > 0:
                    self.track.quadrants_radii[it][3,1] = self.track.R100_SE[it]
                if self.track.R100_SW[it] > 0:
                    self.track.quadrants_radii[it][3,2] = self.track.R100_SW[it]
                if self.track.R100_NW[it] > 0:
                    self.track.quadrants_radii[it][3,3] = self.track.R100_NW[it]

                
                # First find directions of maximum wind speed in each quadrant
                angles0b    = {}
                anglesb     = {}
                for ii in range(0, 4):
                    angles0b[ii] = []
                    anglesb[ii] = []
                angles0b[0] = np.arange(90, 180+10, 10)     # ne
                angles0b[1] = np.arange(0, 90+10, 10)       # se
                angles0b[2] = np.arange(270, 360+10, 10)    # sw
                angles0b[3] = np.arange(180, 270+10, 10)    # nw
                for iquad in range(0, 4):
                    if coords_it.y > 0:
                        anglesb[iquad] = angles0b[iquad] + self.phi_spiral        # include spiralling effect
                    else:
                        anglesb[iquad] = angles0b[iquad] - self.phi_spiral        # include spiralling effect
                        
                    anglesb[iquad] = anglesb[iquad] * np.pi / 180                 # convert to radians
                
                
                # Go over quadrants: find angle with maximum winds flowing
                angles = np.zeros((len(anglesb)))
                for iquad in range(0,4):
                    
                    # Get ready
                    uabs            = np.zeros((len(anglesb[iquad])))
                    vabs            = np.zeros((len(anglesb[iquad])))
                    abs_speed       = np.zeros((len(anglesb[iquad])))
                    counter         = 0
                    
                    # Go over angles
                    for ii in anglesb[iquad]:
                        uabs[counter]       = (35*knots_to_ms) * np.cos(ii)
                        vabs[counter]       = (35*knots_to_ms) * np.sin(ii)
                        uabs[counter]       = uabs[counter] + u_prop
                        vabs[counter]       = vabs[counter] + v_prop
                        abs_speed[counter]  = (np.sqrt(np.dot(uabs[counter], uabs[counter]) + np.dot(vabs[counter], vabs[counter])))
                        counter             = counter + 1
                        
                    imax            = np.where(abs_speed == np.max(abs_speed))
                    if imax[0].size > 1:
                        imax = 0
                        
                    angles[iquad]   = angles0b[iquad][imax] * np.pi / 180
                
                
                # Compute relative speed of all quadrants and radii
                for irad in range(np.size(self.track.quadrants_speed[it],0)):
                    for iquad in range(np.size(self.track.quadrants_speed[it],1)):
                        uabs = self.track.quadrants_speed[it][irad,iquad] * np.cos(angles[iquad])
                        vabs = self.track.quadrants_speed[it][irad,iquad] * np.sin(angles[iquad])
                        urel = uabs - u_prop
                        vrel = vabs - v_prop
                        self.track.quadrants_speed[it][irad,iquad] = np.sqrt(urel**2  + vrel**2)

        # Done with the time steps
        if self.debug == 1: print('done with accounting for forward speed')



    # Create and write-out spiderweb  
    def to_spiderweb(self, filename):
        
        # 1. convert units to km and m/s
        self.convert_units_imperial_metric()
        
        # 2. estimate missing values
        self.account_for_forward_speed()
        self.estimate_missing_values()
        
        # 3. cut off track points with low wind speeds at beginning and end of track + extent track
        self.cut_off_low_wind_speeds()
        self.extent_track()

        # 4. account for forward speed (computes several derivate values)
        self.account_for_forward_speed()
        
        # 5. Define grid and output
        spiderweb       = []
        dx              = self.spiderweb_radius / self.nr_radial_bins
        r               = np.arange(dx, self.spiderweb_radius+dx, dx)
        dphi            = 360 /self.nr_directional_bins
        phi             = np.arange(90, -270, -dphi)

        # 6. Go over time steps in the track
        for it in range(len(self.track)):
            
            # Get values ready
            dp      = self.background_pressure - self.track.pc[it]
            vmax    = self.track.vmax[it]
            pc      = self.track.pc[it]
            rmax    = self.track.RMW[it]
            pn      = self.background_pressure
            rhoa    = self.rho_air
            xn      = 0.5
            coords  = self.track.geometry[it]            
            lat     = coords.y

            # Get derivate values
            ux      = self.track.vtx[it]                                                            # forward speed - x 
            uy      = self.track.vty[it]                                                            # forward speed - y  
            vt      = np.sqrt(self.track.vtx[it]**2  + self.track.vty[it]**2)                       # forward speed - magnitude
            phit    = np.arctan2(self.track.vty[it],self.track.vtx[it]) * 180 / np.pi               # angle
            dpcdt   = self.track.dpcdt[it]                                                          # pressure gradient in time
            vmax_rel= self.track.vmax_rel[it]                                                       # intensity corrected for forward motion

            # initialize arrays
            wind_speed              = np.zeros((len(phi), len(r)))
            wind_to_direction_cart  = np.zeros((len(phi), len(r)))
            pressure_drop           = np.zeros((len(phi), len(r)))
            rainfall_rate           = np.zeros((len(phi), len(r)))
            spiderweb_dict          = {'wind_speed': wind_speed, 'wind_from_direction': wind_speed, 'pressure_drop': wind_speed, 'pressure_drop': wind_speed, 'rainfall': rainfall_rate}

            # Holland et al. 2010
            if self.wind_profile == 'holland2010':
                # either directionally uniform, or using r35, r50, r65, r100
                
                unidir = 0
                n      = 0
                if vmax > 20:
                    for iq in range(np.size(self.track.quadrants_speed[it],0)):
                        for irad in range(np.size(self.track.quadrants_speed[it],1)):
                            if not np.isnan(self.track.quadrants_radii[it][iq,irad]):
                                n = n + 1
                if n == 0:
                    unidir = 1
                
                
                # Do fitting of Holland 2010 xn
                if not unidir:
                    obs                         = {}
                    obs['quadrants_radii']      = self.track.quadrants_radii[it]
                    obs['quadrants_speed']      = self.track.quadrants_speed[it]
                    wrad                        = np.array([35, 50, 65, 100])*knots_to_ms
                    [xn, vtcor, phia]           = fit_wind_field_holland2010(vmax, rmax, pc, vt, phit, pn, self.phi_spiral, lat, dpcdt, obs, wrad)
                    ux                          = vtcor * np.cos((phit + phia) * np.pi / 180)
                    uy                          = vtcor * np.sin((phit + phia) * np.pi / 180)
                    vmax_rel                    = vmax - vtcor
                    # print(xn)
            
                # Finally, fit profile
                [vr, pr]    = holland2010(r, vmax_rel, pc, pn, rmax, dpcdt, lat, vt, xn)

            
            # Assume constant xn that follows a relationship decribed in 2008 paper
            elif self.wind_profile == 'holland2008':
               xn          = 0.6 * (1 - dp / 215)
               [vr, pr]    = holland2010(r, vmax_rel, pc, pn, rmax, dpcdt, lat, vt, xn)

            # Orginal Holland uses a constant xn of 0.5
            elif self.wind_profile == 'holland1980':
                xn          = 0.5
                [vr, pr]    = holland2010(r, vmax_rel, pc, pn, rmax, dpcdt, lat, vt, xn)
                
            else:
                raise Exception('This wind_profile is not supported')

                
            # Compute pressure drop    
            pd          = pn - pr  
            
            # Go over the different phi
            for iphi in range(len(phi)):
            
                # Place wind speed    
                wind_speed[iphi,:] = vr
                
                # Check which hemisphere we are
                if lat >= 0:
                    # northern hemisphere
                    dr  = 90 + phi[iphi]  + self.phi_spiral
                else:
                    # southern hemisphere
                    dr  = -90 + phi[iphi] - self.phi_spiral

                # Wind direction and pressure drop
                wind_to_direction_cart[iphi,:]    = dr
                pressure_drop[iphi,:]             = pd * 100 # convert from hPa to Pa
            
            
            # Add asymmetry
            if self.asymmetry_option == 'schwerdt1979':
                uabs    = np.sqrt(ux**2 + uy**2)    # forward speed using x and y components
                c       = uabs/knots_to_ms          # convert back to kts
                a       = 1.5*c**0.63               # Schwerdt (1979)
                a       = a*knots_to_ms             # Convert to m/s
                u_prop  = a*ux/uabs               
                v_prop  = a*uy/uabs
            elif self.asymmetry_option == 'mvo':
                uabs    = np.sqrt(ux**2 + uy**2)    # forward speed using x and y components
                c2      = 0.6
                u_prop  = a*ux/uabs               
                v_prop  = a*uy/uabs
            elif self.asymmetry_option == 'none':
                u_prop  = 0.0             
                v_prop  = 0.0
            else:
                raise Exception('This asymmetry_option is not supported')
                
            # wind speed with assymetry     
            vx = wind_speed * np.cos(wind_to_direction_cart * np.pi / 180) + u_prop
            vy = wind_speed * np.sin(wind_to_direction_cart * np.pi / 180) + v_prop

            # Save all values
            dr                  = 1.5*np.pi - np.arctan2(vy,vx)
            wind_speed          = np.sqrt(vx**2 + vy**2)
            wind_from_direction = 180 * dr/np.pi
            wind_from_direction = np.remainder(wind_from_direction, 360)

            # Add rainfall (if we want)
            if self.include_rainfall == True:

                # Add rainfall
                if self.rainfall_relationship == 'ipet':

                    # IPET is a simple rainfall model relating pressure to rainfall rate
                    pdef = pressure_drop[0,0]/100            # % Pa to hPa
                    for ip in range(len(r)):
                        if r[ip] < rmax:
                            rainfall_rate[:,ip] = 1.14 + (0.12*pdef)
                        else:
                            rainfall_rate[:,ip] = (1.14 + (0.12*pdef)) * np.exp(-0.3*((r[ip]-rmax)/rmax))
                
                # More options to be added later
                # Bader, Bacla, etc.

            # Save into a dictonary for spiderweb
            spiderweb_dict['wind_speed']           = wind_speed
            spiderweb_dict['wind_from_direction']  = wind_from_direction
            spiderweb_dict['pressure']             = pn - pressure_drop/100     # pa - hPa
            spiderweb_dict['pressure_drop']        = pressure_drop
            spiderweb_dict['rainfall_rate']        = rainfall_rate * self.rainfall_factor       # multiply with a constant factor

            # Add spiderweb_dict to list of spiderweb
            spiderweb.append(spiderweb_dict)
            

        # Actual writing (spiderweb in ascii)
        self.write_spiderweb_ascii(spiderweb, filename)

        # clean-up the geopandas: remove numpy arrays
        self.track.pop('quadrants_radii')
        self.track.pop('quadrants_speed')
        
        # End
        # we are now done


    # Write spiderweb functions
    def write_spiderweb_ascii(self, spiderweb, filename):
        
        # Header information
        vsn             = '1.03'
        merge_frac      = []
        gridunit        = 'degree'
        
        # The rows and columns need to be switched for python
        ncols, nrows    = np.shape(spiderweb[0]['wind_speed'])
    
        # Create output
        fid             = open(filename, 'w')
        format1         = '{:<14} {:1} {:<} {:>} \n'
        format2         = '{:<14} {:1} {:<} \n'
    
        # Write header information
        fid.write(format1.format('FileVersion', '=', vsn, '                            # Version of meteo input file, to check if the newest file format is used'))
        fid.write(format2.format('filetype', '=', 'meteo_on_spiderweb_grid          # from TRACK file: trackfile.trk'))
        fid.write(format2.format('NODATA_value', '=', '-999.000'))
        fid.write(format1.format('n_cols', '=', str(ncols), '                   # Number of columns used for wind datafield'))
        fid.write(format1.format('n_rows', '=', str(nrows), '                           # Number of rows used for wind datafield'))
        fid.write(format2.format('grid_unit', '=', gridunit))
        fid.write(format2.format('spw_radius', '=', str(self.spiderweb_radius*1000)))                   
        fid.write(format2.format('spw_rad_unit', '=', 'm'))
        if merge_frac:
            fid.write(format2.format('spw_merge_frac', '=', str(merge_frac)))   
        if self.include_rainfall == True:     
            fid.write(format2.format('n_quantity', '=', '4'))
        else:
            fid.write(format2.format('n_quantity', '=', '3'))
        fid.write(format2.format('quantity1', '=', 'wind_speed'))
        fid.write(format2.format('quantity2', '=', 'wind_from_direction'))
        fid.write(format2.format('quantity3', '=', 'p_drop'))
        if self.include_rainfall == True: 
            fid.write(format2.format('quantity4', '=', 'precipitation'))
        fid.write(format2.format('unit1', '=', 'm s-1'))
        fid.write(format2.format('unit2', '=', 'degree'))
        fid.write(format2.format('unit3', '=', 'Pa'))
        if self.include_rainfall == True: 
            fid.write(format2.format('unit4', '=', 'mm/h'))

        # Go over the time steps            
        for it in range(len(spiderweb)):
            
            # Get time
            datetime_it         = datetime.strptime(self.track.datetime[it], dateformat_module)
            dt                  = datetime_it - self.reference_time
            dt                  = dt.total_seconds() / 60             # 60 seconds per hour
            
            # Get main variables
            wind_speed          = spiderweb[it]['wind_speed'].transpose()
            wind_from_direction = spiderweb[it]['wind_from_direction'].transpose()
            pressure_drop       = spiderweb[it]['pressure_drop'].transpose()
            rainfall_rate       = spiderweb[it]['rainfall_rate'].transpose()

            # Replace NaN with -999
            wind_speed          = np.nan_to_num(wind_speed, nan=-999)
            wind_from_direction = np.nan_to_num(wind_from_direction, nan=-999)
            pressure_drop       = np.nan_to_num(pressure_drop, nan=-999)
            rainfall_rate       = np.nan_to_num(rainfall_rate, nan=-999)

            # Get coordinates
            coords              = self.track.geometry[it]            
            
            # Print 
            reference_time_str  = self.reference_time.strftime("%Y-%m-%d %H:%M:%S")
            fid.write('{:<14} {:1} {:^10.2f} {:} {:} {:<6}'.format('TIME', '=', int(dt), 'minutes since', reference_time_str, '+00:00'))
            fid.write('\n')
            fid.write(format2.format('x_spw_eye', '=', (round(coords.x,2))))
            fid.write(format2.format('y_spw_eye', '=', (round(coords.y,2))))
            fid.write(format2.format('p_drop_spw_eye', '=', (round(np.amax(pressure_drop),2))))
                                                 
            # Save main variables
            np.savetxt(fid, wind_speed, fmt='%9.2f')
            np.savetxt(fid, wind_from_direction, fmt='%9.2f')
            np.savetxt(fid, pressure_drop, fmt='%9.2f')
            if self.include_rainfall == True: 
                np.savetxt(fid, rainfall_rate, fmt='%9.2f')
         
        # We are done here    
        fid.close()
        if self.debug == 1: print('Succesfully written spiderweb to ' + filename)



# Classes of classes       
class TropicalCycloneEnsemble:
    
    # Init
    def __init__(self,name=None,TropicalCyclone=None):
        
        # Main variables
        self.name                       = name                      # we give the TropicalCycloneEnsemble always a name
        self.number_of_realizations     = []                        # number of realisations
        self.dt                         = 3                         # 3 hours
        self.debug                      = 0                         # do not show prints
        self.include_best_track         = 0                         # ensemble member = 0 is actually the best track

        # Error statistics - based on NHC of 2018-2021
        self.mean_abs_cte24             = 19.0397*nm_to_m           # mean absolute error in cross-track error (CTE)
        self.sc_cte                     = 1.3253                    # auto-regression CTE
        self.mean_abs_ate24             = 26.224*nm_to_m            # mean absolute error in along-track error (ATE)
        self.sc_ate                     = 1.3432                    # auto-regression ATE
        self.mean_abs_ve24              = 6.9858                    # mean absolute error in wind error (VE)
        self.sc_ve                      = 1.0000                    # auto-regression VE = 1 = no auto-regression
        
        # Define best-track
        self.best_track                 = TropicalCyclone
        self.tstart                     = datetime.strptime(self.best_track.track.datetime[0], dateformat_module)   # starting time of the track
        self.tstart_ensemble            = datetime.strptime(self.best_track.track.datetime[0], dateformat_module)   # starting time of variability
        self.tend                       = datetime.strptime(self.best_track.track.datetime[len(self.best_track.track)-1], dateformat_module)
        
        # The actual ensemble members
        self.members                    = []


    # Compute ensemble member
    def compute_ensemble(self, number_of_realizations=None):
        
        # First set time variables based on best track
        if self.debug == 1: print('Started with making ensembles')
        self.number_of_realizations     = number_of_realizations

        # Go over ensemble time steps
        ensemble_time   = []
        current_time    = self.tstart                   # set the current time to the start time
        delta           = timedelta(hours=self.dt)      # create a timedelta object representing a 1 hour time difference
        while current_time <= self.tend:  # loop until we reach the end time
            ensemble_time.append(current_time)  # add the current time to the list
            current_time += delta  # increment the current time by the time difference
        ntpred                          = len(ensemble_time)
        
        # Go over time steps
        best_track_time                 = []
        best_track_lon                  = []
        best_track_lat                  = []
        best_track_vmax                 = []
        for it in range(len(self.best_track.track)):
            coords_it       = self.best_track.track.geometry[it]   
            best_track_lon.append(coords_it.x)
            best_track_lat.append(coords_it.y)
            best_track_vmax.append(self.best_track.track.vmax[it] )
            best_track_time.append(datetime.strptime(self.best_track.track.datetime[it], dateformat_module))

        # Spline to requested times 
        best_track_time2                = [date.timestamp() for date in best_track_time]
        ensemble_time2                  = [date.timestamp() for date in ensemble_time]

        best_track_lon2                 = CubicSpline(best_track_time2,best_track_lon)
        best_track_lon2                 = best_track_lon2(ensemble_time2)
        best_track_lat2                 = CubicSpline(best_track_time2,best_track_lat)
        best_track_lat2                 = best_track_lat2(ensemble_time2)
        best_track_vmax2                = CubicSpline(best_track_time2,best_track_vmax)
        best_track_vmax2                = best_track_vmax2(ensemble_time2)

        # Compute heading again
        [forward_speed, heading]        = compute_forward_speed_heading(ensemble_time2,best_track_lon2, best_track_lat2)

        # Second, define all members with their first time step the same
        self.members                     = []
        for nn in range(self.number_of_realizations+1):
            
            # Add best track
            new_member          = TropicalCyclone(name='ensemble' + str(nn).zfill(5))

            # Use settings from BTD
            new_member.wind_profile               = self.best_track.wind_profile
            new_member.wind_pressure_relation     = self.best_track.wind_pressure_relation
            new_member.rmw_relation               = self.best_track.rmw_relation    
            new_member.background_pressure        = self.best_track.background_pressure
            new_member.phi_spiral                 = self.best_track.phi_spiral
            new_member.wind_conversion_factor     = self.best_track.wind_conversion_factor
            new_member.spiderweb_radius           = self.best_track.spiderweb_radius
            new_member.nr_radial_bins             = self.best_track.nr_radial_bins
            new_member.nr_directional_bins        = self.best_track.nr_directional_bins
            new_member.debug                      = self.best_track.debug
            new_member.low_wind_speeds_cut_off    = self.best_track.low_wind_speeds_cut_off
            new_member.rho_air                    = self.best_track.rho_air
            new_member.asymmetry_option           = self.best_track.asymmetry_option
            new_member.reference_time             = self.best_track.reference_time
            new_member.include_rainfall           = self.best_track.include_rainfall
            new_member.rainfall_relationship      = self.best_track.rainfall_relationship
            new_member.unit_intensity             = self.best_track.unit_intensity
            new_member.unit_radii                 = self.best_track.unit_radii
            new_member.EPSG                       = self.best_track.EPSG

            # Replace track 
            point               = Point(best_track_lon2[0],best_track_lat2[0])
            gdf                 = gpd.GeoDataFrame({"datetime": [ensemble_time[0].strftime(dateformat_module)],"geometry": [point], "vmax": [best_track_vmax2[0]], "pc": [-999], "RMW": [-999],
                                        "R35_NE":  [-999],  "R35_SE":  [-999], "R35_SW":  [-999],  "R35_NW": [-999],
                                        "R50_NE":  [-999],  "R50_SE":  [-999], "R50_SW":  [-999],  "R50_NW": [-999],
                                        "R65_NE":  [-999],  "R65_SE":  [-999], "R65_SW":  [-999],  "R65_NW": [-999],
                                        "R100_NE": [-999], "R100_SE": [-999],"R100_SW": [-999], "R100_NW": [-999]})    
            gdf.set_crs(epsg=new_member.EPSG, inplace=True)
            new_member.track    = pd.concat([new_member.track,gdf]) 
            new_member.track    = new_member.track.reset_index(drop=True)
            new_member.track    = new_member.track.drop([0])           # remove the dummy
            new_member.track    = new_member.track.reset_index(drop=True)

            # Append
            self.members.append(new_member)

        # Third, make variations - go over time
        # not we are making number_of_realizations+1 since the first [0] will be the best-track
        dt_seconds          = ensemble_time2[1] - ensemble_time2[0]
        dtd                 = dt_seconds/86400
        ate_12              = np.zeros((1, self.number_of_realizations+1))
        cte_12              = np.zeros((1, self.number_of_realizations+1))
        ve_12               = np.zeros((1, self.number_of_realizations+1))

        # Random error matrices from normal distribution  .
        arnd0               = np.random.randn(ntpred,self.number_of_realizations+1) 
        crnd0               = np.random.randn(ntpred, self.number_of_realizations+1)    
        vrnd0               = np.random.randn(ntpred,self.number_of_realizations+1) 

        # Rest
        ate                 = np.zeros((ntpred, self.number_of_realizations+1))
        cte                 = np.zeros((ntpred, self.number_of_realizations+1))
        ve                  = np.zeros((ntpred, self.number_of_realizations+1))
        ensemble_lon        = np.zeros((ntpred, self.number_of_realizations+1))
        ensemble_lat        = np.zeros((ntpred, self.number_of_realizations+1))
        ensemble_vmax       = np.zeros((ntpred, self.number_of_realizations+1))

        # Loop over time
        for it in range(0,len(ensemble_time2)):

            # If we want the variability
            if (ensemble_time[it] > self.tstart_ensemble):
                
                # Correct for time   
                tfac                = np.sqrt(dtd)
                
                # go from mean absolute error to standard deviation
                sigma_ate           = self.mean_abs_ate24/np.sqrt(2/np.pi)
                sigma_cte           = self.mean_abs_cte24/np.sqrt(2/np.pi)
                sigma_ve            = self.mean_abs_ve24/np.sqrt(2/np.pi)

                # standard deviation scales with tfac
                arnd                = tfac*sigma_ate*arnd0[it,:]
                crnd                = tfac*sigma_cte*crnd0[it,:]
                vrnd                = tfac*sigma_ve*vrnd0[it,:]
                
                # Limit to -2 and +2 sigma
                arnd                = np.maximum(np.minimum(arnd, 2*tfac*sigma_ate), -2*tfac*sigma_ate)
                crnd                = np.maximum(np.minimum(crnd, 2*tfac*sigma_cte), -2*tfac*sigma_cte)
                vrnd                = np.maximum(np.minimum(vrnd, 2*tfac*sigma_ve), -2*tfac*sigma_ve)

                # Compute new track errors
                at1                 = self.sc_ate**dtd
                ate[it,:]           = at1 * ate_12 + arnd
                ct1                 = self.sc_cte**dtd
                cte[it,:]           = ct1 * cte_12 + crnd

                # Compute new positions
                abserr              = np.sqrt(ate[it,:]**2 + cte[it,:]**2)
                phierr              = np.arctan2(-cte[it,:], ate[it,:])
                phitot              = heading[it] + phierr
                ensemble_lon[it,:]  = best_track_lon2[it] + abserr * np.cos(phitot) *np.cos(best_track_lat2[it]*np.pi/180)/111111
                ensemble_lat[it,:]  = best_track_lat2[it] + abserr * np.sin(phitot)/111111

                # Do wind speed too
                ve1                 = self.sc_ve**dtd
                ve[it,:]            = ve1*ve_12 + vrnd
                ensemble_vmax[it,:] = best_track_vmax2[it] + ve[it,:]
                ensemble_vmax[it,:] = np.maximum(ensemble_vmax[it,:], 10.0)      # low of 10 knots (Beaufort = 3)

                # Save errors from last iteration
                ate_12  = ate[it,:]
                cte_12  = cte[it,:]
                ve_12   = ve[it,:]
            
            # Else we don't
            else:

                # And simply place the best-track here
                ensemble_lon[it,:]  = best_track_lon2[it]
                ensemble_lat[it,:]  = best_track_lat2[it] 
                ensemble_vmax[it,:] = best_track_vmax2[it] 

        # Apply spatial smoothing on track data
        factor                              = round(12/(dtd*24))
        if factor > 1:
            for nn in range(self.number_of_realizations):
                
                # Only apply this for the non-best-track-period
                idwanted               = np.zeros(len(ensemble_time),dtype=bool)
                for dt in range(len(ensemble_time)):
                    idwanted[dt]            = ensemble_time[dt] > self.tstart_ensemble

                # Apply this
                ensemble_lon[idwanted,nn]     = uniform_filter1d(ensemble_lon[idwanted,nn], size=factor)
                ensemble_lat[idwanted,nn]     = uniform_filter1d(ensemble_lat[idwanted,nn], size=factor)

        # Replace first one - that is the best-track
        if self.include_best_track == 1:
            ensemble_lon[:,0]   = best_track_lon2
            ensemble_lat[:,0]   = best_track_lat2
            ensemble_vmax[:,0]  = best_track_vmax2

        # Visual check
        if self.debug == 1: 
            plt.plot(ensemble_time2, ensemble_vmax)
            plt.plot(best_track_time2,best_track_vmax, '-k')

            plt.plot(ensemble_lon, ensemble_lat)
            plt.plot(best_track_lon2,best_track_lat2, '-k')

        # Place them in their geopandas track
        for nn, member in enumerate(self.members):

            # Add time stamps
            for it in range(1,len(ensemble_time2)):
                        
                # Make GeoDataFrame of this timestamp and track
                point       = Point(ensemble_lon[it,nn],ensemble_lat[it,nn])
                gdf         = gpd.GeoDataFrame({"datetime": [ensemble_time[it].strftime(dateformat_module)],"geometry": [point], "vmax": [ensemble_vmax[it,nn]], "pc": [-999], "RMW": [-999],
                                            "R35_NE":  [-999],  "R35_SE":  [-999], "R35_SW":  [-999],  "R35_NW": [-999],
                                            "R50_NE":  [-999],  "R50_SE":  [-999], "R50_SW":  [-999],  "R50_NW": [-999],
                                            "R65_NE":  [-999],  "R65_SE":  [-999], "R65_SW":  [-999],  "R65_NW": [-999],
                                            "R100_NE": [-999], "R100_SE": [-999],"R100_SW": [-999], "R100_NW": [-999]})    
                gdf.set_crs(epsg=4326, inplace=True)
                self.members[nn].track = pd.concat([self.members[nn].track,gdf]) 
                
            # Done with this ensemble member
            self.members[nn].track        = self.members[nn].track.reset_index(drop=True)
            if self.debug == 1: print(self.members[nn].name)
        
        # Are we done?
        if self.debug == 1: print(' done with making ensemble members')


    # Write out shapefile
    def to_shapefile(self, folder_path):  

        # Make path (if needed)
        os.makedirs(folder_path, exist_ok=True)

        # Get the tracks in line format
        lines = []
        ids   = []
        for nn, member in enumerate(self.members):
            coordinates = []
            for it in range(len(member.track)):
                coordinates.append( (member.track.geometry[it].x, member.track.geometry[it].y) )
            line = LineString(coordinates)
            lines.append(line)
            ids.append(member.name)
        multilinestring = MultiLineString(lines)     

        # Write out as shapefile
        filename = os.path.join(folder_path, 'ensemble_members')
        schema      = {'geometry': 'LineString', 'properties': {'id': 'int'}}
        with fiona.open(filename, 'w', 'ESRI Shapefile', schema) as c:
            counter = 0
            for linestring in multilinestring.geoms:
                # Write the linestring to the shapefile
                c.write({'geometry': mapping(linestring), 'properties': {'id': counter}})
                counter += 1


    # Write them out to a spiderweb
    def to_spiderweb(self, folder_path):  

        # Make path (if needed)
        os.makedirs(folder_path, exist_ok=True)

        # Loop over ensemble members and write them out
        for member in self.members:
            filename = os.path.join(folder_path, member.name)   # combine paths    
            filename = filename + '.spw'                        # add spiderweb extension
            member.to_spiderweb(filename)


    # Make output with cyc
    def to_cyc(self, folder_path):  

        # Make path (if needed)
        os.makedirs(folder_path, exist_ok=True)

        # Loop over ensemble members and write them out
        for member in self.members:
            filename = os.path.join(folder_path, member.name)   # combine paths    
            filename = filename + '.cyc'                        # add cyc extension
            member.write_track(filename, 'ddb_cyc')


    # Make visual of all the tracks 
    def make_figures(self, folder_path):  

        # Make path (if needed)
        os.makedirs(folder_path, exist_ok=True)

        # Get times
        datetime_ensemble = []
        for it in range(len(self.members[0].track)):
            datetime_ensemble.append(datetime.strptime(self.members[0].track.datetime[it], dateformat_module))

        # Show wind speeds
        for nn, member in enumerate(self.members):
            plt.plot(datetime_ensemble,member.track.vmax)
        plt.show()

   
            
######
# Definitions that I want to be available in general
######
# Definitions to compute Holland 2010 (1D)
def holland2010(r, vms, pc, pn, rmax, dpdt, lat, vt, xn):
    """
    Returning the one-dimensional Holland et al. (2010) parametric wind profile
    
    Parameters
    ----------
    r : radius in km
    etc etc.
    
    """
    # calculate Holland b parameter based on Holland (2008) - assume Dvorak method
    dp = max(pn - pc, 1)
    x = 0.6 * (1 - dp/215)
    if np.isnan(dpdt):
        dpdt = 0
    b = -4.4 * 10**-5 * dp**2 + 0.01 * dp + 0.03 * dpdt - 0.014 * abs(lat) + 0.15 * vt**x + 1
    b = min(np.nanmax(np.append(b, 1)), 2) # numerical limits
    
    # initialise
    x   = np.zeros(np.size(r)) + xn
    pr  = np.zeros((np.size(r)))
    vr  = np.zeros((np.size(r)))
    
    # Compute 
    index = r <= rmax
    x[index] = 0.5
    rp = (rmax/r)**b
    pr = pc + dp*np.exp(-rp)
    vr = vms * (rp * np.exp(1.0 - rp))**x
        
    # output
    return [vr, pr]



# Definitiaton for wind radii
def wind_radii_nederhoff(vmax, lat, region, probability):
    """
    Returning the estimates of radius of maximum winds (RMW)
    and estimates of gale force winds (R35)
    
    Parameters
    ----------
    vmax    : wind speed intensity in m/s - 1-minute average
    lat     : latitude in degrees
    region  : see paper for details
    probability: integer - 0 only mode; 1 = 1000 values
    
    Returns
    -------
    rmax    : dictonary with mode and possible more
    r35     : ''
    """
    # radius of maximum winds (rmw or rmax)
    # 1. coefficients for A
    coefficients_a      = np.array([  0.306982540000000,
                            0.338409237000000,
                            0.342791450000000,
                            0.363546490000000,
                            0.358572938000000,
                            0.310729085000000,
                            0.395431764000000,
                            0.370190027000000])
    
    
    # 2. coefficients for B        
    coefficients_b      = np.array([[132.411906200000,	14.5640379700000,	-0.00259703300000000,	20.3808036500000], 
                         [229.245844100000,	9.53865069100000,	0.00398810500000000,	28.4457367200000], 
                         [85.2576655100000,	30.6920872600000,	0.00243248000000000,	5.78116540600000],
                         [127.833300700000,	11.8474757400000,	0.0159363120000000,	    25.4682000500000],
                         [153.733294700000,	11.4788885400000,	0.00747119300000000,	28.9489788700000],
                         [261.528874200000,	7.01151785400000,	0.0261912560000000,	    29.2022787100000],
                         [19.0899242800000,	24.0885573100000,	0.106240340000000,	    23.1802014600000],
                         [44.8241743300000,	23.3717128800000,	0.0304690570000000,	    22.4282036100000],
                         ])


    # 3. get the best guess for a and b given wind speed and latitude
    a_value     = coefficients_a[region]
    b_value     = coefficients_b[region, 0] * np.exp(-vmax / coefficients_b[region, 1]) * (1 + coefficients_b[region, 2] * abs(lat)) + coefficients_b[region, 3]
    
    rmax = {}
    rmax['mode'] = {}
    rmax['mean'] = {}
    rmax['median'] = {}
    rmax['lowest'] = {}
    rmax['highest'] = {}
    rmax['numbers'] = {}
    
    # 4. compute 1000 delta r35 values
    rmax['mode'] = np.exp(np.log(b_value) - a_value**2)
    if probability == 1:
        numbers             = np.sort(np.exp(np.random.normal(size = (1000, 1)) * a_value + np.log(b_value)))
        rmax['mean']        = np.mean(numbers)
        rmax['median']      = np.median(numbers)
        rmax['lowest']      = numbers[int(0.05 * len(numbers))][0]
        rmax['highest']     = numbers[int(0.95 * len(numbers))][0]
        rmax['numbers']     = np.sort(numbers)
            
    # delta radius of 35 knots (r35)
    dr35                = {}
    dr35['mode']        = {}
    dr35['mean']        = {}
    dr35['median']      = {}
    dr35['lowest']      = {}
    dr35['highest']     = {}
    dr35['numbers']     = {}
    
    # Only if wind speed is more than 20 m/s
    if vmax > 20:

        # 1. coefficients for a
        coefficients_a = np.array([[0.121563729, -0.052184289, 0.032953813], 
                                   [0.131188105, -0.044389473, 0.002253258], 
                                   [0.122286754, -0.045355772, 0.013286154], 
                                   [0.120490659, -0.035029431, -0.005249445], 
                                   [0.156059522, -0.041685377, 0.004952978], 
                                   [-0.251333213, -0.009072243, -0.00506365], 
                                   [0.131903526, -0.042096876, 0.012443195], 
                                   [0.190044585, -0.044602083, 0.006117124]])
        
        # 2. coefficients for b
        coefficients_b = np.array([[30.92867473, 0.530681714, -0.012001645], 
                                   [30.21210133, 0.414897465, 0.021689596], 
                                   [26.58686237, 0.425916004, 0.028547278], 
                                   [23.88007085, 0.43109144, 0.038119083], 
                                   [33.26829485, 0.42859578, 0.017209431], 
                                   [18.11013691, 0.486399912, 0.02955688], 
                                   [16.9973011, 0.453713419, 0.054643743], 
                                   [29.61141102, 0.4132484, 0.024418947]])
        
        # 3. get the best guess for a and b given wind speed and latitude
        a_value = coefficients_a[region, 0] + np.exp(vmax * coefficients_a[region, 1]) * (1 + coefficients_a[region, 2] * abs(lat))
        b_value = coefficients_b[region, 0] + (vmax - 18)**coefficients_b[region, 1] * (1 + coefficients_b[region, 2] * abs(lat))

        # 4. compute 1000 delta r35 values
        dr35['mode']    = np.exp(np.log(b_value) - a_value**2)
        if probability == 1:
            numbers             = np.sort(np.exp(np.random.normal(size = (1000, 1)) * a_value + np.log(b_value)))
            dr35['mean']        = np.mean(numbers)
            dr35['median']      = np.median(numbers)
            dr35['lowest']      = numbers[int(0.05 * len(numbers))][0]
            dr35['highest']     = numbers[int(0.95 * len(numbers))][0]
            dr35['numbers']     = np.sort(numbers)
    
            
    # output
    return [rmax, dr35]


# Definition to compute wind-pressure relation to determine the vmax or the pressure drop
def wpr_holland2008(pc = None, pn = None, phi = None, vt = None, dpcdt = None, 
        rhoa = None, SST = None, vmax = None):
                
    # used when pc needs to be determined
    if not rhoa:
        if vmax:
            dp1 = np.arange(1, 151 + 5, 5)
            pc1 = pn - dp1
        else:
            dp1 = pn - pc
            pc1 = pc
        
        if not SST:
            Ts = 28.0 - 3*(phi - 10) / 20 # surface temperature
        else:
            Ts = SST - 1
        
        prmw = pc1 + dp1 / 3.7
        qm = 0.9 * (3.802 / prmw) * np.exp(17.67 * Ts / (243.5 + Ts)) # vapor pressure
        Tvs = (Ts + 273.15) * (1.0 + 0.81 * qm) # virtual surface air temperature
        Rspecific = 287.058
        rhoa = 100 * pc1 / (Rspecific * Tvs)
        
    # vmax to be determined
    if not vmax:
        dp              = pn - pc
        x               = 0.6 * (1 - dp / 215)
        bs              = -4.4e-5 * dp**2 + 0.01 * dp + 0.03 * dpcdt - 0.014 * phi + 0.15 * vt**x + 1.0
        vmax            = np.sqrt(100 * bs * dp / (rhoa * np.e))
        output          = vmax
    else:
        vtkmh           = vt * 3.6
        vmaxkmh         = vmax * 3.6 * 0.88
        dp              = 0.00592 * (1 - 0.0687 * vtkmh**0.33) * (1 + 0.00285 * abs(phi)**1.35) * vmaxkmh**1.81
        output          = pn - dp
        
    return output



# Definition to fit Holland 2010 wind field 
def fit_wind_field_holland2010(vmax, rmax, pc, vtreal, phit, pn, phi_spiral, lat, dpdt, obs, wrad):
    
    # Discussion
    # shouldnt we have a switch to only calibrate vt and phi_a for observed radii
    # what about limits on these variables
    # OK with xn calibration
    
    # function to fit wind field based on Holland 2010    
    size_factor = 1
    phi         = np.arange(90, -270-10, -10) # radial angles (cartesian, degrees)
    rmax        = rmax * 1000 # convert from km to m
    r           = np.arange(4000, 1000000+4000, 4000)
    
    # first estimates
    xn          = 0.5
    vt          = 0.6 * vtreal
    
    if lat > 0:
        phia = 45 # angle with respect to track angle (cartesian degrees, i.e. couter-clockwise)
    else:
        phia = -45
        
    # More variables
    dxn     = 0.01
    dvt     = 0.5
    dphia   = 5
    nrad    = 2
    nobs    = 0
    
    for irad in range(np.size(obs['quadrants_radii'],0)):
        for iquad in range(np.size(obs['quadrants_radii'],1)):
            if not np.isnan(obs['quadrants_radii'][irad,iquad]):
                nobs = nobs+1
                
    # just for plotting
    xx = np.zeros((len(phi), len(r)))
    yy = np.zeros((len(phi), len(r)))
    # plt.pcolor(xx,yy,w)
    
    for j in range(len(phi)):
        for h in range(len(r)):
            xx[j,h] = 0.001 * r[h] * np.cos(phi[j] * np.pi / 180)
            yy[j,h] = 0.001 * r[h] * np.sin(phi[j] * np.pi / 180)
    
    if nobs > 0 and vmax > 21:

        # Do three fits      
        for irep in range(3):
            
            # Default fit
            w = compute_wind_field(r, phi, vmax, pc, rmax, pn, vtreal, phit, lat, dpdt, phi_spiral, xn, vt, phia)
            [mean_error, rms_error, err] = compute_mean_error(r, w, obs, wrad)
            nit = 0
            
            # 1) now first adjust size of storm with xn
            while True:
                nit = nit + 1
                wu = compute_wind_field(r, phi, vmax, pc, rmax, pn, vtreal, phit, lat, dpdt, phi_spiral, xn+dxn, vt, phia)
                [mean_error_u, rms_error_u, err_u] = compute_mean_error(r, wu, obs, wrad)
                wd = compute_wind_field(r, phi, vmax, pc, rmax, pn, vtreal, phit, lat, dpdt, phi_spiral, xn-dxn, vt, phia)
                [mean_error_d, rms_error_d, err_d] = compute_mean_error(r, wd, obs, wrad)
                
                # better with larger value of xn
                if rms_error_u < rms_error:
                    xn = xn + dxn
                    rms_error = rms_error_u
                    
                # better with smaller value of xn    
                elif rms_error_d < rms_error:
                    xn = xn - dxn
                    rms_error = rms_error_d
                
                # optimum reached
                else:
                    break
                
                # Other criteria
                if xn < 0.3 or xn > 1.0:
                    break
                if nit > 100:
                    break
                
            nit = 0
            
            # 2) now the asymmetry magnitude
            while True:
                nit = nit + 1
                wu = compute_wind_field(r, phi, vmax, pc, rmax, pn, vtreal, phit, lat, dpdt, phi_spiral, xn, vt+dvt, phia)
                [mean_error_u, rms_error_u, err_u] = compute_mean_error(r, wu, obs, wrad)
                wd = compute_wind_field(r, phi, vmax, pc, rmax, pn, vtreal, phit, lat, dpdt, phi_spiral, xn, vt-dvt, phia)
                [mean_error_d, rms_error_d, err_d] = compute_mean_error(r, wd, obs, wrad)
                
                # better with larger value of vt
                if rms_error_u < rms_error:
                    vt = vt + dvt
                    rms_error = rms_error_u
                    
                # better with smaller value of vt    
                elif rms_error_d < rms_error:
                    vt = vt - dvt
                    rms_error = rms_error_d
                
                # optimum reached
                else:
                    break
                
                # Other criteria
                if vt < 0.0 or vt > 1.5*vtreal:
                    break
                if nit > 100:
                    break
    
            nit = 0
            
            # 3. now the asymmetry direction
            while True:
                nit = nit + 1
                
                wu = compute_wind_field(r, phi, vmax, pc, rmax, pn, vtreal, phit, lat, dpdt, phi_spiral, xn, vt, phia+dphia)
                [mean_error_u, rms_error_u, err_u] = compute_mean_error(r, wu, obs, wrad)
                wd = compute_wind_field(r, phi, vmax, pc, rmax, pn, vtreal, phit, lat, dpdt, phi_spiral, xn, vt, phia-dphia)
                [mean_error_d, rms_error_d, err_d] = compute_mean_error(r, wd, obs, wrad)
                
                if rms_error_u < rms_error:
                    # better with larger value of phia
                    phia = phia + dphia
                    rms_error = rms_error_u
                    
                elif rms_error_d < rms_error:
                    # better with smaller value of phia
                    phia = phia - dphia
                    rms_error = rms_error_d
                else:
                    # optimum reached
                    break
                
                if phia < -180:
                    phia = phia + 360
                    
                if phia > 180:
                    phia = phia - 360
                
                if nit > 100:
                    break
    
    return [xn, vt, phia]           



# defintiion to compute wind field
def compute_wind_field(r, phi, vmax, pc, rmax, pn, vtreal, phit, lat, dpdt, phi_spiral, xn, vt, phia):
    
    # Discussion
    # is asymmetry account for properly? I believe there should be a factor in front of ux/vy
    vms = vmax - vt
    
    # compute wind profile (vr and pr)
    [vr, pr] = holland2010(r, vms, pc, pn, rmax, dpdt, lat, vtreal, xn)
    
    wind_speed = np.zeros((phi.shape[0],r.shape[0]))
    wind_to_direction_cart = np.zeros((phi.shape[0],r.shape[0]))
    for iphi in range(len(phi)):
        wind_speed[iphi,:] = vr
        if lat >= 0:
            # northern hemisphere
            dr = 90 + phi[iphi] + phi_spiral
        else:
            # southern hemisphere
            dr = -90 + phi[iphi] - phi_spiral
        wind_to_direction_cart[iphi,:] = dr
        
    ux = vt * np.cos((phit + phia) * np.pi / 180)
    uy = vt * np.sin((phit + phia) * np.pi / 180)
    
    vx = wind_speed * np.cos(wind_to_direction_cart * np.pi / 180) + ux
    vy = wind_speed * np.sin(wind_to_direction_cart * np.pi / 180) + uy
    
    wind_speed = np.sqrt(vx**2 + vy**2)
    
    return wind_speed


# Definition to compute mean error
def compute_mean_error(r, w, obs, wrad):
    
    # Discussion
    # why are we only accounting for R35?
    
    # variables
    nrad    = np.size(obs['quadrants_radii'],0)
    nrad    = 1         # not we are only fitting R35, nothing else
    nq      = np.size(obs['quadrants_radii'],1)     
    iq1     = [0, 9, 18, 27]
    iq2     = [9, 18, 27, 36]
    err     = np.zeros((nq, nrad))
    
    # Go over the quadrants and radii
    for irad in range(nrad):
        for iquad in range(nq):
            vrad = 0
            for j in range(iq1[iquad], iq2[iquad] + 1):
                ww = w[j,:]
                if not np.isnan(obs['quadrants_radii'][irad,iquad]):
                    # compute wind speed vrad at required radius
                    wf      = interp1d(r, ww, bounds_error=False, fill_value=0)
                    w0      = wf(obs['quadrants_radii'][irad,iquad]*1000)
                    vrad    = max(vrad, w0)
                else:
                    # maximum wind speed must be lower than wrad
                    w0      = max(ww)
                    vrad    = max(vrad, w0)
            if not np.isnan(obs['quadrants_radii'][irad,iquad]):
                err[iquad, irad] = vrad - wrad[irad]
            else:
                err[iquad, irad] = np.NAN
   
    # Get error values
    mask        = ~np.isnan(err)  # Create the mask
    err         = err[mask]
    mean_error  = np.nanmean(err)
    rms_error   = np.sqrt(np.mean(err**2))
    
    # Return
    return [mean_error, rms_error, err]



# Definition to compute forward speed and heading
def compute_forward_speed_heading(t, x, y):
    
    # variables
    forward_speed = np.zeros((len(x)))
    heading       = np.zeros((len(x)))
    for it in range(len(x)):
    
        # Get basics
        geofacy = 111111
        geofacx = geofacy * np.cos(y[it] * np.pi/180)
    
        if it == 0:
            
            #print('Forward')
            #datetime_forward    = 
            #dt                  = datetime_forward - datetime_it
            #dt                  = dt.total_seconds()
            dx                  = (x[it+1] - x[it]) * geofacx
            dy                  = (y[it+1] - y[it]) * geofacy
            
        elif it == (len(x)-1):
            
            #print('Backward')
            #datetime_backward   = datetime.strptime(self.track.datetime[it-1], dateformat_module)
            #coords_backward     = self.track.geometry[it-1] 
            #dt                  = datetime_it - datetime_backward
            #dt                  = dt.total_seconds()
            dx                  = (x[it] - x[it-1]) * geofacx
            dy                  = (y[it] - y[it-1]) * geofacy
            
        else: 

            # Forward           
            dx1                  = (x[it] - x[it-1]) * geofacx
            dy1                  = (y[it] - y[it-1]) * geofacy
            
            # Backward 
            dx2                  = (x[it+1] - x[it]) * geofacx
            dy2                  = (y[it+1] - y[it]) * geofacy
            
            # Combined yields central differences
            #print('Central')
            dx                  = np.mean([dx1, dx2])
            dy                  = np.mean([dy1, dy2])

        # Compute angle
        forward_speed[it]   = 0.0
        heading[it]         = np.arctan2(dy,dx)
    
        
    # Return
    return [forward_speed, heading]