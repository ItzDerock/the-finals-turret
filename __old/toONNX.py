from ultralytics import YOLO

model = YOLO('best.pt')
model.export(format = 'onnx') # exports the model in '.onnx' format
