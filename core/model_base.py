from flask_sqlalchemy.model import DefaultMeta


class CoreModel(DefaultMeta):

    def assign_attrs(self, **kwargs):
        for key, val in kwargs.items():
            setattr(self, key, val)
