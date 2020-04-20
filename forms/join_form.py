from wtforms import StringField
from wtforms.validators import DataRequired, Email
from .login_form import LoginForm


class JoinForm(LoginForm):
    email = StringField(validators=[Email(message='Not a valid email address.'), DataRequired()])

    @property
    def e_mail(self):
        return self.email.data
