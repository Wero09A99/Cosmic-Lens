#!/usr/bin/env python3
"""
Script para regenerar el mosaico de un dataset existente.
"""

import sys
import json
from pathlib import Path

# Agregar el directorio de scripts al path
sys.path.insert(0, str(Path(__file__).parent))
from download_mast_files import generate_mosaic, save_catalog, load_catalog

BASE_DIR = Path(__file__).parent.parent
CATALOG_FILE = BASE_DIR / "data" / "downloaded_catalog.json"


def regenerate_mosaic(dataset_id):
    """Regenerar el mosaico de un dataset."""
    # Cargar catálogo
    catalog = load_catalog()
    
    if dataset_id not in catalog:
        print(f"❌ Dataset '{dataset_id}' no encontrado")
        return False
    
    dataset = catalog[dataset_id]
    
    # Obtener directorio del dataset
    if "dataset_dir" not in dataset:
        print(f"❌ Dataset no tiene directorio")
        return False
    
    dataset_dir = BASE_DIR / dataset["dataset_dir"]
    
    if not dataset_dir.exists():
        print(f"❌ Directorio no encontrado: {dataset_dir}")
        return False
    
    # Buscar archivos FITS
    fits_files = sorted(dataset_dir.glob("*.fits"))
    
    if not fits_files:
        print(f"❌ No se encontraron archivos FITS en {dataset_dir}")
        return False
    
    print(f"\n🔄 Regenerando mosaico para: {dataset['name']}")
    print(f"   Archivos encontrados: {len(fits_files)}")
    
    # Generar nuevo mosaico
    mosaic_path = dataset_dir / "mosaic.png"
    result = generate_mosaic(fits_files, mosaic_path)
    
    if result:
        # Actualizar catálogo
        catalog[dataset_id]["mosaic_path"] = str(mosaic_path.relative_to(BASE_DIR))
        save_catalog(catalog)
        print(f"\n✅ Mosaico regenerado exitosamente")
        return True
    else:
        print(f"\n❌ Error al generar mosaico")
        return False


def main():
    print("="*70)
    print("  REGENERADOR DE MOSAICOS")
    print("="*70)
    
    # Cargar catálogo
    catalog = load_catalog()
    
    if not catalog:
        print("\n❌ No hay datasets en el catálogo")
        return 1
    
    # Mostrar datasets disponibles
    print(f"\n📋 Datasets disponibles:\n")
    for idx, (dataset_id, dataset) in enumerate(catalog.items(), 1):
        print(f"{idx}. {dataset['name']}")
        print(f"   ID: {dataset_id}")
        print(f"   Archivos: {dataset.get('file_count', 0)}")
        print()
    
    # Preguntar cuál regenerar
    choice = input("Selecciona el número del dataset (o 'all' para todos): ").strip().lower()
    
    if choice == 'all':
        success_count = 0
        for dataset_id in catalog.keys():
            if regenerate_mosaic(dataset_id):
                success_count += 1
        
        print(f"\n{'='*70}")
        print(f"  ✅ {success_count}/{len(catalog)} mosaicos regenerados")
        print(f"{'='*70}")
    else:
        try:
            idx = int(choice)
            dataset_ids = list(catalog.keys())
            if 1 <= idx <= len(dataset_ids):
                dataset_id = dataset_ids[idx - 1]
                regenerate_mosaic(dataset_id)
            else:
                print("❌ Número inválido")
                return 1
        except ValueError:
            print("❌ Entrada inválida")
            return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
