#!/usr/bin/env python3
"""
Descargador de archivos FITS desde MAST (Mikulski Archive for Space Telescopes)
Permite descargar observaciones de Hubble, JWST, y otros telescopios espaciales.
"""

import argparse
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime

try:
    from astroquery.mast import Observations
except ImportError:
    print("❌ Error: astroquery no está instalado")
    print("\nPara instalar, ejecuta:")
    print("  pip install astroquery")
    print("\nO con conda:")
    print("  conda install -c conda-forge astroquery")
    sys.exit(1)

# Catálogo de datasets descargados
CATALOG_FILE = Path(__file__).parent.parent / "data" / "downloaded_catalog.json"


def load_catalog():
    """Cargar el catálogo de datasets descargados."""
    if CATALOG_FILE.exists():
        with open(CATALOG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_catalog(catalog):
    """Guardar el catálogo de datasets descargados."""
    CATALOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CATALOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)


def move_files_from_subdirs(base_dir):
    """
    Mover archivos FITS de subcarpetas a la carpeta principal.
    Estructura típica de MAST: base_dir/mastDownload/MISSION/obs_id/file.fits
    """
    base_path = Path(base_dir)
    moved_files = []
    
    # Buscar todos los archivos FITS en subdirectorios
    for fits_file in base_path.rglob("*.fits"):
        # Si el archivo ya está en la raíz, saltarlo
        if fits_file.parent == base_path:
            continue
        
        # Crear nombre único si hay conflicto
        dest_file = base_path / fits_file.name
        counter = 1
        while dest_file.exists():
            stem = fits_file.stem
            suffix = fits_file.suffix
            dest_file = base_path / f"{stem}_{counter}{suffix}"
            counter += 1
        
        # Mover archivo
        try:
            shutil.move(str(fits_file), str(dest_file))
            moved_files.append(dest_file)
            print(f"  ✓ Movido: {fits_file.name} → {dest_file.name}")
        except Exception as e:
            print(f"  ⚠️  Error moviendo {fits_file.name}: {e}")
    
    # Limpiar directorios vacíos
    for subdir in base_path.rglob("*"):
        if subdir.is_dir() and not any(subdir.iterdir()):
            try:
                subdir.rmdir()
            except:
                pass
    
    return moved_files


