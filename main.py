from __future__ import annotations  #used for calling the same class in the same class
import argparse
from pathlib import Path
import json
import sys
import hashlib
import zlib
from typing import Dict
from typing import List
from typing import Tuple
class GitObject:
    def __init__(self,obj_type:str,content:bytes):
        self.type = obj_type
        self.content = content

    def hash(self)-> str:
        # the sha format will in this format
        # <type> <size>\0<content>
        header = f"{self.type} {len(self.content)}\0".encode()
        return hashlib.sha1(header + self.content).hexdigest()
    
    def serialize(self)->bytes:
        header = f"{self.type} {len(self.content)}\0".encode()
        # lossless compression
        return zlib.compress(header + self.content)
    
    @classmethod
    def deserialize(cls,data: bytes)-> GitObject:
        decompressed = zlib.decompress(data)
        null_idx = decompressed.find(b"\0")
        header = decompressed[:null_idx]
        content = decompressed[null_idx+1:]

        obj_type, _  = header.split(" ")
        return cls(obj_type,content)



# storing file content
class Blob(GitObject):
    def __init__(self, content: bytes):
        super().__init__('blob', content)
    
    def get_content(self)->bytes:
        return self.content

class Tree(GitObject):
    def __init__(self, entries: List[Tuple[str,str,str]]):
        self.entries = entries or []
        content = self._serialize_entries()
        super().__init__("tree", content)
    
    def _serialize_entries(self)-> bytes:
        # format
        # <mode> <name>\0<hash>
        content = b""
        for mode, name, obj_hash in sorted(self.entries):
            content += f"{mode} {name}\0".encode()
            content += bytes.fromhex(obj_hash)
        
        return content
    
    def add_entry(self , mode:str,name:str,obj_hash:str):
        self.entries.append(mode,name,obj_hash)
        self.content = self._serialize_entries()

    @classmethod
    def from_content(cls,content: bytes)-> Tree:
        tree = cls()
        i = 0

        while i < len(content):
            null_idx =content.find(b"\0",i)
            if null_idx == -1:
                break
            
            mode_name = content[i:null_idx].decode()
            mode,name = mode_name.split(" ",1)
            obj_hash = content[null_idx+1:null_idx+21].hex()
            tree.entries.append((mode,name,obj_hash))
            i = null_idx+21
        
        return tree
    

