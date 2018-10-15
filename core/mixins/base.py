class BaseFunctionalityMixin:

    @classmethod
    def assign_attrs(cls, **kwargs):
        for key, val in kwargs.items():
            setattr(cls, key, val)
