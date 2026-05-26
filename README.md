# Parallel Saver(pickle)

A lightweight Python utility for **fast, parallel saving and loading of NumPy arrays** using shared memory and multiprocessing.

---

## Overview

`parallel-saver` provides two main components:

- **`ParallelSaver`** — Serializes a list or dict of NumPy arrays to disk in parallel, using shared memory to avoid data copying across processes.
- **`restore`** — Deserializes and reconstructs the arrays from disk in parallel into a single contiguous shared memory block, returning a `dict`.

This is particularly useful when working with large collections of NumPy arrays where sequential I/O becomes a bottleneck.

---

## Features

- Zero-copy inter-process data sharing via `multiprocessing.shared_memory`
- Parallel file writes and reads using `multiprocessing.Pool`
- Accepts both `list` and `dict` as input — dict keys are preserved as array identifiers
- Restores all arrays into a single 64-byte-aligned shared memory block for efficient loading
- Preserves array metadata (shape, dtype, offset) through dedicated metadata files
- Simple, dependency-light API

---

## Requirements

- Python ≥ 3.8
- NumPy

No third-party packages required beyond NumPy. `multiprocessing`, `pickle`, `os`, and `pathlib` are all from the standard library.

---

## Usage

### Saving a list of arrays

```python
import numpy as np
from parallel_saver import ParallelSaver

data_list = [np.random.rand(1000, 1000) for _ in range(8)]

saver = ParallelSaver(data_list)
saver.save("./output_dir")
# Keys default to "arr_0", "arr_1", ..., "arr_n"
```

### Saving a dict of arrays

```python
import numpy as np
from parallel_saver import ParallelSaver

data_dict = {
    "features": np.random.rand(512, 768),
    "labels":   np.array([0, 1, 2, 3]),
    "weights":  np.random.rand(256, 256),
}

saver = ParallelSaver(data_dict)
saver.save("./output_dir")
# Dict keys are preserved and restored on load
```

### Restoring arrays

```python
from parallel_saver import restore

data = restore("./output_dir")
# Returns a dict, e.g. {"arr_0": ..., "arr_1": ...} or {"features": ..., "labels": ..., "weights": ...}
```

---

## How It Works

```
┌──────────────────────────────────────────────────────────────────────┐
│                            SAVE PHASE                                │
│                                                                      │
│  data[key_0] ──► SharedMemory[0] ──► Worker 0 ──► data_1.dat        │
│  data[key_1] ──► SharedMemory[1] ──► Worker 1 ──► data_2.dat        │
│      ...               ...               ...          ...            │
│  data[key_n] ──► SharedMemory[n] ──► Worker n ──► data_n+1.dat      │
│                                                                      │
│  Each worker also writes: data_index_n.dat, data_metadata_n.dat      │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                            LOAD PHASE                                │
│                                                                      │
│  metadata files ──► compute total size ──► one large SharedMemory    │
│                                                  │                   │
│  data_1.dat ──► Worker 0 ──► SharedMemory[offset_0]                 │
│  data_2.dat ──► Worker 1 ──► SharedMemory[offset_1]                 │
│      ...              ...           ...                              │
│                                                  │                   │
│                         copy-out to dict ◄────────                   │
└──────────────────────────────────────────────────────────────────────┘
```

1. **Save**: Each array is placed into its own named `SharedMemory` block. A pool of workers reads directly from shared memory and pickles each array to disk, alongside an index file (the key) and a metadata file (shape, dtype, byte offset).
2. **Load**: Metadata files are read first to calculate the total required size. A single 64-byte-aligned `SharedMemory` block is allocated to hold all arrays. Workers load each data file in parallel and write into the correct offset of the shared block. Finally, arrays are copied out into a plain Python dict and the shared memory is released.

---

## API Reference

### `class ParallelSaver(data)`

| Parameter | Type | Description |
|-----------|------|-------------|
| `data` | `list[np.ndarray]` or `dict[str, np.ndarray]` | Arrays to save. If a list, keys default to `"arr_0"`, `"arr_1"`, etc. |

