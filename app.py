from math import ceil, log2
import shutil
import io
import os
import json
from pathlib import Path

from flask import (
    Flask,
    render_template,
    send_file,
    request,
    jsonify,
    redirect,
    url_for,
    flash,
)

from PIL import Image, ImageDraw

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
TILE_CACHE = BASE_DIR / "tiles"
LABELS_FILE = DATA_DIR / "labels.json"

TILE_SIZE = 256

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size


def ensure_dirs():
    DATA_DIR.mkdir(exist_ok=True)
    TILE_CACHE.mkdir(exist_ok=True)
    (TILE_CACHE / "tmp").mkdir(exist_ok=True)


def create_demo_image(path: Path, size=(8192, 8192)):
    # Create a synthetic large image: radial gradients and labeled features
    print(f"Creating demo image at {path} ({size[0]}x{size[1]})")
    img = Image.new("RGB", size, "black")
    draw = ImageDraw.Draw(img)
    w, h = size

    # Draw concentric colored circles to create features
    for i in range(0, max(w, h) // 100, 1):
        r = int((i / (max(w, h) / 100)) * max(w, h) / 2)
        bbox = [w//2 - r, h//2 - r, w//2 + r, h//2 + r]
        color = (int(128 + 127 * (i % 2)), int(64 + i * 3) % 256, int(200 - i) % 256)
        draw.ellipse(bbox, outline=color)

    # Add some bright spots (simulating craters/features)
    import random

    random.seed(0)
    for _ in range(60):
        x = random.randint(0, w - 1)
        y = random.randint(0, h - 1)
        r = random.randint(20, 200)
        bbox = [x - r, y - r, x + r, y + r]
        draw.ellipse(bbox, fill=(random.randint(120, 255), random.randint(120, 255), random.randint(120, 255)))

    img.save(path, "PNG", quality=85)


def find_latest_image():
    """Find the most recent image in the data directory."""
    ensure_dirs()
    supported_formats = ['.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp']
    images = []
    for ext in supported_formats:
        images.extend(DATA_DIR.glob(f'*{ext}'))
        images.extend(DATA_DIR.glob(f'*{ext.upper()}'))
    
    if images:
        # Return the most recently modified image
        return max(images, key=lambda p: p.stat().st_mtime)
    return None


def load_image():
    ensure_dirs()
    # Try to find any existing image first
    img_path = find_latest_image()
    
    if img_path is None:
        # Create demo image if no images exist
        demo_path = DATA_DIR / "demo.png"
        create_demo_image(demo_path)
        img_path = demo_path
    
    print(f"Loading image: {img_path}")
    img = Image.open(img_path).convert("RGB")
    return img


IMAGE = None
MAX_ZOOM = None


def init():
    global IMAGE, MAX_ZOOM
    IMAGE = load_image()
    max_dim = max(IMAGE.width, IMAGE.height)
    MAX_ZOOM = max(0, int(ceil(log2(max_dim / TILE_SIZE))))
    print(f"Image loaded: {IMAGE.width}x{IMAGE.height}, MAX_ZOOM={MAX_ZOOM}")


def tile_path(z, x, y):
    d = TILE_CACHE / str(z)
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{x}_{y}.png"


def make_tile(z: int, x: int, y: int):
    """
    Create a tile for zoom level z and tile coordinates (x, y).
    Zoom definition: z in [0..MAX_ZOOM], where MAX_ZOOM is the highest-resolution level.
    At level z, each tile covers TILE_SIZE * scale pixels of the source image, where scale = 2^(MAX_ZOOM - z)
    """
    global IMAGE, MAX_ZOOM
    if IMAGE is None:
        init()

    scale = 2 ** (MAX_ZOOM - z)
    src_tile_px = int(TILE_SIZE * scale)

    left = int(x * src_tile_px)
    top = int(y * src_tile_px)
    right = left + src_tile_px
    bottom = top + src_tile_px

    # If the requested tile is completely outside the image, return a blank tile
    if left >= IMAGE.width or top >= IMAGE.height or right <= 0 or bottom <= 0:
        blank = Image.new("RGB", (TILE_SIZE, TILE_SIZE), (0, 0, 0))
        bio = io.BytesIO()
        blank.save(bio, "PNG")
        bio.seek(0)
        return bio

    # Clamp crop to image bounds
    cl_left = max(0, left)
    cl_top = max(0, top)
    cl_right = min(IMAGE.width, right)
    cl_bottom = min(IMAGE.height, bottom)

    # If after clamping there's nothing to crop, return blank
    if cl_right <= cl_left or cl_bottom <= cl_top:
        blank = Image.new("RGB", (TILE_SIZE, TILE_SIZE), (0, 0, 0))
        bio = io.BytesIO()
        blank.save(bio, "PNG")
        bio.seek(0)
        return bio

    # Create source-sized tile and paste the cropped region into the correct offset
    src_tile = Image.new("RGB", (src_tile_px, src_tile_px), (0, 0, 0))
    region = IMAGE.crop((cl_left, cl_top, cl_right, cl_bottom))
    paste_x = int(cl_left - left)
    paste_y = int(cl_top - top)
    src_tile.paste(region, (paste_x, paste_y))

    # Resize down to TILE_SIZE for client consumption
    tile = src_tile.resize((TILE_SIZE, TILE_SIZE), Image.LANCZOS)
    bio = io.BytesIO()
    tile.save(bio, "PNG")
    bio.seek(0)
    return bio


@app.route("/")
def index():
    # Provide image metadata
    if IMAGE is None:
        init()
    meta = {
        "width": IMAGE.width,
        "height": IMAGE.height,
        "tile_size": TILE_SIZE,
        "max_zoom": MAX_ZOOM,
    }
    return render_template("index.html", meta=meta)


@app.route("/tiles/<int:z>/<int:x>/<int:y>.png")
def tiles(z, x, y):
    if IMAGE is None:
        init()
    # Basic bounds check: if requested tile outside image bounds, still return a blank tile
    p = tile_path(z, x, y)
    if p.exists():
        resp = send_file(str(p), mimetype="image/png")
        # prevent aggressive browser caching so uploads/changes appear immediately
        resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        resp.headers['Pragma'] = 'no-cache'
        resp.headers['Expires'] = '0'
        return resp

    bio = make_tile(z, x, y)
    # cache
    with open(p, "wb") as f:
        f.write(bio.getbuffer())
    bio.seek(0)
    resp = send_file(bio, mimetype="image/png")
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp


@app.route("/labels", methods=["GET", "POST"])
def labels():
    ensure_dirs()
    if request.method == "GET":
        if LABELS_FILE.exists():
            return send_file(str(LABELS_FILE), mimetype="application/json")
        return jsonify([])

    data = request.get_json() or {}
    # Expect {x: float, y: float, zoom: int, text: str}
    labels = []
    if LABELS_FILE.exists():
        with open(LABELS_FILE, "r", encoding="utf8") as f:
            try:
                labels = json.load(f)
            except Exception:
                labels = []

    labels.append(data)
    with open(LABELS_FILE, "w", encoding="utf8") as f:
        json.dump(labels, f, indent=2)
    return jsonify({"ok": True})


@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "GET":
        return render_template("upload.html")
    
    if 'file' not in request.files:
        flash('No file selected')
        return redirect(url_for('upload'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected')
        return redirect(url_for('upload'))
    
    if file:
        # Save the uploaded file
        filename = Path(file.filename).name
        filepath = DATA_DIR / filename
        file.save(str(filepath))
        
        # Clear tile cache to regenerate tiles for new image
        clear_tile_cache()
        
        # Reload the image
        global IMAGE, MAX_ZOOM
        IMAGE = None
        init()
        
        flash(f'Image "{filename}" uploaded successfully!')
        return redirect(url_for('index'))
    
    return redirect(url_for('upload'))


@app.route("/datasets")
def datasets():
    """Show available datasets for download."""
    # Cargar catálogo de datasets descargados localmente
    local_catalog = {}
    catalog_file = DATA_DIR / "downloaded_catalog.json"
    if catalog_file.exists():
        try:
            with open(catalog_file, 'r', encoding='utf-8') as f:
                local_catalog = json.load(f)
        except Exception as e:
            print(f"Error loading local catalog: {e}")
    
    return render_template("datasets.html", 
                         local_datasets=local_catalog)




@app.route("/load-local-dataset/<dataset_id>")
def load_local_dataset(dataset_id):
    """Load a locally downloaded dataset."""
    global IMAGE, MAX_ZOOM
    
    try:
        catalog_file = DATA_DIR / "downloaded_catalog.json"
        if not catalog_file.exists():
            return jsonify({"error": "Catálogo no encontrado"}), 404
        
        with open(catalog_file, 'r', encoding='utf-8') as f:
            catalog = json.load(f)
        
        if dataset_id not in catalog:
            return jsonify({"error": "Dataset no encontrado"}), 404
        
        dataset = catalog[dataset_id]
        
        # Priorizar mosaico si existe
        if dataset.get('mosaic_path'):
            mosaic_path = BASE_DIR / dataset['mosaic_path']
            if mosaic_path.exists():
                # Copiar mosaico a data/
                dest_path = DATA_DIR / mosaic_path.name
                if not dest_path.exists():
                    shutil.copy(str(mosaic_path), str(dest_path))
                
                # Clear cache and reload
                clear_tile_cache()
                IMAGE = None
                init()
                
                return jsonify({
                    "success": True,
                    "message": f"Mosaico de '{dataset['name']}' cargado exitosamente",
                    "filename": mosaic_path.name
                })
        
        # Si no hay mosaico, intentar cargar el primer FITS
        if dataset.get('dataset_dir'):
            dataset_dir = BASE_DIR / dataset['dataset_dir']
            fits_files = list(dataset_dir.glob("*.fits"))
            if fits_files:
                # Copiar primer archivo
                dest_path = DATA_DIR / fits_files[0].name
                if not dest_path.exists():
                    shutil.copy(str(fits_files[0]), str(dest_path))
                
                # Clear cache and reload
                clear_tile_cache()
                IMAGE = None
                init()
                
                return jsonify({
                    "success": True,
                    "message": f"Dataset '{dataset['name']}' cargado exitosamente",
                    "filename": fits_files[0].name
                })
        
        return jsonify({"error": "No se encontraron archivos para cargar"}), 404
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/download-from-mast", methods=["GET", "POST"])
def download_from_mast():
    """Download datasets from MAST."""
    if request.method == "GET":
        return render_template("download_mast.html")
    
    # POST - iniciar descarga
    try:
        data = request.get_json()
        target = data.get('target', 'M16')
        telescope = data.get('telescope', 'HST')
        max_files = int(data.get('max_files', 10))
        
        print(f"\n{'='*70}")
        print(f"Iniciando descarga desde web:")
        print(f"  Target: {target}")
        print(f"  Telescope: {telescope}")
        print(f"  Max files: {max_files}")
        print(f"{'='*70}\n")
        
        # Importar la función de descarga
        import sys
        sys.path.insert(0, str(BASE_DIR / 'scripts'))
        
        try:
            from download_mast_files import search_and_download
        except ImportError as e:
            print(f"Error importando módulo: {e}")
            return jsonify({
                "success": False,
                "error": f"Error al importar módulo: {str(e)}"
            }), 500
        
        # Ejecutar descarga con parámetros simplificados
        output_dir = str(DATA_DIR / "hst_temp")
        
        try:
            # Ejecutar descarga
            success = search_and_download(
                target=target,
                telescope=telescope,
                radius="0.05 deg",  # Fijo
                max_files=max_files,
                output_dir=output_dir,
                product_type="SCIENCE"  # Fijo
            )
            
            if success:
                print(f"\n✅ Descarga completada exitosamente\n")
                return jsonify({
                    "success": True,
                    "message": f"Dataset de {target} descargado exitosamente"
                })
            else:
                print(f"\n❌ Descarga falló\n")
                return jsonify({
                    "success": False,
                    "error": "Error al descargar el dataset"
                }), 500
        
        except Exception as download_error:
            print(f"\n❌ Error durante descarga: {download_error}\n")
            import traceback
            traceback.print_exc()
            return jsonify({
                "success": False,
                "error": f"Error durante descarga: {str(download_error)}"
            }), 500
    
    except Exception as e:
        print(f"\n❌ Error general: {e}\n")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"Error: {str(e)}"
        }), 500


@app.route("/delete-dataset/<dataset_id>", methods=["DELETE"])
def delete_dataset(dataset_id):
    """Delete a dataset."""
    try:
        catalog_file = DATA_DIR / "downloaded_catalog.json"
        if not catalog_file.exists():
            return jsonify({"error": "Catálogo no encontrado"}), 404
        
        with open(catalog_file, 'r', encoding='utf-8') as f:
            catalog = json.load(f)
        
        if dataset_id not in catalog:
            return jsonify({"error": "Dataset no encontrado"}), 404
        
        dataset = catalog[dataset_id]
        
        # Eliminar directorio del dataset
        if "dataset_dir" in dataset:
            dataset_path = BASE_DIR / dataset["dataset_dir"]
            if dataset_path.exists():
                shutil.rmtree(dataset_path)
                print(f"Deleted dataset directory: {dataset_path}")
        
        # Eliminar del catálogo
        del catalog[dataset_id]
        
        # Guardar catálogo actualizado
        with open(catalog_file, 'w', encoding='utf-8') as f:
            json.dump(catalog, f, indent=2, ensure_ascii=False)
        
        return jsonify({
            "success": True,
            "message": f"Dataset eliminado exitosamente"
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/reload")
def reload_image():
    """Reload the current image and clear cache."""
    global IMAGE, MAX_ZOOM
    clear_tile_cache()
    IMAGE = None
    init()
    return jsonify({"ok": True, "message": "Image reloaded"})


def clear_tile_cache():
    """Clear all cached tiles."""
    if TILE_CACHE.exists():
        for item in TILE_CACHE.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            elif item.is_file():
                item.unlink()
    ensure_dirs()


if __name__ == "__main__":
    init()
    app.run(debug=True, host="0.0.0.0", port=5000)
