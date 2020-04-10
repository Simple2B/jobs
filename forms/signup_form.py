from wtforms import StringField
from wtforms.validators import DataRequired
from .login_form import LoginForm


class SignupForm(LoginForm):
    email = StringField('email', validators=[DataRequired()])

    @property
    def e_mail(self):
        return self.email.data