#### `ParallelSaver.save(path)`

| Parameter | Type  | Description |
|-----------|-------|-------------|
| `path`    | `str` | Directory path where files will be written (created if absent) |

Uses `mp.Pool(os.cpu_count())` to write all arrays concurrently. All shared memory blocks are unlinked after the pool completes.

---

### `restore(path) -> dict[str, np.ndarray]`

| Parameter | Type  | Description |
|-----------|-------|-------------|
| `path`    | `str` | Directory previously written by `ParallelSaver.save()` |

Allocates a single contiguous shared memory region (with 64-byte alignment per array) and fills it in parallel. Returns a plain `dict` mapping each key to its corresponding NumPy array.

---

## File Layout

After calling `save("./output_dir")` on a dict with 3 entries, the directory will contain:

```
output_dir/
├── data_1.dat           # pickled array for key_0
├── data_index_1.dat     # stores "key_0"
├── data_metadata_1.dat  # stores (shape, dtype, byte_offset)
├── data_2.dat           # pickled array for key_1
├── data_index_2.dat     # stores "key_1"
├── data_metadata_2.dat  # stores (shape, dtype, byte_offset)
├── data_3.dat           # pickled array for key_2
├── data_index_3.dat     # stores "key_2"
└── data_metadata_3.dat  # stores (shape, dtype, byte_offset)
```

# Parallel Saver(numpy)

A lightweight Python utility for **fast, parallel saving and loading of NumPy arrays** using shared memory and multiprocessing, with **`.npy`-based `.npz` archive storage**.

---

## Overview

`parallel-saver` provides two main components:

- **`ParallelSaver`** — Serializes NumPy arrays to disk in parallel using shared memory, then packages them into a single portable `.npz` file.
- **`restore`** — Extracts the `.npz` archive and reconstructs all arrays in parallel into a single contiguous shared memory block, returning a `dict`.

This is particularly useful when working with large collections of NumPy arrays where sequential I/O becomes a bottleneck.

---

## Features

- Zero-copy inter-process data sharing via `multiprocessing.shared_memory`
- Parallel file writes and reads using `multiprocessing.Pool`
- Accepts positional and keyword arguments — keyword argument names are used as array keys; positional arguments default to `"arr_0"`, `"arr_1"`, etc.
- Saves to a single self-contained `.npz` file using NumPy's native `.npy` format (no pickle)
- Restores all arrays into a single 64-byte-aligned shared memory block for efficient loading
- Simple, dependency-light API

---

## Requirements

- Python ≥ 3.8
- NumPy

No third-party packages required beyond NumPy. `multiprocessing`, `zipfile`, `shutil`, `os`, and `pathlib` are all from the standard library.

---

## Usage

### Saving arrays

Pass arrays as positional arguments (auto-named `arr_0`, `arr_1`, …) or keyword arguments (names preserved as keys):

```python
import numpy as np
from parallel_saver import ParallelSaver

a = np.random.rand(1000, 1000)
b = np.random.rand(512, 512)

# Positional — keys will be "arr_0", "arr_1"
saver = ParallelSaver(a, b)
saver.save("./output")          # writes ./output.npz

# Keyword — keys are the argument names
saver = ParallelSaver(features=a, weights=b)
saver.save("./output")          # writes ./output.npz
```

Both styles can be mixed in a single call:

```python
saver = ParallelSaver(a, b, labels=np.array([0, 1, 2]))
saver.save("./output")
# Keys: "arr_0", "arr_1", "labels"
```

### Restoring arrays

```python
from parallel_saver import restore

data = restore("./output")      # .npz extension added automatically if omitted
# Returns {"arr_0": ..., "arr_1": ...}  or  {"features": ..., "weights": ..., "labels": ...}
print(data["features"].shape)
```

---

## How It Works

