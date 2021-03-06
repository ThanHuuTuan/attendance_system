
import os
import numpy as np
import tensorflow as tf 
from modules.network import RetinaFaceModel
from utils.align_face import FaceAligner
from modules.utils import (set_memory_growth, load_yaml, draw_bbox_landm,
                           pad_input_image, recover_pad_output, preprocess_input)

class RetinaFace():
    def __init__(self, cfg_path):
        self.model = self.__create_model(cfg_path)

    def __create_model(self, cfg_path):
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
        os.environ['CUDA_VISIBLE_DEVICES'] = '0'

        logger = tf.get_logger()
        logger.disabled = True
        # logger.setLevel(logging.FATAL)
        set_memory_growth()
        cfg = load_yaml(cfg_path)
        model = RetinaFaceModel(cfg, training=False, iou_th=0.4,
                                score_th=0.5)
        # load checkpoint
        checkpoint_dir = './checkpoints/' + cfg['sub_name']
        checkpoint = tf.train.Checkpoint(model=model)
        if tf.train.latest_checkpoint(checkpoint_dir):
            checkpoint.restore(tf.train.latest_checkpoint(checkpoint_dir))
            print("[*] load ckpt from {}.".format(
                tf.train.latest_checkpoint(checkpoint_dir)))
        else:
            print("[*] Cannot find ckpt from {}.".format(checkpoint_dir))
            exit()
        return model

    def __detect_faces(self, frame):
        img = np.float32(frame.copy())
        # pad input image to avoid unmatched shape problem
        img, pad_params = pad_input_image(img, max_steps=32)
        
        # run model
        outputs = self.model(img[np.newaxis, ...]).numpy()

        # recover padding effect
        outputs = recover_pad_output(outputs, pad_params)

        return outputs

    def extract_faces(self, frame):
        frame_height, frame_width,_ = frame.shape
        outputs = self.__detect_faces(frame)
        aligner = FaceAligner()
        results = np.empty((0,160,160,3))
        for ann in outputs:
            b_box = int(ann[0] * frame_width), int(ann[1] * frame_height), \
                    int(ann[2] * frame_width), int(ann[3] * frame_height)
            if (b_box[0]<0) or (b_box[1]<0) or (b_box[2]>=frame_width) or (b_box[3]>=frame_height):
                continue
            keypoints = {
                'left_eye': (int(ann[4] * frame_width),int(ann[5] * frame_height)),
                'right_eye': (int(ann[6] * frame_width),int(ann[7] * frame_height)),
            }
            out_frame = aligner.align(frame, keypoints, b_box)
            out_frame = preprocess_input(out_frame)
            results = np.vstack([results, out_frame[np.newaxis,...]])
        return results
        