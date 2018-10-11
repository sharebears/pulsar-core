from flask_sqlalchemy.model import DefaultMeta


class CoreModel(DefaultMeta):

    def assign_attr(self, name, value):
        setattr(self, name, value)
