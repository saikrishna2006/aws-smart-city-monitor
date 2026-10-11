from flask import Flask, render_template, Response, jsonify
from detector import generate_frames, global_state

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/status')
def status():
    return jsonify(global_state)

if __name__ == "__main__":
    app.run(debug=True, port=5000)