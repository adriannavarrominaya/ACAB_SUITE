import hashlib
import os

def get_file_hash(path):
    with open(path, "rb") as f:
        # Lee el archivo en trozos para no saturar la RAM
        return hashlib.md5(f.read()).hexdigest()

folder_path = "examples"
print(f"Folder path: {folder_path}")
hashes_encontrados = {}
duplicados = []

for archivo in os.listdir(folder_path):
    ruta_completa = os.path.join(folder_path, archivo)
    if os.path.isfile(ruta_completa):
        file_hash = get_file_hash(ruta_completa)
        
        if file_hash in hashes_encontrados:
            duplicados.append(archivo)
        else:
            hashes_encontrados[file_hash] = archivo

print(f"Archivos únicos: {len(hashes_encontrados)}")
print(f"Archivos duplicados a descartar: {len(duplicados)}")
print(f"Lista de duplicados: {duplicados}")