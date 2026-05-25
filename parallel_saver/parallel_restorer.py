import multiprocessing as mp
from pathlib import Path
import pickle
import os


def parallel_load(data_list, index, path, counter):
    input_file=open(os.path.join(path, f"data_{counter}.dat"),'rb')
    data_list[index]=pickle.load(input_file)
    input_file.close()


def restore(path):
    path = Path(path)
    pattern = "data_index*"
    matching_files = [f for f in path.glob(pattern) if f.is_file()]
    count = len(matching_files)
    manager = mp.Manager()
    data_list = manager.list()
    counter = 0
    for i in range(count):
        data_list.append(None)
    process_list = []
    for i in range(count):
        counter += 1
        input_file = open(os.path.join(path, f"data_index_{counter}.dat"), 'rb')
        index = pickle.load(input_file)
        process = mp.Process(target=parallel_load, args=(data_list, index, path, counter))
        process.start()
        process_list.append(process)
        input_file.close()
    for process in process_list:
        process.join()