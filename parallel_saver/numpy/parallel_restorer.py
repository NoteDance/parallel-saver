import numpy as np
import multiprocessing as mp
from multiprocessing import shared_memory
from pathlib import Path
import zipfile
import shutil
import os


def _parallel_load_npy(shm_name, shape, dtype, offset, file_path):
    try:
        shm = shared_memory.SharedMemory(name=shm_name)
        shared_array = np.ndarray(shape, dtype=dtype, buffer=shm.buf, offset=offset)
        
        loaded_arr = np.load(file_path)
        shared_array[:] = loaded_arr[:]
        shm.close()
    except Exception as e:
        print(f"Error loading {file_path}: {e}")


def restore(file_path):
    file_path = str(file_path)
    if not file_path.endswith('.npz'):
        file_path += '.npz'
        
    temp_dir = f"{file_path}_extracted_temp"
    os.makedirs(temp_dir, exist_ok=True)
    
    with zipfile.ZipFile(file_path, 'r') as zipf:
        zipf.extractall(temp_dir)
        
    path_obj = Path(temp_dir)
    npy_files = list(path_obj.glob("*.npy"))
    
    total_size = 0
    metadata_list = []
    
    for npy_file in npy_files:
        arr_mmap = np.load(npy_file, mmap_mode='r')
        
        remainder = total_size % 64
        if remainder != 0:
            total_size += (64 - remainder)
            
        offset = total_size
        nbytes = arr_mmap.nbytes
        
        metadata_list.append({
            'key': npy_file.stem,
            'file_path': str(npy_file),
            'shape': arr_mmap.shape,
            'dtype': arr_mmap.dtype,
            'nbytes': nbytes,
            'offset': offset
        })
        total_size += nbytes
        
    if total_size == 0:
        shutil.rmtree(temp_dir)
        return {}
        
    large_shm = shared_memory.SharedMemory(create=True, size=total_size)
    pool = mp.Pool(processes=mp.cpu_count())
    
    for meta in metadata_list:
        if meta['nbytes'] > 0:
            pool.apply_async(_parallel_load_npy, args=(
                large_shm.name, meta['shape'], meta['dtype'], 
                meta['offset'], meta['file_path']
            ))
            
    pool.close()
    pool.join()
    
    result_dict = {}
    for meta in metadata_list:
        if meta['nbytes'] == 0:
            result_dict[meta['key']] = np.empty(meta['shape'], dtype=meta['dtype'])
        else:
            shm_arr = np.ndarray(meta['shape'], dtype=meta['dtype'], buffer=large_shm.buf, offset=meta['offset'])
            result_dict[meta['key']] = shm_arr.copy()
            
    large_shm.close()
    large_shm.unlink()
    shutil.rmtree(temp_dir)
    
    return result_dict