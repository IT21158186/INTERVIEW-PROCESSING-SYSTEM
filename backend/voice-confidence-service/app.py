
# venv\Scripts\activate

from flask import Flask, request, jsonify
import joblib
import librosa
import numpy as np
import os

app = Flask(__name__)

# Load the trained model
model = joblib.load(r'/app/models/confidence_model.pkl')


def preprocess_audio(file_path):
    audio, sr = librosa.load(file_path, sr=None)
    mfccs = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=13)
    mfccs_mean = np.mean(mfccs.T, axis=0)
    pitches, magnitudes = librosa.core.piptrack(y=audio, sr=sr)
    pitch_mean = np.mean(pitches[pitches > 0]) if np.any(pitches) else 0
    spectral_centroid = np.mean(librosa.feature.spectral_centroid(y=audio, sr=sr))
    spectral_bandwidth = np.mean(librosa.feature.spectral_bandwidth(y=audio, sr=sr))
    chroma = np.mean(librosa.feature.chroma_stft(y=audio, sr=sr))
    features = np.hstack([mfccs_mean, pitch_mean, spectral_centroid, spectral_bandwidth, chroma])
    expected_feature_count = 19
    while len(features) < expected_feature_count:
        features = np.append(features, 0)
    return features

@app.route('/predict', methods=['POST'])
def predict():
    # Check if there's an audio file or text message in the request
    if 'audio' in request.files:
        audio_file = request.files['audio']
        audio_file.save('temp_audio.wav')  # Save the audio temporarily
        features = preprocess_audio('temp_audio.wav')
        features_reshaped = features.reshape(1, -1)

        predicted_class = model.predict(features_reshaped)
        predicted_label = predicted_class[0]  # Assuming binary classification
        predicted_proba = model.predict_proba(features_reshaped) 
        predicted_confidence = np.max(predicted_proba)

        # Clean up the temporary audio file
        os.remove('temp_audio.wav')

        return jsonify({
            'confidence_level': int(predicted_label),
            'confidence_score': float(predicted_confidence)  # Send the confidence score
        })


    elif 'text' in request.json:
        text_message = request.json['text']
        print(f"Received text message: {text_message}")  # Log the received text message

        # Return a success response
        return jsonify({'message': 'Text received successfully', 'received_text': text_message}), 200

    else: 
        return jsonify({'error': 'No audio file or text provided'}), 400

if __name__ == '__main__':
   app.run(host='0.0.0.0', port=3000)
