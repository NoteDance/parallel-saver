# parallel-saver

A lightweight Python utility for **fast, parallel saving and loading of NumPy arrays** using shared memory and multiprocessing.

---

## Overview

`parallel-saver` provides two main components:

- **`Parallel_saver`** — Serializes a list of NumPy arrays to disk in parallel, using shared memory to avoid data copying across processes.
- **`restore`** — Deserializes and reconstructs the array list from disk in parallel, preserving original ordering.

This is particularly useful when working with large collections of NumPy arrays where sequential I/O becomes a bottleneck.

---

## Features

- Zero-copy inter-process data sharing via `multiprocessing.shared_memory`
- Parallel file writes and reads using `multiprocessing.Process`
- Preserves original array ordering through index files
- Simple, dependency-light API

---

## Requirements

- Python ≥ 3.8
- NumPy

No third-party packages required beyond NumPy. `multiprocessing`, `pickle`, `os`, and `pathlib` are all from the standard library.

---

## Usage

### Saving arrays

```python
import numpy as np
from parallel_saver.parallel_saver import Parallel_saver

# Create a list of NumPy arrays
data_list = [np.random.rand(1000, 1000) for _ in range(8)]

# Save to disk in parallel
saver = Parallel_saver(data_list)
saver.save("./output_dir")
```

Each array is written to `output_dir/data_<n>.dat`, along with a corresponding index file `data_index_<n>.dat` that records its original position in the list.

---

### Restoring arrays

```python
from parallel_saver.parallel_restorer import restore

data_list = restore("./output_dir")
# data_list is a managed list with arrays restored in their original order
```

---

## How It Works

```
┌─────────────────────────────────────────────────────┐
│                      SAVE PHASE                     │
│                                                     │
│  data_list[0] ──► SharedMemory[0] ──► Process 0 ──► data_1.dat      │
│  data_list[1] ──► SharedMemory[1] ──► Process 1 ──► data_2.dat      │
│        ...                ...              ...                       │
│  data_list[n] ──► SharedMemory[n] ──► Process n ──► data_n+1.dat    │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│                     LOAD PHASE                      │
│                                                     │
│  data_1.dat ──► Process 0 ──► data_list[original_index_0]           │
│  data_2.dat ──► Process 1 ──► data_list[original_index_1]           │
│       ...            ...              ...                            │
└─────────────────────────────────────────────────────┘
```

1. **Save**: Each array is placed into a named `SharedMemory` block. A separate process reads directly from shared memory and pickles the array to disk — no data copying between the main process and workers.
2. **Load**: Index files are read sequentially to determine the correct slot for each array. Workers load data files in parallel and write into a `Manager`-backed shared list, restoring original ordering.

---

## API Reference

### `class parallel_save(data_list)`

| Parameter   | Type              | Description                          |
|-------------|-------------------|--------------------------------------|
| `data_list` | `list[np.ndarray]`| List of NumPy arrays to be saved     |

#### `parallel_save.save(path)`

| Parameter | Type  | Description                              |
|-----------|-------|------------------------------------------|
| `path`    | `str` | Directory path where files will be saved |

Spawns one process per array. All shared memory blocks are released after all processes complete.

---

### `restore(path) -> list[np.ndarray]`

| Parameter | Type  | Description                                |
|-----------|-------|--------------------------------------------|
| `path`    | `str` | Directory path previously written by `save`|

Returns a `multiprocessing.Manager` list populated with the original arrays in their correct positions.

---

## File Layout

After calling `save("./output_dir")` on a list of 3 arrays, the directory will contain:

```
output_dir/
├── data_1.dat          # pickled array (original index 0)
├── data_index_1.dat    # stores integer 0
├── data_2.dat          # pickled array (original index 1)
├── data_index_2.dat    # stores integer 1
├── data_3.dat          # pickled array (original index 2)
└── data_index_3.dat    # stores integer 2
```
