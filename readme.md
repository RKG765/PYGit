# PyGit — A Minimal Git-like Version Control System in Python

PyGit is a **from-scratch implementation of core Git internals** written in Python.  
The objective of this project is to understand how Git works **under the hood**, including
content-addressable storage, object hashing, compression, staging, and tree construction.

This project does **not** use Git libraries or shell commands internally. All logic is implemented manually for learning and experimentation.

---

## Features

### Implemented
- Content-addressable object storage
- Git-compatible SHA-1 hashing  
  (`<type> <size>\0<content>`)
- zlib-based object compression
- Blob objects for file contents
- Tree objects for directory representation
- Index (staging area) stored on disk
- Recursive directory traversal
- Command-line interface (CLI)
  - `init`
  - `add` (file or directory)
  - `commit` (basic structure)

---

## How It Works (High Level)

1. File contents are read as raw bytes
2. A Git-style header is prepended  
   `blob <size>\0`
3. SHA-1 hash is computed over header + content
4. Object data is compressed using zlib
5. Object is stored in a content-addressable layout
6. The index maps file paths to blob hashes
7. Trees are constructed recursively from the index

---

## Requirements

- Python **3.9 or higher**
- No third-party dependencies

---

## How to Run

### Initialize a Repository
```bash
python main.py init
```

### Expected result:

Internal repository directory created

Object storage and references initialized


### Add a File

``` bash
python main.py add test1.txt
```

### Expected result:

File content hashed

Blob object created and stored

Index updated

### Add a Directory

```bash

python main.py add .
```
Recursively stages all files except internal repository data.

### Commit
```bash
python main.py commit -m "First commit"
```
Creates a tree object from the staging index and prepares commit metadata.

Commit implementation is minimal and educational.

## Index Format

The staging index is stored as JSON and maps file paths to blob hashes:

```json
{
  "test1.txt": "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3"
}
```

## Object Storage Format

Objects are stored using the same logical format as Git:
```php
zlib(
  "<type> <size>\\0<content>"
)
```

Each object is addressed by its SHA-1 hash.

## Learning Outcomes

This project demonstrates understanding of:

Git internal object model

Content-addressable storage

Hash-based immutability

Filesystem-backed data storage

Recursive tree construction

CLI design using argparse

Binary data handling in Python


## Future Improvements

Full commit object support

Parent commit chaining

Branch management

Diff and status implementation

Compatibility validation with real Git

# Author

Raj Kumar





