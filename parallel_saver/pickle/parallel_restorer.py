import numpy as np
import multiprocessing as mp
from multiprocessing import shared_memory
from pathlib import Path
import pickle
import os


def parallel_load(self, shm_name, metadata, path, counter):
    input_file=open(os.path.join(path,f"data_{counter}.dat"),'rb')
    existing_shm = shared_memory.SharedMemory(name=shm_name)
    shared_array = np.ndarray(metadata[0], dtype=metadata[1], buffer=existing_shm.buf, offset=metadata[2])
    shared_array[:] = pickle.load(input_file)[:]
    existing_shm.close()
    input_file.close()


def restore(path):
    path = Path(path)
    pattern = "data_index*"
    matching_files = [f for f in path.glob(pattern) if f.is_file()]
    count = len(matching_files)
    metadata_list = []
    counter = 0
    total_size = 0
    for i in range(count):
        counter += 1
        input_file = open(os.path.join(path, f"data_metadata_{counter}.dat"), 'rb')
        metadata = pickle.load(input_file)
        metadata_list.append(metadata)
        aligned_nbytes = metadata[2]
        total_size += aligned_nbytes
        input_file.close()
    large_shm = shared_memory.SharedMemory(create=True, size=total_size)
    data_dict = {}
    index_list = []
    counter = 0
    pool = mp.Pool(processes=os.cpu_count())
    for i in range(count):
        counter += 1
        input_file = open(os.path.join(path, f"data_index_{counter}.dat"), 'rb')
        index = pickle.load(input_file)
        index_list.append(index)
        metadata = metadata_list[counter]
        pool.apply_async(parallel_load, args=(large_shm.name, metadata, path, counter))
        input_file.close()
    pool.close()
    pool.join()
    counter = 0
    for i in range(count):
        counter += 1
        metadata = metadata_list[counter]
        shm_arr = np.ndarray(metadata[0], dtype=metadata[1], buffer=large_shm.buf, offset=metadata[2])
        index = index_list[counter]
        data_dict[index] = shm_arr.copy()
    large_shm.close()
    large_shm.unlink()
    return data_dict