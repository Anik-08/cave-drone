
import sys
import numpy as np
from PIL import Image
import tensorflow as tf
from tensorflow import keras

MODEL_PATH = "dce_model.keras" 
IMAGE_SIZE = 256 


def enhance_image(image_path, model, size=IMAGE_SIZE):
    original = Image.open(image_path).convert("RGB")
    resized = original.resize((size, size))

    arr = np.array(resized).astype("float32") / 255.0
    arr = np.expand_dims(arr, axis=0)

    dce_output = model(arr, training=False)
    x = arr
    for i in range(0, 3 * 8, 3):
        r = dce_output[:, :, :, i:i + 3]
        x = x + r * (tf.square(x) - x)

    enhanced = tf.clip_by_value(x[0], 0.0, 1.0)
    enhanced = tf.cast(enhanced * 255, tf.uint8).numpy()

    return original, Image.fromarray(enhanced)


def main():
    if len(sys.argv) != 3:
        sys.exit(1)

    input_path, output_path = sys.argv[1], sys.argv[2]

    print(f"Loading model from {MODEL_PATH} ...")
    model = keras.models.load_model(MODEL_PATH)

    print(f"Enhancing {input_path} ...")
    original, enhanced = enhance_image(input_path, model)

    # Uncomment to resize output back to the original photo's resolution
    # instead of the model's working size (256x256):
    # enhanced = enhanced.resize(original.size)

    enhanced.save(output_path)
    print(f"Saved enhanced image to {output_path}")


if __name__ == "__main__":
    main()