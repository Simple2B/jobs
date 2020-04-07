from flask import Flask, render_template, session
from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired

app = Flask(__name__)
app.secret_key = "adlfkhLSDHFlkshfsdbfnBSMDNFBSkjweKDFJhsldkjhf"

class LoginForm(FlaskForm):
    username = StringField('username', validators=[DataRequired()])
    password = StringField('password', validators=[DataRequired()])

    @property
    def name(self):
        return self.username.data

    @property
    def passwd(self):
        return self.password.data

@app.route("/")
def home():
    if 'role' not in session:
        session['role'] = 'guest'
    return render_template("landing.html", form=LoginForm(), role=session['role'])

@app.route("/login", methods=['POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        if form.name=="ton" and form.passwd == "123":
            return "hello, ton"
        else:
            return "no such user"

@app.route("/signup", methods=['POST'])
def signup():
    pass