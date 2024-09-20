# utils/optimization.py

import numpy as np
import open3d as o3d

def optimize_point_cloud(pcd):
    # Downsample the point cloud for efficiency
    pcd = pcd.voxel_down_sample(voxel_size=0.005)

    # Remove noise
    pcd = remove_noise(pcd)

    # Estimate normals
    pcd.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.01, max_nn=30))

    return pcd

def remove_noise(pcd, nb_neighbors=20, std_ratio=1.0):
    # Statistical outlier removal
    clean_pcd, _ = pcd.remove_statistical_outlier(nb_neighbors=nb_neighbors, std_ratio=std_ratio)
    return clean_pcd
