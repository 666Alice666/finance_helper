from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
@app.route("/registration")
def registr():
    return render_template('registr.html')

@app.route("/main")
def main():
    return render_template('main.html')

@app.route("/history")
def history():
    return render_template('history.html')

@app.route("/statistics")
def statistics():
    return render_template('statistics.html')

@app.route("/debts")
def debts():
    return render_template('debts.html')

if __name__ == '__main__':
    app.run(debug=True)
