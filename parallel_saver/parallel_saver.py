import numpy as np
import multiprocessing as mp
from multiprocessing import shared_memory
import pickle
import os


class Parallel_saver:
    def __init__(self, data_list):
        self.data_list = data_list
        self.active_shms = []
        for i in range(len(data_list)):
            data = data_list[i]
            shm = shared_memory.SharedMemory(create=True, size=data.nbytes)
            self.active_shms.append(shm)
            shared_array = np.ndarray(data.shape, dtype=data.dtype, buffer=shm.buf)
            shared_array[:] = data[:]
    
    def parallel_dump(self, shm_metadata, index, path, counter):
        os.makedirs(path, exist_ok=True)
        filename = os.path.join(path, f"data_{counter}.dat")
        output_file=open(filename,'wb')
        name, shape, dtype = shm_metadata
        shm = shared_memory.SharedMemory(name=name)
        data = np.ndarray(shape, dtype=dtype, buffer=shm.buf)
        pickle.dump(data, output_file)
        output_file.close()
        os.makedirs(path, exist_ok=True)
        path = os.path.join(path, f"data_index_{counter}.dat")
        output_file=open(path,'wb')
        pickle.dump(index, output_file)
        output_file.close()
        shm.close()
    
    def save(self, path):
        counter=0
        process_list = []
        for i in range(len(self.data_list)):
            counter+=1
            data = self.data_list[i]
            shm = self.active_shms[i]
            shm_metadata = (shm.name, data.shape, data.dtype)
            process = mp.Process(target=self.parallel_dump, args=(shm_metadata, i, path, counter))
            process.start()
            process_list.append(process)
        for process in process_list:
            process.join()
        for shm in self.active_shms:
            shm.close()
            shm.unlink()