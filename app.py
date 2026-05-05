from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
@app.route("/registration")
def registr():
    return render_template('registr.html')

@app.route("/main")
def main():
    return render_template('main.html')

if __name__ == '__main__':
    app.run(debug=True)