```
┌──────────────────────────────────────────────────────────────────────┐
│                            SAVE PHASE                                │
│                                                                      │
│  arr[key_0] ──► SharedMemory[0] ──► Worker 0 ──► key_0.npy          │
│  arr[key_1] ──► SharedMemory[1] ──► Worker 1 ──► key_1.npy          │
│      ...               ...               ...          ...            │
│  arr[key_n] ──► SharedMemory[n] ──► Worker n ──► key_n.npy          │
│                                                      │               │
│                              key_0.npy … key_n.npy ──► output.npz   │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                            LOAD PHASE                                │
│                                                                      │
│  output.npz ──► extract ──► mmap scan ──► compute total size         │
│                                                  │                   │
│                              one large 64-byte-aligned SharedMemory  │
│                                                  │                   │
│  key_0.npy ──► Worker 0 ──► SharedMemory[offset_0]                  │
│  key_1.npy ──► Worker 1 ──► SharedMemory[offset_1]                  │
│      ...              ...           ...                              │
│                                                  │                   │
│                         copy-out to dict ◄────────                   │
└──────────────────────────────────────────────────────────────────────┘
```

1. **Save**: Each array is copied into its own named `SharedMemory` block. A pool of workers reads directly from shared memory and writes each array as a `.npy` file into a temporary directory. When all workers finish, the `.npy` files are packed into a single `.npz` archive (ZIP, no compression) and the temporary directory is removed.
2. **Load**: The `.npz` archive is extracted to a temporary directory. Each `.npy` file is memory-mapped to read its shape and dtype without loading data into RAM. A single 64-byte-aligned `SharedMemory` block sized to fit all arrays is allocated. Workers load each file in parallel and write into the correct offset of the shared block. Arrays are then copied out into a plain Python `dict`, and both the shared memory and temporary directory are cleaned up.

---

## API Reference

### `class ParallelSaver(*args, **kwds)`

| Parameter | Type | Description |
|-----------|------|-------------|
| `*args`   | `np.ndarray` | Positional arrays. Automatically assigned keys `"arr_0"`, `"arr_1"`, etc. |
| `**kwds`  | `np.ndarray` | Keyword arrays. The argument name becomes the array's key. |

Non-array inputs are converted via `np.asarray()`. Zero-byte arrays are handled safely (saved directly without shared memory).

#### `ParallelSaver.save(target_path)`

| Parameter     | Type  | Description |
|---------------|-------|-------------|
| `target_path` | `str` | Output path. `.npz` extension is appended automatically if absent. |

Uses `mp.Pool(mp.cpu_count())` to write all `.npy` files concurrently, then zips them into a single `.npz` archive. All shared memory blocks are unlinked after the pool completes.

---

### `restore(file_path) -> dict[str, np.ndarray]`

| Parameter   | Type  | Description |
|-------------|-------|-------------|
| `file_path` | `str` | Path to the `.npz` file written by `ParallelSaver.save()`. `.npz` extension is appended if absent. |

Extracts the archive, allocates a single contiguous shared memory region (64-byte-aligned per array), and fills it in parallel. Returns a plain `dict` mapping each key to its NumPy array. Returns `{}` if the archive contains no arrays.

---

## File Layout

`ParallelSaver.save()` produces a **single `.npz` file**. Internally it is a ZIP archive of `.npy` files named after the array keys:

```
output.npz
 └─ (ZIP archive)
     ├── arr_0.npy        # array for key "arr_0"
     ├── arr_1.npy        # array for key "arr_1"
     └── weights.npy      # array for key "weights"
```

During `restore()`, a temporary directory `<file_path>_extracted_temp/` is created and automatically removed on completion.

---

## Comparison with `numpy.savez`

| | `parallel-saver` | `numpy.savez` |
|---|---|---|
| I/O | Parallel (multiprocessing) | Sequential |
| Format | `.npz` (compatible) | `.npz` |
| Shared memory | Yes (zero-copy workers) | No |
| Key support | Positional + keyword args | Keyword args only |
| Zero-size arrays | Handled | Handled |
