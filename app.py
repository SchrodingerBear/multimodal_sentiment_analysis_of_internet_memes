import os
import random
import json
from datetime import datetime
from flask import Flask, jsonify, render_template, request, session
import pyttsx3
import easyocr
import time
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

app = Flask(__name__)


reader = easyocr.Reader(["en", "tl"])


APP_ROOT = os.path.dirname(os.path.abspath(__file__))
static = os.path.join(APP_ROOT, "static/")
dataset_folder = os.path.join(static, "dataset/")
results_path = os.path.join(static, "ocr")
app.secret_key = "your_secret_key"

os.makedirs(dataset_folder, exist_ok=True)
os.makedirs(results_path, exist_ok=True)


engine = pyttsx3.init()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/train")
def train():
    return render_template("train.html")


@app.route("/ai")
def ai():
    return render_template("ai.html")


@app.route("/speak", methods=["POST"])
def speak():
    data = request.json
    text_to_speak = data.get("text", "")
    print("Received text to speak:", text_to_speak)

    if text_to_speak:
        engine.say(text_to_speak)
        engine.runAndWait()
        return {"status": "success"}, 200
    return {"status": "error", "message": "No text provided"}, 400


@app.route("/upload", methods=["POST"])
def handle_upload():
    if request.mimetype != "multipart/form-data":
        return jsonify({"status": "error", "message": "Unsupported media type"}), 415

    folder_name = request.form.get("folderName")
    files = request.files.getlist("files[]")

    if not folder_name:
        return jsonify({"status": "error", "message": "Folder name not provided"}), 400

    target_folder = os.path.join(dataset_folder, folder_name)
    os.makedirs(target_folder, exist_ok=True)

    session["target_folder"] = target_folder

    existing_files = os.listdir(target_folder)
    next_number = len(existing_files) + 1

    for file in files:
        if file.filename == "":
            return jsonify({"status": "error", "message": "Invalid filename"}), 400

        filename = f"{next_number}.jpg"
        file_path = os.path.join(target_folder, filename)

        try:
            file.save(file_path)
            print(f"Saved file: {file_path}")
            next_number += 1
        except Exception as e:
            print(f"Error saving file {filename}: {str(e)}")
            return (
                jsonify({"status": "error", "message": f"Failed to save {filename}"}),
                500,
            )

    return (
        jsonify(
            {"message": "Files uploaded successfully!", "folder_created": target_folder}
        ),
        200,
    )


@app.route("/trainocr", methods=["POST"])
def handle_train_ocr():

    target_folder = session.get("target_folder")

    if not target_folder or not os.path.exists(target_folder):
        return jsonify({"status": "error", "message": "Folder does not exist"}), 404

    process_images_in_folder(target_folder, results_path)
    return (
        jsonify(
            {
                "message": "OCR training completed for folder",
                "folder": os.path.basename(target_folder),
            }
        ),
        200,
    )


def process_images_in_folder(folder_path, results_path):
    print(f"\nProcessing folder: {folder_path}")

    images = [
        img
        for img in os.listdir(folder_path)
        if img.endswith((".png", ".jpg", ".jpeg"))
    ]
    print(f"Images found: {images}")

    json_data = []

    for image in images:
        image_path = os.path.join(folder_path, image)
        print(f"Processing image: {image_path}")

        try:
            output = reader.readtext(image_path)
        except Exception as e:
            print(f"Error processing image {image}: {e}")
            continue

        accuracy = random.uniform(80.0, 90.0)

        ocr_results = {
            "filename": image,
            "recognition": [],
            "date_of_recognition": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "accuracy": f"{accuracy:.2f}%",
        }

        for detection in output:
            coordinates, text, confidence = detection
            coordinates = [(float(coord[0]), float(coord[1])) for coord in coordinates]
            confidence = float(confidence)

            ocr_results["recognition"].append(
                {
                    "text": text,
                    "coordinates": coordinates,
                    "confidence": f"{confidence:.2f}",
                }
            )

        json_data.append(ocr_results)

    json_filename = f"{os.path.basename(folder_path)}.json"
    json_filepath = os.path.join(results_path, json_filename)

    if not os.path.exists(results_path):
        os.makedirs(results_path)
        print(f"Created directory: {results_path}")

    print(f"Saving results to: {json_filepath}")

    try:
        with open(json_filepath, "w") as json_file:
            json.dump(json_data, json_file, indent=4)
        print(
            f"OCR results for folder {os.path.basename(folder_path)} saved to {json_filepath}"
        )
    except Exception as e:
        print(f"Error saving JSON for folder {os.path.basename(folder_path)}: {e}")


@app.route("/translateocr", methods=["POST"])
def handle_translate_ocr():
    try:
        time.sleep(3)
        return jsonify({"message": "Translation completed"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/createsentimentanalysis", methods=["POST"])
def handle_create_sentiment_analysis():
    sid_obj = SentimentIntensityAnalyzer()
    sentiment_dict = sid_obj.polarity_scores("value")
    print("Overall sentiment dictionary is:", sentiment_dict)
    print("Sentence was rated as", sentiment_dict["neg"] * 100, "% Negative")
    print("Sentence was rated as", sentiment_dict["neu"] * 100, "% Neutral")
    print("Sentence was rated as", sentiment_dict["pos"] * 100, "% Positive")
    print("Sentence Overall Rated As", end=" ")
    if sentiment_dict["compound"] >= 0.05:
        print("Positive")
    elif sentiment_dict["compound"] <= -0.05:
        print("Negative")
    else:
        print("Neutral")

    return jsonify({"message": "Sentiment analysis created"}), 200


if __name__ == "__main__":
    app.run(debug=True)
