import numpy as np
import multiprocessing as mp
from multiprocessing import shared_memory
import zipfile
import shutil
import os


def _parallel_save_npy(shm_name, shape, dtype, file_path):
    try:
        shm = shared_memory.SharedMemory(name=shm_name)
        arr = np.ndarray(shape, dtype=dtype, buffer=shm.buf)
        np.save(file_path, arr)
        shm.close()
    except Exception as e:
        print(f"Error saving {file_path}: {e}")


class ParallelSaver:
    def __init__(self, *args, **kwds):
        self.arrays = {}
        
        for i, arr in enumerate(args):
            self.arrays[f"arr_{i}"] = np.asarray(arr)
            
        for key, arr in kwds.items():
            self.arrays[key] = np.asarray(arr)
            
        self.active_shms = {}
        self.metadata = {}
        
        for key, arr in self.arrays.items():
            if arr.nbytes == 0:
                self.metadata[key] = (None, arr.shape, str(arr.dtype))
                continue
                
            shm = shared_memory.SharedMemory(create=True, size=arr.nbytes)
            self.active_shms[key] = shm
            
            shared_array = np.ndarray(arr.shape, dtype=arr.dtype, buffer=shm.buf)
            shared_array[:] = arr[:]
            
            self.metadata[key] = (shm.name, arr.shape, str(arr.dtype))

    def save(self, target_path):
        temp_dir = f"{target_path}_temp_npz"
        os.makedirs(temp_dir, exist_ok=True)
        
        pool = mp.Pool(processes=mp.cpu_count())
        
        for key, (shm_name, shape, dtype_str) in self.metadata.items():
            file_path = os.path.join(temp_dir, f"{key}.npy")
            
            if shm_name is None:
                np.save(file_path, self.arrays[key])
                continue
                
            dtype = np.dtype(dtype_str)
            pool.apply_async(_parallel_save_npy, args=(shm_name, shape, dtype, file_path))
            
        pool.close()
        pool.join()
        
        for shm in self.active_shms.values():
            shm.close()
            shm.unlink()
            
        npz_path = f"{target_path}.npz" if not target_path.endswith('.npz') else target_path
        with zipfile.ZipFile(npz_path, 'w', compression=zipfile.ZIP_STORED) as zipf:
            for file_name in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, file_name)
                zipf.write(file_path, arcname=file_name)
        
        shutil.rmtree(temp_dir)