def generate_mosaic(fits_files, output_path):
    """Generar mosaico a partir de archivos FITS."""
    try:
        from PIL import Image
        import numpy as np
        from astropy.io import fits as astropy_fits
        
        print(f"\n🎨 Generando mosaico...")
        
        # Ordenar archivos por nombre para mantener consistencia
        sorted_files = sorted(fits_files, key=lambda x: x.name)
        
        images = []
        for fits_file in sorted_files[:10]:  # Limitar a 10 para no sobrecargar
            try:
                with astropy_fits.open(fits_file) as hdul:
                    # Buscar datos de imagen
                    data = None
                    for hdu in hdul:
                        if hasattr(hdu, 'data') and hdu.data is not None and len(hdu.data.shape) >= 2:
                            data = hdu.data
                            break
                    
                    if data is not None:
                        # Limpiar datos
                        data = np.nan_to_num(data, nan=0.0, posinf=0.0, neginf=0.0)
                        
                        # Normalización simple y robusta
                        if np.max(data) > np.min(data):
                            # Usar percentiles para evitar outliers extremos
                            vmin = np.percentile(data, 2)
                            vmax = np.percentile(data, 98)
                            
                            # Clip y normalizar
                            data = np.clip(data, vmin, vmax)
                            data = (data - vmin) / (vmax - vmin)
                        else:
                            data = np.zeros_like(data)
                        
                        # Convertir a 8-bit
                        data = (data * 255).astype(np.uint8)
                        
                        # Convertir a imagen PIL
                        img = Image.fromarray(data)
                        images.append(img)
                        print(f"  ✓ Procesado: {fits_file.name}")
            except Exception as e:
                print(f"  ⚠️  Error procesando {fits_file.name}: {e}")
        
        if not images:
            print("  ❌ No se pudieron procesar imágenes")
            return None
        
        # Determinar el mejor layout para el grid
        num_images = len(images)
        
        # Calcular dimensiones del grid (intentar hacer un grid más cuadrado)
        if num_images <= 4:
            cols = 2
            rows = (num_images + 1) // 2
        elif num_images <= 9:
            cols = 3
            rows = (num_images + 2) // 3
        else:
            cols = 4
            rows = (num_images + 3) // 4
        
        # Redimensionar todas las imágenes al mismo tamaño para uniformidad
        target_size = (800, 800)  # Tamaño estándar
        border_size = 5  # Borde entre imágenes
        
        resized_images = []
        for img in images:
            # Mantener aspect ratio
            img.thumbnail(target_size, Image.Resampling.LANCZOS)
            # Crear imagen con padding para que todas sean del mismo tamaño
            padded = Image.new('L', target_size, 0)
            offset = ((target_size[0] - img.width) // 2, (target_size[1] - img.height) // 2)
            padded.paste(img, offset)
            resized_images.append(padded)
        
        # Crear mosaico con bordes
        cell_width = target_size[0] + border_size
        cell_height = target_size[1] + border_size
        mosaic_width = cols * cell_width + border_size
        mosaic_height = rows * cell_height + border_size
        
        # Fondo gris oscuro para los bordes
        mosaic = Image.new('L', (mosaic_width, mosaic_height), 20)
        
        for idx, img in enumerate(resized_images):
            row = idx // cols
            col = idx % cols
            x = col * cell_width + border_size
            y = row * cell_height + border_size
            mosaic.paste(img, (x, y))
        
        # Guardar
        mosaic.save(output_path, quality=95)
        print(f"  ✓ Mosaico guardado: {output_path}")
        print(f"  📐 Dimensiones: {mosaic_width}x{mosaic_height}")
        
        return output_path
        
    except ImportError as e:
        print(f"  ⚠️  Falta dependencia para generar mosaico: {e}")
        print(f"  💡 Instala: pip install astropy")
        return None
    except Exception as e:
        print(f"  ❌ Error generando mosaico: {e}")
        return None


def create_manifest(dataset_dir, target, telescope, files):
    """Crear archivo manifest.json en el directorio del dataset."""
    manifest = {
        "target": target,
        "telescope": telescope,
        "download_date": datetime.now().isoformat(),
        "file_count": len(files),
        "files": []
    }
    
    total_size = 0
    for file_path in files:
        if file_path.exists():
            size = file_path.stat().st_size
            total_size += size
            manifest["files"].append({
                "name": file_path.name,
                "size": size,
                "path": str(file_path.name)
            })
    
    manifest["total_size"] = total_size
    
    # Guardar manifest
    manifest_path = dataset_dir / "manifest.json"
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Manifest creado: {manifest_path}")
    return manifest


def add_to_catalog(target, telescope, dataset_dir, mosaic_path=None):
    """Agregar dataset al catálogo."""
    catalog = load_catalog()
    
    # Crear ID único para este dataset
    dataset_id = f"{telescope.lower()}_{target.replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Leer manifest
    manifest_path = dataset_dir / "manifest.json"
    if manifest_path.exists():
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
    else:
        manifest = {"file_count": 0, "total_size": 0, "files": []}
    
    # Crear entrada en el catálogo
    catalog[dataset_id] = {
        "id": dataset_id,
        "name": f"{target} ({telescope})",
        "description": f"Observaciones de {target} del telescopio {telescope}",
        "target": target,
        "telescope": telescope,
        "download_date": datetime.now().isoformat(),
        "file_count": manifest["file_count"],
        "total_size": manifest["total_size"],
        "dataset_dir": str(dataset_dir.relative_to(Path(__file__).parent.parent)),
        "mosaic_path": str(mosaic_path.relative_to(Path(__file__).parent.parent)) if mosaic_path and mosaic_path.exists() else None,
        "type": "mast_download"
    }
    
    save_catalog(catalog)
    print(f"\n✓ Dataset catalogado: {dataset_id}")
    return dataset_id


def search_and_download(
    target="M16",
    telescope="HST",
    radius="0.05 deg",
    max_files=10,
    output_dir="data/hst",
    product_type="SCIENCE"
):
    """
    Busca y descarga archivos FITS de MAST.
    
    Args:
        target: Nombre del objeto astronómico (ej: "M16", "NGC 3372")
        telescope: Telescopio (HST, JWST, TESS, etc.)
        radius: Radio de búsqueda
        max_files: Número máximo de archivos a descargar
        output_dir: Directorio de salida
        product_type: Tipo de producto (SCIENCE, PREVIEW, etc.)
    """
    
    print(f"\n{'='*70}")
    print(f"  DESCARGANDO DATOS DE MAST")
    print(f"{'='*70}\n")
    print(f"  Objetivo: {target}")
    print(f"  Telescopio: {telescope}")
    print(f"  Radio de búsqueda: {radius}")
    print(f"  Máximo de archivos: {max_files}")
    print()
    
    # Buscar observaciones
    print(f"  Buscando observaciones de {target}...")
    try:
        obs_table = Observations.query_object(target, radius=radius)
    except Exception as e:
        print(f"  Error al buscar observaciones: {e}")
        return False
    
    if len(obs_table) == 0:
        print(f"  No se encontraron observaciones para {target}")
        return False
    
    print(f"  Se encontraron {len(obs_table)} observaciones totales")
    
    # Filtrar por telescopio
    obs_filtered = obs_table[obs_table['obs_collection'] == telescope]
    
    if len(obs_filtered) == 0:
        print(f"  No se encontraron observaciones de {telescope}")
        print(f"\nTelescopios disponibles:")
        unique_telescopes = set(obs_table['obs_collection'])
        for tel in sorted(unique_telescopes):
            count = len(obs_table[obs_table['obs_collection'] == tel])
            print(f"    - {tel}: {count} observaciones")
        return False
    
    print(f"  Se encontraron {len(obs_filtered)} observaciones de {telescope}")
    
    # Obtener lista de productos
    print(f"\n  Obteniendo lista de productos...")
    try:
        products = Observations.get_product_list(obs_filtered)
    except Exception as e:
        print(f"  Error al obtener productos: {e}")
        return False
    
    print(f"  Se encontraron {len(products)} productos totales")
    
    # Filtrar solo archivos FITS de tipo SCIENCE
    print(f"\n  Filtrando archivos FITS de tipo {product_type}...")
    fits_products = Observations.filter_products(
        products,
        productType=product_type,
        mrp_only=False
    )
    
    # Filtrar por extensión .fits
    fits_mask = [fn.lower().endswith(".fits") for fn in fits_products["productFilename"]]
    fits_products = fits_products[fits_mask]
    
    if len(fits_products) == 0:
        print(f"  No se encontraron archivos FITS")
        return False
    
    print(f"  Se encontraron {len(fits_products)} archivos FITS")
    
    # Limitar cantidad de archivos
    files_to_download = min(max_files, len(fits_products))
    fits_products = fits_products[:files_to_download]
    
    print(f"\n  Descargando {files_to_download} archivos...")
    print(f"    Destino: {output_dir}")
    print()
    
    # Crear directorio de salida
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Descargar
    try:
        manifest = Observations.download_products(
            fits_products,
            mrp_only=False,
            download_dir=output_dir
        )
        
        print(f"\n{'='*70}")
        print(f"  ✓ DESCARGA COMPLETADA")
        print(f"{'='*70}\n")
        print(f"Archivos descargados: {len(manifest)}")
        print(f"Ubicación: {output_dir}")
        print()
        
        # Mostrar lista de archivos descargados
        print("Archivos:")
        for row in manifest[:10]:  # Mostrar primeros 10
            print(f"  - {row['Local Path']}")
        
        if len(manifest) > 10:
            print(f"  ... y {len(manifest) - 10} más")
        
        # Crear carpeta específica para este dataset
        dataset_name = f"{telescope}_{target.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        dataset_dir = Path(output_dir).parent / "datasets" / dataset_name
        dataset_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\n  Organizando archivos en: {dataset_dir}")
        
        # Mover archivos de subcarpetas a la carpeta del dataset
        moved_files = move_files_from_subdirs(output_dir)
        
        # Mover archivos a la carpeta del dataset
        final_files = []
        for fits_file in moved_files:
            dest_file = dataset_dir / fits_file.name
            if fits_file.exists():
                shutil.move(str(fits_file), str(dest_file))
                final_files.append(dest_file)
        
        print(f"  {len(final_files)} archivos organizados")
        
        # Crear manifest
        print(f"\n  Creando manifest...")
        create_manifest(dataset_dir, target, telescope, final_files)
        
        # Generar mosaico
        mosaic_path = dataset_dir / "mosaic.png"
        mosaic_result = generate_mosaic(final_files, mosaic_path)
        
        # Catalogar el dataset
        print(f"\n  Catalogando dataset...")
        add_to_catalog(target, telescope, dataset_dir, mosaic_result)
        
        # Limpiar directorio temporal de descarga
        try:
            if Path(output_dir).exists():
                shutil.rmtree(output_dir)
        except:
            pass
        
        return True
        
    except Exception as e:
        print(f"\n  Error durante la descarga: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="Descargador de archivos FITS desde MAST",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Descargar 10 archivos FITS de M16 (Hubble)
  python download_mast_files.py --target M16 --telescope HST --max-files 10
  
  # Descargar observaciones de JWST de la Nebulosa de Carina
  python download_mast_files.py --target "NGC 3372" --telescope JWST --max-files 5
  
  # Buscar en un radio mayor
  python download_mast_files.py --target M16 --radius "0.1 deg" --max-files 20
  
Objetos populares:
  - M16: Nebulosa del Águila (Pilares de la Creación)
  - NGC 3372: Nebulosa de Carina
  - M42: Nebulosa de Orión
  - NGC 7293: Nebulosa de la Hélice
  - M1: Nebulosa del Cangrejo
        """
    )
    
    parser.add_argument('--target', default='M16',
                       help='Nombre del objeto astronómico (default: M16)')
    parser.add_argument('--telescope', default='HST',
                       help='Telescopio: HST, JWST, TESS, etc. (default: HST)')
    parser.add_argument('--radius', default='0.05 deg',
                       help='Radio de búsqueda (default: 0.05 deg)')
    parser.add_argument('--max-files', type=int, default=10,
                       help='Número máximo de archivos a descargar (default: 10)')
    parser.add_argument('--output', default='data/hst',
                       help='Directorio de salida (default: data/hst)')
    parser.add_argument('--product-type', default='SCIENCE',
                       help='Tipo de producto: SCIENCE, PREVIEW, etc. (default: SCIENCE)')
    
    args = parser.parse_args()
    
    success = search_and_download(
        target=args.target,
        telescope=args.telescope,
        radius=args.radius,
        max_files=args.max_files,
        output_dir=args.output,
        product_type=args.product_type
    )
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
