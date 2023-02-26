# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
import scipy.spatial as ss
import matplotlib.pyplot as plt
import matplotlib
import seaborn as sns
import imageio
import os
import glob
import shutil
import imageio
matplotlib.use('Agg')

sns.set_context("paper")
sns.set_theme(style='whitegrid')

class Dipole_Analyzer():

    polar_scale_factor = -1.60217646*1000
    def __init__(self):
        # self.griddim = griddim
        self.total_polz_list = []
        self.efield_state = []
        self.mag_list = []
        self.synced_frames = []


    
    
    @staticmethod
    def file_handler():
        print('Processing...')
        for directory in ['dipole_analysis', 'dipole_analysis/total_polarization', 'dipole_analysis/local_polarization',
                          'dipole_analysis/local_polarization/XZ_images', 'dipole_analysis/local_polarization/YZ_images']:
            if not os.path.exists(directory):
                os.mkdir(directory)
        shutil.copy('xmolout', 'dipole_analysis/xmolout.txt')
        shutil.copy('fort.7', 'dipole_analysis/fort7.txt')
        shutil.copy('eregime.in', 'dipole_analysis/eregime.txt')
        shutil.copy('control', 'dipole_analysis/control.txt')



    
    def xmol_fort_handler(self):
        with open('dipole_analysis/control.txt', "r") as f:
            ctrl_lines = f.readlines()
        for line in ctrl_lines:
            if 'iout2' in line.split():
                self.save_coords = int(line.split()[0])
            elif 'nmdit' in line.split():
                self.num_iters = int(line.split()[0])
        
        with open('dipole_analysis/xmolout.txt', "r") as f:
            xmol_lines = f.readlines()
        with open('dipole_analysis/fort7.txt', 'r') as f:
            fort_lines = f.readlines()
        
        self.num_atoms = int(xmol_lines[0].strip())
        xmol_line_count = self.num_atoms + 2
        fort_line_count = self.num_atoms + 3
        self.num_frames = int(len(xmol_lines)/xmol_line_count)
        xmol_frames = {}
        new_lines = []
        
        for line in xmol_lines:
            if line.startswith('Zn'):
                line = line.replace('Zn', '2 ')
            elif line.startswith('Mg'):
                line = line.replace('Mg', '3 ')
            elif line.startswith('O'):
                line = line.replace('O', '1')
            new_lines.append(line)
        xmol_lines = new_lines

        for i in range(self.num_frames):
            curr_xmol_frame = xmol_lines[i*xmol_line_count:(i+1)*xmol_line_count]
            curr_fort_frame = fort_lines[i*fort_line_count:(i+1)*fort_line_count]
            del curr_xmol_frame[0]
            del curr_xmol_frame[0]
            del curr_fort_frame[0]
            del curr_fort_frame[-1]
            del curr_fort_frame[-1]
            xmol_frame_data = np.array([line.strip().split() for line in curr_xmol_frame], dtype='float32')
            fort_frame_data = np.array([line.strip().split() for line in curr_fort_frame], dtype='float32')
            curr_frame_charges = fort_frame_data[:,-1]
            xmol_frame_data = np.hstack((xmol_frame_data, curr_frame_charges.reshape(-1,1)))
            xmol_frames[str(i)] = xmol_frame_data
        print('Finished importing xmolout and fort.7!')
        self.xmol_frames = xmol_frames
        self.get_box_dims()


    
        
    def eregime_handler(self):
        with open('dipole_analysis/eregime.txt', 'r') as f:
            eregime_lines = f.readlines()
        eregime_lines = eregime_lines[3:-2]
        for line in eregime_lines:
            self.efield_state.append((int(line.split()[0]), float(line.split()[-1])))   # Tuple: (iteration, efield_magnitude) > based on eregime.in
        self.efield_state.append((self.num_iters, float(line.split()[-1])))             # This is to account for the final iteration which is not printed in eregime.
        self.xmol_fort_timevec = np.arange(0, self.num_iters + self.save_coords, self.save_coords)
        for i in range(len(self.efield_state)-1):
            tstamp1, mag1 = self.efield_state[i]
            tstamp2, mag2 = self.efield_state[i+1]
            frame_index = np.searchsorted(self.xmol_fort_timevec, tstamp2-1, side='right') - 1
            self.synced_frames.append(str(frame_index))
            self.mag_list.append(mag1)
        print('Finished importing eregime.in!')

    


    def get_box_dims(self):
        x_mins, y_mins, z_mins = [], [], []
        x_maxs, y_maxs, z_maxs = [], [], []
        for fram_index, frame in self.xmol_frames.items():
            x_min, x_max = np.min(frame[:,1]), np.max(frame[:,1])
            y_min, y_max = np.min(frame[:,2]), np.max(frame[:,2])
            z_min, z_max = np.min(frame[:,3]), np.max(frame[:,3])
            x_mins.append(x_min)
            x_maxs.append(x_max)
            y_mins.append(y_min)
            y_maxs.append(y_max)
            z_mins.append(z_min)
            z_maxs.append(z_max)
        self.x_lo, self.x_hi = min(x_mins), max(x_maxs)
        self.y_lo, self.y_hi = min(y_mins), max(y_maxs)
        self.z_lo, self.z_hi = min(z_mins), max(z_maxs)




    def get_dipole(self, xmol_frame, origin = np.array([0, 0, 0])):
        pu = 0
        coords = xmol_frame[:,1:-1] - origin
        volume = ss.ConvexHull(coords).volume
        for row in xmol_frame:
            atom_coord = row[1:-1]
            atom_charge = row[-1]
            pu = pu + atom_charge*atom_coord            #Dipole moment vector (Px, Py, Pz)
        polarization = pu[-1]/volume                    #Polarization: P/vol.
        return pu, polarization




    def get_total_dipole(self):
        xmol_frames = self.xmol_fort_handler()
        selected_frames = []
        
        for frame_index in self.synced_frames:
            xmol_frame = self.xmol_frames[frame_index]
            pu, polarization = self.get_dipole(xmol_frame)
            self.total_polz_list.append(polarization)




    def get_intercept(self, pu_zlist, v):
        intercepts = []
        for i,pu_z in enumerate(pu_zlist):
            if i == 0:
                x1 = pu_z
                x2 = pu_z
            else:
                x1 = pu_zlist[i-1]
                x2 = pu_z

            if x1*x2<0:
                v1 = v[i-1]
                v2 = v[i]
                V = np.array([v1, v2])
                x = np.array([x1, x2])
                slope, intercept = np.polyfit(x, V, 1)
                intercepts.append(round(intercept, 1))
        return intercepts
    
        


    def get_mesh(self, points, griddim):
        griddim_x, griddim_y, griddim_z = griddim

        # Find the dimensions of the box:
        self.x_min, self.x_max = self.x_lo-0.1, self.x_hi+0.1
        self.y_min, self.y_max = self.y_lo-0.1, self.y_hi+0.1
        self.z_min, self.z_max = self.z_lo-0.1, self.z_hi+0.1
        gridsize_x = np.round((self.x_max - self.x_min)/griddim_x, 2)
        gridsize_y = np.round((self.y_max - self.y_min)/griddim_y, 2)
        gridsize_z = np.round((self.z_max - self.z_min)/griddim_z, 2)
        
        #Generate XZ and YZ grids:
        x_grid = np.around(np.linspace(self.x_min, self.x_max, griddim_x+1), 2)
        y_grid = np.around(np.linspace(self.y_min, self.y_max, griddim_y+1), 2)
        z_grid = np.around(np.linspace(self.z_min, self.z_max, griddim_z+1), 2)

        # Assign each point to the corresponding XZ grid
        xz_grid_indices = np.zeros((points.shape[0], 2), dtype=int)
        for i, point in enumerate(points):
            xz_grid_indices[i, 0] = np.searchsorted(x_grid, point[1], side='right') - 1
            xz_grid_indices[i, 1] = np.searchsorted(z_grid, point[3], side='right') - 1

        # Assign each point to the corresponding YZ grid
        yz_grid_indices = np.zeros((points.shape[0], 2), dtype=int)
        for i, point in enumerate(points):
            yz_grid_indices[i, 0] = np.searchsorted(y_grid, point[2], side='right') - 1
            yz_grid_indices[i, 1] = np.searchsorted(z_grid, point[3], side='right') - 1

        # Create a dictionary to store the points and grid coordinates
        xz_grid_dict = {}
        for i in range(len(points)):
            grid_num = xz_grid_indices[i, 0] * (len(z_grid)-1) + xz_grid_indices[i, 1]
            grid_center_coordinates = (self.x_min + xz_grid_indices[i, 0]*gridsize_x + round(0.5 * gridsize_x, 2),
                                       self.z_min + xz_grid_indices[i, 1]*gridsize_z + round(0.5 * gridsize_z, 2))
            if grid_num not in xz_grid_dict:
                xz_grid_dict[grid_num] = (np.array([points[i]]), grid_center_coordinates)
            else:
                xz_grid_dict[grid_num] = (np.concatenate((xz_grid_dict[grid_num][0], [points[i]])), xz_grid_dict[grid_num][1])

        # Create a dictionary to store the points and grid coordinates
        yz_grid_dict = {}
        for i in range(len(points)):
            grid_num = yz_grid_indices[i, 0] * (len(z_grid)-1) + yz_grid_indices[i, 1]
            grid_center_coordinates = (self.y_min + yz_grid_indices[i, 0]*gridsize_y + round(0.5 * gridsize_y, 2),
                                       self.z_min + yz_grid_indices[i, 1]*gridsize_z + round(0.5 * gridsize_z, 2))
            if grid_num not in yz_grid_dict:
                yz_grid_dict[grid_num] = (np.array([points[i]]), grid_center_coordinates)
            else:
                yz_grid_dict[grid_num] = (np.concatenate((yz_grid_dict[grid_num][0], [points[i]])), yz_grid_dict[grid_num][1])
            
        return (x_grid, y_grid, z_grid), (gridsize_x, gridsize_y, gridsize_z), (xz_grid_dict, yz_grid_dict)



    
    def get_local_dipole(self):
        for frame_index in self.synced_frames:
            temp_grid_coords = []
            xmol_frame = self.xmol_frames[frame_index]
            (x_grid, y_grid, z_grid), (gridsize_x, gridsize_y, gridsize_z), (xz_grid_dict, yz_grid_dict) = self.get_mesh(xmol_frame, self.griddim)
            
            # Plot the local polarization for XZ plane:
            fig, ax = plt.subplots()
            ax.set_xlim(self.x_min, self.x_max)
            ax.set_ylim(self.z_min, self.z_max)
            ax.grid(True)
            ax.set_xticks(x_grid)
            ax.set_yticks(z_grid)
            ax.set_xlabel('X(A)')
            ax.set_ylabel('Z(A)')
            xz_grid_info = []
            for grid_num, (points, grid_coords) in xz_grid_dict.items():
                _, polarization = self.get_dipole(points)
                polarization = polarization * -1.60217646 * 1000
                if polarization >= 0:
                    color = 'blue'
                else:
                    color = 'red'
                xz_grid_info.append((polarization, grid_coords, color))
            max_xpol = np.max(np.abs(np.array(xz_grid_info)[:,0]))
            for polarization, grid_coords, color in xz_grid_info:
                plt.arrow(grid_coords[0], grid_coords[1]-polarization/max_xpol*gridsize_z/2.5, dx=0, dy=polarization/max_xpol*gridsize_z/1.25, head_width=0.2, head_length=0.2, fc=color, ec=color)
            ax.annotate(f"Frame {frame_index.zfill(len(str(self.num_frames)))}", xy=(0, 1), xycoords='axes fraction', fontsize=14, ha='left', va='top')
            fig.savefig('dipole_analysis/local_polarization/XZ_images/xz_{}.eps'.format(frame_index), bbox_inches='tight', format='eps')
            fig.savefig('dipole_analysis/local_polarization/XZ_images/xz_{}.png'.format(frame_index.zfill(len(str(self.num_frames)))), bbox_inches='tight', format='png')

            # Plot the local polarization for YZ plane:
            fig, ax = plt.subplots()
            ax.set_xlim(self.y_min, self.y_max)
            ax.set_ylim(self.z_min, self.z_max)
            ax.grid(True)
            ax.set_xticks(y_grid)
            ax.set_yticks(z_grid)
            ax.set_xlabel('Y(A)')
            ax.set_ylabel('Z(A)')
            yz_grid_info = []
            for grid_num, (points, grid_coords) in yz_grid_dict.items():
                _, polarization = self.get_dipole(points)
                polarization = polarization * -1.60217646 * 1000
                if polarization >= 0:
                    color = 'blue'
                else:
                    color = 'red'
                yz_grid_info.append((polarization, grid_coords, color))
            max_ypol = np.max(np.abs(np.array(yz_grid_info)[:,0]))
            for polarization, grid_coords, color in yz_grid_info:
                plt.arrow(grid_coords[0], grid_coords[1]-polarization/max_ypol*gridsize_z/2.5, dx=0, dy=polarization/max_ypol*gridsize_z/1.25, head_width=0.2, head_length=0.2, fc=color, ec=color)
            ax.annotate(f"Frame {frame_index.zfill(len(str(self.num_frames)))}", xy=(0, 1), xycoords='axes fraction', fontsize=14, ha='left', va='top')
            fig.savefig('dipole_analysis/local_polarization/YZ_images/yz_{}.eps'.format(frame_index), bbox_inches='tight', format='eps')
            fig.savefig('dipole_analysis/local_polarization/YZ_images/yz_{}.png'.format(frame_index.zfill(len(str(self.num_frames)))), bbox_inches='tight', format='png')
        self.get_movie('dipole_analysis/local_polarization/XZ_images')
        self.get_movie('dipole_analysis/local_polarization/YZ_images')

        #Delete the .png format files
        for dir in ['XZ_images', 'YZ_images']:
            png_files = glob.glob(os.path.join(f'dipole_analysis/local_polarization/{dir}', '*.png'))
            # Loop through the list of .png files and remove each one
            for png_file in png_files:
                os.remove(png_file)




    def get_hysteresis(self):
        x = [100*i for i in self.mag_list]
        y = [Dipole_Analyzer.polar_scale_factor*i for i in self.total_polz_list]
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.plot(x, y, marker='o', linewidth=3, markersize=4)
        ax.set_xlim(min(x)-5, max(x)+5)
        ax.set_ylim(min(y)-10, max(y)+10)
        ax.axhline(0, color='black', linestyle='--')
        try:
            intercepts = self.get_intercept(y, x)
            assert(len(intercepts)==2)
            plt.scatter(intercepts, [0,0], marker='x', c='k', s=150, linewidth=3, zorder=10)
            ax.scatter(intercepts, [0,0], marker='x', c='k', s=150, linewidth=3, zorder=10)
            right_intercept = max(intercepts)
            left_intercept = min(intercepts)
            ax.annotate(right_intercept, xy=(right_intercept, 0), xytext=(13,8),
                        ha='right', va='bottom', fontsize=20)
            ax.annotate(left_intercept, xy=(left_intercept, 0), xytext=(-9,8),
                        ha='right', va='bottom', fontsize=20)
        except:
            print('More than two coercive field values found! Skipping the plot of coercive fields...')
            
        ax.set_xlabel('Electric Field (MV/cm)', fontsize=20)
        ax.set_ylabel('$P_z$ '+' ($\mu C$/'+'$cm^2$)', fontsize=20)
        ax.tick_params(axis='both', which='major', labelsize=15)
        fig.savefig('dipole_analysis/total_polarization/Hysteresis.eps', bbox_inches='tight', format='eps')

    def get_movie(self, image_dir):
        #Get the .gif name based on the directory
        name = image_dir.split('/')[-1].split('_')[0]
        # Get the list of .eps images in the directory
        images = glob.glob(os.path.join(image_dir, '*.png'))
        # Sort the images in alphabetical order
        images = sorted(images)
        # Create the gif using the .png images
        imageio.mimsave(f'dipole_analysis/local_polarization/{name}_movie.gif', [imageio.imread(img) for img in images], fps=1.5)

    def main(self):

        method = input('Select option:\n1: Total polarization\n2: Local polarization\n3:Both')

        try:
            method = int(method)
            assert(method in [1, 2, 3])
        except ValueError:
            raise ValueError('That was not a valid number. Please try again!')

        if method in [2, 3]:
            try:
                x, y, z = map(int, input('Enter number of X- Y- and Z-bins separated by spaces:').split())
                assert isinstance(x, int) and isinstance(y, int) and isinstance(z, int)
            except ValueError:
                raise ValueError('Numbers entered were not valid. Please try again!')
        
        instance = Dipole_Analyzer()
        if method in [2, 3]:
            instance.griddim = (x, y, z)
        instance.file_handler()
        instance.xmol_fort_handler()
        instance.eregime_handler()
        
        if method in [1, 3]:
            instance.get_total_dipole()
            instance.get_hysteresis()
        
        if method in [2, 3]:
            instance.get_local_dipole()

if __name__ == '__main__':
    Dipole_Analyzer().main()
