#!/usr/bin/env python3
"""
Script para catalogar archivos FITS existentes que fueron descargados previamente.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Rutas
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
CATALOG_FILE = DATA_DIR / "downloaded_catalog.json"


def load_catalog():
    """Cargar el catálogo existente."""
    if CATALOG_FILE.exists():
        with open(CATALOG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_catalog(catalog):
    """Guardar el catálogo."""
    CATALOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CATALOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)


def catalog_directory(directory_path, telescope="HST", target="Unknown"):
    """Catalogar todos los archivos FITS en un directorio."""
    dir_path = Path(directory_path)
    
    if not dir_path.exists():
        print(f"❌ Directorio no encontrado: {directory_path}")
        return None
    
    # Buscar archivos FITS
    fits_files = list(dir_path.rglob("*.fits"))
    
    if not fits_files:
        print(f"⚠️  No se encontraron archivos FITS en {directory_path}")
        return None
    
    print(f"\n📁 Directorio: {directory_path}")
    print(f"   Encontrados: {len(fits_files)} archivos FITS")
    
    # Crear ID único
    dir_name = dir_path.name
    dataset_id = f"{telescope.lower()}_{dir_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Recopilar información de archivos
    file_list = []
    total_size = 0
    
    for fits_file in fits_files:
        size = fits_file.stat().st_size
        total_size += size
        
        # Ruta relativa desde BASE_DIR
        try:
            rel_path = fits_file.relative_to(BASE_DIR)
        except ValueError:
            rel_path = fits_file
        
        file_list.append({
            "name": fits_file.name,
            "path": str(rel_path),
            "size": size
        })
    
    # Crear entrada del catálogo
    dataset_entry = {
        "id": dataset_id,
        "name": f"{target} ({telescope})",
        "description": f"Observaciones de {target} del telescopio {telescope} (catalogado automáticamente)",
        "target": target,
        "telescope": telescope,
        "download_date": datetime.now().isoformat(),
        "file_count": len(file_list),
        "total_size": total_size,
        "files": file_list,
        "type": "mast_download"
    }
    
    return dataset_id, dataset_entry


def main():
    print("="*70)
    print("  CATALOGADOR DE ARCHIVOS FITS EXISTENTES")
    print("="*70)
    
    # Cargar catálogo existente
    catalog = load_catalog()
    print(f"\n📋 Catálogo actual: {len(catalog)} datasets")
    
    # Buscar directorios con archivos FITS
    print("\n🔍 Buscando directorios con archivos FITS...")
    
    # Buscar en data/hst/
    hst_dir = DATA_DIR / "hst"
    if hst_dir.exists():
        print(f"\n📂 Analizando: {hst_dir}")
        
        # Buscar subdirectorios
        subdirs = [d for d in hst_dir.iterdir() if d.is_dir()]
        
        if subdirs:
            for subdir in subdirs:
                fits_count = len(list(subdir.rglob("*.fits")))
                if fits_count > 0:
                    print(f"\n   📁 {subdir.name}: {fits_count} archivos FITS")
                    
                    # Preguntar al usuario
                    response = input(f"   ¿Catalogar este directorio? (s/n): ").strip().lower()
                    
                    if response == 's':
                        # Pedir información
                        target = input(f"   Nombre del objeto (ej: M16): ").strip() or "Unknown"
                        telescope = input(f"   Telescopio (ej: HST, JWST): ").strip() or "HST"
                        
                        # Catalogar
                        result = catalog_directory(subdir, telescope, target)
                        
                        if result:
                            dataset_id, dataset_entry = result
                            catalog[dataset_id] = dataset_entry
                            print(f"   ✅ Catalogado como: {dataset_id}")
        else:
            # Catalogar directamente data/hst si tiene archivos
            fits_count = len(list(hst_dir.rglob("*.fits")))
            if fits_count > 0:
                print(f"\n   📁 {hst_dir.name}: {fits_count} archivos FITS")
                response = input(f"   ¿Catalogar este directorio? (s/n): ").strip().lower()
                
                if response == 's':
                    target = input(f"   Nombre del objeto (ej: M16): ").strip() or "Unknown"
                    telescope = input(f"   Telescopio (ej: HST, JWST): ").strip() or "HST"
                    
                    result = catalog_directory(hst_dir, telescope, target)
                    
                    if result:
                        dataset_id, dataset_entry = result
                        catalog[dataset_id] = dataset_entry
                        print(f"   ✅ Catalogado como: {dataset_id}")
    
    # Guardar catálogo actualizado
    if len(catalog) > 0:
        save_catalog(catalog)
        print(f"\n{'='*70}")
        print(f"  ✅ CATÁLOGO ACTUALIZADO")
        print(f"{'='*70}")
        print(f"\nTotal de datasets: {len(catalog)}")
        print(f"Archivo: {CATALOG_FILE}")
        print("\n💡 Ahora puedes ver tus datasets en: http://localhost:5000/datasets")
    else:
        print("\n⚠️  No se catalogó ningún dataset")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
