import os, torch, timm, onnx, onnxruntime as ort, numpy as np

PTH_PATH  = "best_model.pth"
ONNX_PATH = "app/ai/model/retinascan_model.onnx"
IMG_SIZE  = 380
NUM_CLASES = 5

print("🔧 Cargando arquitectura EfficientNet-B4 ...")
model = timm.create_model("efficientnet_b4", pretrained=False, num_classes=NUM_CLASES)
print(f"📦 Cargando pesos desde: {PTH_PATH}")
state = torch.load(PTH_PATH, map_location="cpu")
model.load_state_dict(state)
model.eval()
print("✅ Pesos cargados correctamente")

os.makedirs(os.path.dirname(ONNX_PATH), exist_ok=True)
dummy = torch.randn(1, 3, IMG_SIZE, IMG_SIZE)
print(f"🚀 Exportando a ONNX → {ONNX_PATH}")
torch.onnx.export(model, dummy, ONNX_PATH, input_names=["input"], output_names=["output"], dynamic_axes={"input": {0: "batch"}, "output": {0: "batch"}}, opset_version=17)
print("✅ Exportación completada")

model_onnx = onnx.load(ONNX_PATH)
onnx.checker.check_model(model_onnx)
sess = ort.InferenceSession(ONNX_PATH, providers=["CPUExecutionProvider"])
print(f"📥 Input : {sess.get_inputs()[0].shape}")
print(f"📤 Output: {sess.get_outputs()[0].shape}")
print("🎉 ¡Listo!")
