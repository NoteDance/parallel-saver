import numpy as np
import multiprocessing as mp
from multiprocessing import shared_memory
import pickle
import os


class ParallelSaver:
    def __init__(self, data):
        if type(data) == list:
            self.data_list = data
            self.index = []
            for i in range(len(self.data_list)):
                self.index.append(f"arr_{i}")
        elif type(data) == dict:
            self.data_list = list(data.values())
            self.index = list(data.keys())
        self.active_shms = []
        for i in range(len(self.data_list)):
            data = self.data_list[i]
            shm = shared_memory.SharedMemory(create=True, size=data.nbytes)
            self.active_shms.append(shm)
            shared_array = np.ndarray(data.shape, dtype=data.dtype, buffer=shm.buf)
            shared_array[:] = data[:]
    
    def parallel_dump(self, shm_metadata, index, path, counter):
        os.makedirs(path, exist_ok=True)
        path = os.path.join(path, f"data_{counter}.dat")
        output_file = open(path,'wb')
        name, shape, dtype, offset = shm_metadata
        shm = shared_memory.SharedMemory(name=name)
        data = np.ndarray(shape, dtype=dtype, buffer=shm.buf)
        pickle.dump(data, output_file)
        output_file.close()
        os.makedirs(path, exist_ok=True)
        path = os.path.join(path, f"data_index_{counter}.dat")
        output_file = open(path, 'wb')
        pickle.dump(index, output_file)
        output_file.close()
        path = os.path.join(path, f"data_metadata_{counter}.dat")
        output_file = open(path, 'wb')
        pickle.dump((data.shape, data.dtype, offset), output_file)
        output_file.close()
        shm.close()
    
    def align_to_64(self, size_in_bytes):
        return (size_in_bytes + 63) & ~63
    
    def save(self, path):
        counter = 0
        current_offset = 0
        pool = mp.Pool(processes=os.cpu_count())
        for i in range(len(self.data_list)):
            counter += 1
            data = self.data_list[i]
            index = self.index[i]
            shm = self.active_shms[i]
            shm_metadata = (shm.name, data.shape, data.dtype, current_offset)
            current_offset += self.align_to_64(data.nbytes)
            pool.apply_async(self.parallel_dump, args=(shm_metadata, index, path, counter))
        pool.close()
        pool.join()
        for shm in self.active_shms:
            shm.close()
            shm.unlink()