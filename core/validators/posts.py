import flask
from voluptuous import Length, LengthInvalid


class PostLength(Length):
    def __call__(self, v):
        if self.min is not None and len(v) < self.min:
            raise LengthInvalid(
                self.msg or f'length of value must be at least {self.min}')
        if (self.max is not None
                and len(v) > self.max
                and (flask.g.user is None
                     or not flask.g.user.has_permission('site_no_post_length_limit'))):
            raise LengthInvalid(
                self.msg or f'length of value can be at most {self.max}')
        return v
