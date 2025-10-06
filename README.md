# 🌌 Cosmic Lens - FITS Image Viewer

An interactive web-based viewer for astronomical FITS images with zoom, pan, and dataset management capabilities. Download real observations from Hubble, JWST, and other space telescopes directly from MAST.

---

## 🚀 Quick Start

### Requirements
- **Python 3.8+** → [Download here](https://www.python.org/downloads/)
  - ⚠️ **IMPORTANT**: Check **"Add Python to PATH"** during installation

### Installation (2 steps)

#### 1. Install Dependencies
```bash
# Windows
INSTALAR.bat

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### 2. Start the Server
```bash
# Windows
INICIAR.bat

# macOS/Linux
python app.py
```

Open your browser at: **http://localhost:5000**

---

## 📖 Features

### 🔭 Download Datasets from MAST
- Download real observations from Hubble, JWST, and other space telescopes
- Automatic organization and cataloging
- Automatic mosaic generation
- Web-based interface (no terminal required)

### 🖼️ Image Viewer
- **Zoom**: Mouse wheel or +/- buttons
- **Pan**: Click and drag
- **Brightness**: Adjustable slider
- **Labels**: Add markers to images

### 📦 Dataset Management
- View all downloaded datasets
- Load datasets with one click
- Delete datasets
- Automatic mosaic preview

---

## 🎯 How to Use

### Method 1: Download from Web (Easiest)
1. Click **"🌌 Datasets"**
2. Click **"🔭 Download New Dataset"**
3. Fill the form:
   - Astronomical object (e.g., M16, NGC 3372)
   - Telescope (HST or JWST)
   - Number of files (5-15 recommended)
4. Click **"📥 Download and Generate Mosaic"**
5. Wait for download to complete
6. Click **"👁️ View in Viewer"**

### Method 2: Upload Image
1. Click **"📤 Upload"** button
2. Select your FITS or image file
3. Done!

### Method 3: Manual Copy
1. Copy your FITS files to the `data/` folder
2. Reload the page (F5)

---

## 🛠️ Advanced Usage

### Download from Terminal
```bash
python scripts/download_mast_files.py --target M16 --telescope HST --max-files 10
```

### Regenerate Mosaic
```bash
python scripts/regenerate_mosaic.py
```

### Clean Project
```bash
python limpiar.py
```

---

## 📁 Project Structure

```
Cosmic-Lens/
├── app.py                      # Main Flask application
├── requirements.txt            # Python dependencies
├── INICIAR.bat                # Start script (Windows)
├── INSTALAR.bat               # Install script (Windows)
├── limpiar.py                 # Cleanup script
├── .gitignore                 # Git ignore rules
├── data/                      # Image data folder
│   └── datasets/              # Downloaded datasets
├── scripts/                   # Utility scripts
│   ├── download_mast_files.py # Download from MAST
│   └── regenerate_mosaic.py   # Regenerate mosaics
├── static/                    # CSS and JavaScript
│   ├── style.css
│   └── viewer.js
└── templates/                 # HTML templates
    ├── index.html             # Main viewer
    ├── datasets.html          # Dataset catalog
    ├── upload.html            # Upload interface
    └── download_mast.html     # MAST download form
```

---

## 🌟 Popular Astronomical Objects

- **M16** - Eagle Nebula (Pillars of Creation)
- **NGC 3372** - Carina Nebula
- **M42** - Orion Nebula
- **NGC 7293** - Helix Nebula
- **M1** - Crab Nebula
- **M31** - Andromeda Galaxy
- **NGC 6543** - Cat's Eye Nebula

---

## 📦 Dependencies

- Flask - Web framework
- Pillow - Image processing
- NumPy - Numerical operations
- Astropy - FITS file handling
- Astroquery - MAST API access

---

## 🐛 Troubleshooting

### Server won't start
- Make sure Python is installed and in PATH
- Run `INSTALAR.bat` again
- Check if port 5000 is available

### Download fails
- Check internet connection
- Try with fewer files (5-10)
- Some objects may not have data available

### Mosaic looks wrong
- Regenerate with: `python scripts/regenerate_mosaic.py`
- Try downloading fewer files

---

## 📝 License

This project is open source and available for educational purposes.

---

## 🤝 Contributing

Contributions are welcome! Feel free to submit issues and pull requests.

---

## 📧 Support

For issues and questions, please open an issue on the repository.
