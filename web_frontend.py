from flask import Flask, render_template
import database

app = Flask(__name__)

@app.route("/")
def index():
    return render_template('index.html')

@app.route('/tracks/<button>')
def trackselect(button):
    track_name = database.get_track_name(button)
    artist_name = database.get_artist_name(button)
    return render_template('tracks.html', track_name=track_name, artist_name=artist_name)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)