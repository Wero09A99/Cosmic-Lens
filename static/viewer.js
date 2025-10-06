const viewer = document.getElementById('viewer');
const canvas = document.createElement('canvas');
const ctx = canvas.getContext('2d');
viewer.appendChild(canvas);

const tiles = [];
const labels = []; // {x, y, text, visible}
const tileSize = META.tile_size;
const imgW = META.width;
const imgH = META.height;
const maxZ = META.max_zoom;

let scale = 1;
let offsetX = 0;
let offsetY = 0;
let brightness = 1; // brillo inicial

// ------------------
// Cargar todos los tiles
// ------------------
async function loadTiles() {
  const promises = [];
  const tilesX = Math.ceil(imgW / tileSize);
  const tilesY = Math.ceil(imgH / tileSize);

  for (let ty = 0; ty < tilesY; ty++) {
    for (let tx = 0; tx < tilesX; tx++) {
      const img = new Image();
      img.src = `/tiles/${maxZ}/${tx}/${ty}.png`;
      tiles.push({img, x: tx * tileSize, y: ty * tileSize});
      promises.push(new Promise(res => img.onload = res));
    }
  }

  await Promise.all(promises);
  draw();
}

// ------------------
// Dibujar canvas
// ------------------
function draw() {
  canvas.width = viewer.clientWidth;
  canvas.height = viewer.clientHeight;

  ctx.save();
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.translate(-offsetX * scale, -offsetY * scale);
  ctx.scale(scale, scale);

  // Aplicar brillo
  ctx.filter = `brightness(${brightness})`;

  // Dibujar mosaico
  for (const t of tiles) ctx.drawImage(t.img, t.x, t.y);

  // Dibujar labels
  ctx.filter = 'none'; // los labels no se ven afectados por brillo
  ctx.font = `${16/scale}px sans-serif`;
  ctx.fillStyle = 'red';
  ctx.textBaseline = 'top';
  for (const l of labels) {
    if (!l.visible) continue;
    ctx.fillText(l.text, l.x, l.y);
  }

  ctx.restore();
}

// ------------------
// Panning
// ------------------
let isDown = false, startX = 0, startY = 0;
viewer.addEventListener('mousedown', e => { 
  isDown = true; startX = e.clientX; startY = e.clientY; 
});
window.addEventListener('mouseup', () => isDown = false);
window.addEventListener('mousemove', e => {
  if (!isDown) return;
  const dx = (e.clientX - startX) / scale;
  const dy = (e.clientY - startY) / scale;
  offsetX -= dx; offsetY -= dy;
  startX = e.clientX; startY = e.clientY;
  draw();
});

// ------------------
// Zoom
// ------------------
viewer.addEventListener('wheel', e => {
  e.preventDefault();
  const factor = e.deltaY < 0 ? 1.2 : 1/1.2;
  scale *= factor;
  draw();
});

// ------------------
// Añadir label interactivo
// ------------------
viewer.addEventListener('dblclick', e => {
  const rect = viewer.getBoundingClientRect();
  const x = (offsetX + (e.clientX - rect.left)/scale);
  const y = (offsetY + (e.clientY - rect.top)/scale);
  const text = prompt('Label text:');
  if (!text) return;
  labels.push({x, y, text, visible: true});
  draw();
});

// ------------------
// Atajos teclado para ocultar/mostrar labels
// ------------------
window.addEventListener('keydown', e => {
  if (e.key === 'r' || e.key === 'R') {
    labels.forEach(l => l.visible = false);
    draw();
  }
  if (e.key === 'y' || e.key === 'p' || e.key === 'Y' || e.key === 'P') {
    labels.forEach(l => l.visible = true);
    draw();
  }
});

// ------------------
// Slider de brillo
// ------------------
const slider = document.getElementById('brightness');
if (slider) {
  slider.addEventListener('input', () => {
    brightness = parseFloat(slider.value);
    draw();
  });
}

// ------------------
// Inicializar
// ------------------
function init() {
  offsetX = Math.max(0, (imgW - viewer.clientWidth)/2);
  offsetY = Math.max(0, (imgH - viewer.clientHeight)/2);
  loadTiles();
}

window.addEventListener('load', init);
