import os
import io
 
import cv2
import numpy as np
import onnxruntime as ort
 
from PIL import Image
 
# ════════════════════════════════════════════════
# CONFIGURACIÓN DEL MODELO
# ════════════════════════════════════════════════
 
BASE_DIR = os.path.dirname(__file__)
 
MODEL_PATH = os.path.join(
    BASE_DIR,
    "model",
    "retinascan_model.onnx"
)
 
LABELS = [
    "Sin retinopatía",
    "Leve",
    "Moderada",
    "Severa",
    "Proliferativa"
]
 
# ✅ CORREGIDO: debe coincidir con el entrenamiento (380x380, no 224x224)
IMG_SIZE = 380
 
_session = None
 
 
# ════════════════════════════════════════════════
# CARGAR SESIÓN ONNX
# ════════════════════════════════════════════════
 
def get_session():
 
    global _session
 
    if _session is None:
 
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                f"No se encontró el modelo ONNX:\n{MODEL_PATH}"
            )
 
        try:
 
            _session = ort.InferenceSession(
                MODEL_PATH,
                providers=["CPUExecutionProvider"]
            )
 
            print("✅ Modelo ONNX cargado correctamente")
 
        except Exception as e:
 
            raise RuntimeError(
                f"❌ Error cargando ONNX:\n{str(e)}"
            )
 
    return _session
 
 
# ════════════════════════════════════════════════
# PREPROCESAMIENTO
# ════════════════════════════════════════════════
 
def preprocess(img: Image.Image) -> np.ndarray:
 
    img = img.convert("RGB")
 
    # ✅ CORREGIDO: 380x380 igual que en el entrenamiento
    img = img.resize((IMG_SIZE, IMG_SIZE))
 
    arr = np.array(img).astype(np.float32) / 255.0
 
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std  = np.array([0.229, 0.224, 0.225], dtype=np.float32)
 
    arr = (arr - mean) / std
    arr = arr.transpose(2, 0, 1)
    arr = np.expand_dims(arr, axis=0)
 
    return arr.astype(np.float32)
 
 
# ════════════════════════════════════════════════
# SOFTMAX ESTABLE
# ════════════════════════════════════════════════
 
def softmax(x):
 
    e_x = np.exp(x - np.max(x))
 
    return e_x / e_x.sum()
 
 
# ════════════════════════════════════════════════
# GENERAR HEATMAP
# ════════════════════════════════════════════════
 
def generate_heatmap(img, probs, idx):
 
    img_resized = img.resize((IMG_SIZE, IMG_SIZE))
    original    = np.array(img_resized)
 
    heat = np.zeros((IMG_SIZE, IMG_SIZE), dtype=np.float32)
    h, w = heat.shape
 
    center_x = w // 2
    center_y = h // 2
 
    for y in range(h):
        for x in range(w):
            dist = np.sqrt(
                (x - center_x) ** 2 +
                (y - center_y) ** 2
            )
            heat[y, x] = np.exp(-dist / 80)
 
    heat    = (heat * 255).astype(np.uint8)
    heatmap = cv2.applyColorMap(heat, cv2.COLORMAP_JET)
 
    overlay = cv2.addWeighted(original, 0.6, heatmap, 0.4, 0)
    overlay = cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB)
 
    return Image.fromarray(overlay)
 
 
# ════════════════════════════════════════════════
# PREDICCIÓN PRINCIPAL
# ════════════════════════════════════════════════
 
def predict(image_input):
 
    # ── Abrir imagen
    if isinstance(image_input, str):
        img = Image.open(image_input).convert("RGB")
    else:
        img = Image.open(io.BytesIO(image_input)).convert("RGB")
 
    # ── Preprocesar
    arr = preprocess(img)
 
    # ── Obtener sesión
    sess = get_session()
 
    input_name = sess.get_inputs()[0].name
 
    # ── Inferencia
    logits = sess.run(None, {input_name: arr})[0][0]
 
    probs      = softmax(logits)
    idx        = int(np.argmax(probs))
    confidence = float(probs[idx]) * 100
 
    # ── Heatmap
    heatmap_img      = generate_heatmap(img, probs, idx)
    heatmap_filename = "heatmap_last.jpg"
    heatmap_path     = os.path.join(
        "app", "static", "uploads", heatmap_filename
    )
 
    os.makedirs(os.path.dirname(heatmap_path), exist_ok=True)
    heatmap_img.save(heatmap_path)
 
    # ── Entropía
    entropy = float(-np.sum(probs * np.log(probs + 1e-9)))
 
    return {
        "prediction":       LABELS[idx],
        "label":            LABELS[idx],
        "confidence":       round(confidence, 2),
        "severity":         ["none", "mild", "moderate", "severe", "proliferative"][idx],
        "probs":            [round(float(p) * 100, 2) for p in probs],
        "entropy":          round(entropy, 4),
        "heatmap_filename": heatmap_filename,
    }