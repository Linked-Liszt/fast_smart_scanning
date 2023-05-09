import gradio as gr


import fast.s26_analysis.utils as utils 
from fast.utils.generate_scan_pattern import generate_scan_pattern as gcn

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import matplotlib as mpl
import skimage
from tqdm.notebook import tqdm
import tifffile as tif
import joblib
import numpy as np
import cv2

class ScanUI:
    def __init__(self):
        self.num_imgs = 5
        self.main_interface()


    def run_scan(self, input_im):
        init_pattern = gcn(*input_im.T.shape, 0.01)


        # Specifying the trained nn model to use
        # We use the model generated for c=2.
        erd_model_to_load = Path.cwd().parent / 'training/cameraman/c_2/erd_model_relu.pkl'

        # Creating a simulated sample
        # Setting the initial batch size to 50 (inner_batch_size=50)
        # Supplying the nn model path
        sample_fast = utils.create_experiment_sample(numx=input_im.shape[1], numy=input_im.shape[0],
                                                inner_batch_size=50,
                                                initial_idxs=init_pattern,
                                                erd_model_file_path=erd_model_to_load)

        # Actual simulation run. This can be fairly time consuming
        masks_all = []
        recons_fast_all = []
        ratios_all = []
        tot_erds_all = []
        count = 0
        new_idxs = init_pattern


        n_scan_points = int(0.4 * input_im.size)
        out_ims = np.zeros((n_scan_points // 50, input_im.shape[0], input_im.shape[1] * 2))

        i = 0
        while sample_fast.mask.sum() < n_scan_points:
            print(sample_fast.mask.sum(), n_scan_points)
            # Supply the measurement values.
            sample_fast.measurement_interface.finalize_external_measurement(input_im[new_idxs[:,0], new_idxs[:,1]])
            
            # Supply in measurement positions
            sample_fast.perform_measurements(new_idxs)
            
            # Use the measurement values to reconstruct the sample and calculate the ERDs
            sample_fast.reconstruct_and_compute_erd()
            
            # Compute new positions.
            new_idxs = sample_fast.find_new_measurement_idxs()[:50]
            
            ratio = sample_fast.ratio_measured
            ratios_all.append(ratio)
            tot_erds_all.append(sample_fast.ERD.sum())
            recons_fast_all.append(sample_fast.recon_image.copy())
            masks_all.append(sample_fast.mask.copy())

            # Hardcoded for now
            out_ims[i, :, 0:input_im.shape[1]] = sample_fast.mask * 256
            out_ims[i, :, input_im.shape[1]:input_im.shape[1] * 2] = sample_fast.recon_image

            i += 1

        return out_ims

    def init_image(self):
        coffee = skimage.color.rgb2gray(skimage.data.coffee())

        coffee = skimage.transform.resize(coffee[:256,100:356], (128, 128))
        coffee = (coffee - coffee.min()) / (coffee.max() - coffee.min()) * 100

        return coffee


    def render_im(self, incoming_im):
        print(incoming_im.shape)
        print(type(incoming_im))
        im = cv2.cvtColor(incoming_im, cv2.COLOR_BGR2GRAY)
        scans = self.run_scan(im)


        ims = []
        print(scans.shape)

        scans_norm = (scans-np.min(scans))/(np.max(scans)-np.min(scans))
        for i in range(scans_norm.shape[0]):
            ims.append(scans_norm[i])

        print('done')
        
        return gr.Gallery.update(value=ims)


    def main_interface(self):
        with gr.Blocks(title='Fast Smart Scan Demo') as scan_if:
            im_ul = gr.Image()
            scan_gal = gr.Gallery(label='Scan Preview')


            im_ul.upload(self.render_im, inputs=[im_ul], outputs=[scan_gal])

        scan_if.launch()
    

if __name__ == '__main__':
    fss_ui = ScanUI()