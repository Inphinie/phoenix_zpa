import mmap
import os
import struct
import hashlib
import time
import math
import ctypes
from dataclasses import dataclass

# --- CONSTANTES UNIVERSELLES ---
PHI = 1.61803398875
H_THRESHOLD = 1.0 / PHI  # ~0.618
ATOM_SIZE = 64  # 496 bits (62 bytes) + 2 bytes padding = 64 bytes (Cache Line Aligned)
MAGIC_SIG = 0x1F0

# --- COULEURS TERMINAL ---
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# --- STRUCTURE BARE-METAL (CTYPES) ---
# C'est ici que la magie opère. Cette structure est mappée DIRECTEMENT sur les octets.
# Pas de conversion, pas de parsing.
class FC496Struct(ctypes.Structure):
    _pack_ = 1  # Alignement strict sur 1 octet pour éviter le padding surprise
    _fields_ = [
        # --- MINOR SEGMENT (190 bits -> ~24 bytes) ---
        ("magic", ctypes.c_uint16),      # 2 bytes
        ("pi_index", ctypes.c_uint64),   # 8 bytes
        ("geo_hash", ctypes.c_uint64),   # 8 bytes
        ("schema", ctypes.c_uint16),     # 2 bytes
        ("h_score", ctypes.c_uint16),    # 2 bytes
        ("flags", ctypes.c_uint16),      # 2 bytes
        
        # --- MAJOR SEGMENT (306 bits -> ~38 bytes) ---
        ("payload", ctypes.c_char * 32), # 32 bytes (256 bits)
        ("strands", ctypes.c_uint64),    # 8 bytes (contient 34 bits utiles + CRC padding)
    ]

class PhoenixZPA:
    def __init__(self, filename="lichen_memory.zpa", size_mb=100):
        self.filename = filename
        self.size_bytes = size_mb * 1024 * 1024
        self.atom_capacity = self.size_bytes // ATOM_SIZE
        self.map = None
        self.file_obj = None
        
        # Initialisation du "Terreau" (Fichier mappé)
        self._init_storage()

    def _init_storage(self):
        """Crée ou ouvre le fichier et le mappe en mémoire (Ring 0 style simulation)"""
        is_new = not os.path.exists(self.filename)
        
        self.file_obj = open(self.filename, "a+b")
        if is_new:
            print(f"{Colors.OKBLUE}[ZPA] Initializing Empty Substrate ({self.size_bytes/1024/1024} MB)...{Colors.ENDC}")
            self.file_obj.truncate(self.size_bytes)
        
        # MMAP: Le disque DEVIENT la RAM.
        self.map = mmap.mmap(self.file_obj.fileno(), self.size_bytes)
        print(f"{Colors.OKGREEN}[ZPA] Memory Mapped via DMA emulation. Address Space Ready.{Colors.ENDC}")

    def _calculate_h_score(self, payload):
        """Simule le calcul d'harmonie basé sur la densité d'information"""
        entropy = len(set(payload)) / len(payload) if payload else 0
        # On booste artificiellement pour la démo si l'entropie est bonne
        return min(0.99, entropy * PHI)

    def write_atom(self, index, data_bytes, schema_type=0x01):
        """Écriture Zéro-Copie : On écrit directement dans la structure mappée."""
        if index >= self.atom_capacity:
            raise IndexError("Storage Full")

        # 1. Validation H-Scale (Filtre)
        h_score_val = self._calculate_h_score(data_bytes)
        if h_score_val < H_THRESHOLD:
            print(f"{Colors.FAIL}[REJECT] Entropy too low (H={h_score_val:.3f} < {H_THRESHOLD:.3f}){Colors.ENDC}")
            return False

        # 2. Calcul de l'adresse mémoire (Arithmétique de pointeur)
        offset = index * ATOM_SIZE
        
        # 3. Instanciation de la vue (Overlay)
        # On crée une instance C-struct qui pointe vers l'adresse mémoire du mmap
        atom = FC496Struct.from_buffer(self.map, offset)
        
        # 4. Remplissage (Direct Memory Access)
        atom.magic = MAGIC_SIG
        atom.pi_index = int(time.time() * 1000) # Pseudo-Pi time
        atom.geo_hash = 0xCAFEBABE # Mock GeoHash
        atom.schema = schema_type
        atom.h_score = int(h_score_val * 10000)
        atom.flags = 0b101010
        
        # Payload handling (Truncate/Pad to 32 bytes)
        clean_payload = data_bytes[:32].ljust(32, b'\0')
        atom.payload = clean_payload
        atom.strands = 0xDEADBEEF # Mock pointer
        
        return True

    def read_atom(self, index):
        """Lecture Zéro-Parse : On lit la structure sans la décoder."""
        offset = index * ATOM_SIZE
        # CASTING INSTANTANÉ : Pas de JSON.loads(), pas de parsing XML.
        # La donnée brute EST l'objet Python.
        atom = FC496Struct.from_buffer(self.map, offset)
        
        if atom.magic != MAGIC_SIG:
            return None # Atome vide ou corrompu
            
        return atom

    def close(self):
        self.map.close()
        self.file_obj.close()

# --- BENCHMARK COMPARATIF ---
def run_benchmark():
    print(f"\n{Colors.HEADER}--- PHOENIX-ZPA BENCHMARK PROTOCOL ---{Colors.ENDC}")
    zpa = PhoenixZPA()
    
    n_ops = 100_000
    dummy_data = b"Lichen Universe Semantic Payload V3"
    
    # 1. Test d'Écriture
    start = time.perf_counter()
    for i in range(n_ops):
        zpa.write_atom(i, dummy_data)
    end = time.perf_counter()
    write_time = end - start
    print(f"Write Speed: {n_ops / write_time:.0f} atoms/sec")

    # 2. Test de Lecture (ZPA vs JSON simulé)
    start = time.perf_counter()
    # Lecture ZPA (Pointeur)
    for i in range(0, n_ops, 100): # Sample
        atom = zpa.read_atom(i)
        _ = atom.payload # Accès
    end = time.perf_counter()
    zpa_time = end - start
    
    # Simulation JSON (Parsing overhead)
    import json
    json_str = json.dumps({"magic": 496, "payload": "Lichen Universe..."})
    start = time.perf_counter()
    for i in range(0, n_ops, 100):
        obj = json.loads(json_str) # Coût du parsing
        _ = obj["payload"]
    end = time.perf_counter()
    json_time = end - start
    
    print(f"\n{Colors.BOLD}RESULTS:{Colors.ENDC}")
    print(f"ZPA Access Time:  {zpa_time:.5f}s")
    print(f"JSON Parse Time:  {json_time:.5f}s")
    print(f"{Colors.OKGREEN}>>> SPEEDUP FACTOR: {json_time / zpa_time:.1f}x{Colors.ENDC}")
    
    zpa.close()
    
    # Nettoyage
    if os.path.exists("lichen_memory.zpa"):
        os.remove("lichen_memory.zpa")

if __name__ == "__main__":
    run_benchmark()