class Repository:
    def __init__(self,path = "."):
        self.path  = Path(path).resolve()  # git init
        self.git_dir = self.path / ".pygit"

        # .git/objects in the real git
        self.objects_dir  = self.git_dir / "objects"
        # .git/refs
        self.ref_dir  = self.git_dir / "refs"
        self.heads_dir = self.ref_dir / "heads"

        # .git/Head
        self.head_file = self.git_dir / "HEAD"
        # .git/index
        self.index_file = self.git_dir / "index"
    def init(self)-> bool:
        if self.git_dir.exists():
            return False
        # create directories .pygit,objects,ref
        self.git_dir.mkdir()
        self.objects_dir.mkdir()
        self.ref_dir.mkdir()
        self.heads_dir.mkdir()

        # create inital HEAD pointing to a branch
        self.head_file.write_text("ref: refs/heads/master\n")

        # creating a empty index file which stores realtions(filename<->hash related) in json

        self.save_index({})
        # self.index_file.write_text(json.dumps({},indent = 2))

        print(f"Initialized Empty pygit repository in {self.git_dir}")
        return True
    
    def store_object(self,obj = GitObject)-> str:
          
          obj_hash = obj.hash()
          obj_dir = self.objects_dir / obj_hash[:2]
          obj_file = obj_dir / obj_hash[2:]

          if not obj_file.exists():
                obj_dir.mkdir(exist_ok = True)
                obj_file.write_bytes(obj.serialize())

          return obj_hash
    
    def load_index(self)-> Dict[str,str] :
        if not self.index_file.exists():
            return {}
        try:
            return json.loads(self.index_file.read_text())
        except:
            return {}

    def save_index(self,index: Dict[str,str]):
        self.index_file.write_text(json.dumps(index,indent = 2))
        

    def add_file(self,path:str):
        full_path  = self.path / path
        if not full_path.exists():
            raise FileNotFoundError(f"Path [{path}] not found error !")

        # read the file contents
        content = full_path.read_bytes()

        # create a BLOB(Binary Large Objects) object
        blob = Blob(content)

        # store the BLOB in the database (.pygit/objects)     
        blob_hash = self.store_object(blob)

        # update the index part

        index = self.load_index()  # load file
        index[path] = blob_hash    # updating
        self.save_index(index)     # saving
        print(f"Added {path}")

    
    def add_directory(self,path: str):
        full_path  = self.path / path
        if not full_path.exists():
            raise FileNotFoundError(f"Directory [{path}] not found error !")
        if not full_path.is_dir():
            raise ValueError(f"{path} is not a directory")
        index = self.load_index()
        added_count = 0
        # recursively traverse the directory
        for file_path in full_path.rglob("*"):
            if file_path.is_file():
                if ".pygit" in file_path.parts:
                    continue
            
                # create and store blob object
                content = file_path.read_bytes()
                blob  = Blob(content)
                blob_hash = self.store_object(blob)
                # update the index
                rel_path = str(file_path.relative_to(self.path))
                index[rel_path] = blob_hash
                added_count+=1
        
        self.save_index(index)
        if added_count > 0:
            print(f"Added {added_count} files from directory {path}")
        else:
            print(f"Directory {path} already up to date")



    def add_path(self,path:str)-> None:
        full_path = self.path / path

        if not full_path.exists():
            raise FileNotFoundError(f"Path {path} not found.")
        if full_path.is_file():
            self.add_file(path)
        elif full_path.is_dir():
            self.add_directory(path)
        else:
            raise ValueError(f"{path} is neither file or dir")

    def create_tree_from_index(self):
        index = self.load_index()
        if not index:
            tree = Tree()
            return self.store_object(tree)
        dirs = {}
        files = {}

        for file_path,blob_hash in index.items():
            parts = file_path.split("/")

            if len(parts) == 1:
                # file is in root folder
                files[parts[0]] = blob_hash
            else:
                dir_name = parts[0]
                if dir_name not in dirs:
                    dirs[dir_name] = {}
                current = dirs[dir_name]
                for part in parts[1:-1]:
                    if part not in current:
                        current[part] = {}
                    
                    current = current[part]
                current[parts[-1]] = blob_hash
        
        def create_tree_recursive(entries_dict: Dict):
                                                        <-----------
            pass
        root_entries = {**files}
        for dir_name, dir_contents in dirs.items():
            root_entries[dir_name] = dir_contents
        
        return create_tree_recursive(root_entries)

                     

    def commit(self,message: str,author:str="PyGit User user@pygit.com",):
        # create a tree object from the index
        tree_hash = self.create_tree_from_index()
        pass   <----
               
        


        
def main():
    parser = argparse.ArgumentParser(description="PyGit - A Git clone in pyhton !")
    subparsers = parser.add_subparsers(dest = "command",help = "Available Commands")
    # init command
    init_parser = subparsers.add_parser("init",help = "Initialize a new repository.")
    # add command
    add_parser = subparsers.add_parser("add",help = "Add files and directories to the staging area.")
    add_parser.add_argument("paths",nargs='+',help="Files and Directories to add.")

    # commit command
    commit_parser = subparsers.add_parser("commit",help="Create a new commit")

    commit_parser.add_argument("-m","--message",help="commit message",required=True)
    commit_parser.add_argument("--author",help="Author name and email")

    
    
    args  = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    repo = Repository()
    try:
        if args.command == "init":
            if not repo.init():
                print("Repository already exists")
                return
        elif args.command == "add":
            if not repo.git_dir.exists():
                print("Make a git repo first....")
                return
            for path in args.paths:
                repo.add_path(path)
        elif args.command == "commit":
            if not repo.git_dir.exists():
                print("Make a git repo first....")
                return
            author = args.author or "PyGit user <user@pygit.com>"
            repo.commit(args.message,author)    <--- create that function 
                   
            
            
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

main()
