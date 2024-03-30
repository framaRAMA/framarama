
from django.db.models.fields.related import RelatedField

from jinja2.sandbox import SandboxedEnvironment

class Result:
    pass


class ResultValue:

    def __init__(self, value):
        self._value = value
        if type(value) == dict:
            self._resolver = MapResolver(self._value)
        elif type(value) == object:
            self._resolver = ObjectResolver(self._value)
        else:
            self._resolver = None

    def __call__(self, *args, **kwargs):
        return ResultValue(None)

    def __len__(self):
        return len(self._value) if self._value != None else 0

    def __iter__(self):
        def value_iterator(value, l):
            i = 0
            while i < l:
                yield self[i]
                i = i + 1
        return value_iterator(self, len(self))

    def __getitem__(self, key):
        if self._value == None:
            return ResultValue(None)
        if self._resolver:
            return self._resolver[key]
        try:
            return ResultValue(self._value[key])
        except:
            return ResultValue(None)

    def __getattr__(self, key):
        return self.__getitem__(key)

    def __repr__(self):
        return '<ResultValue: ' + str(self._value) + '>'

    def __str__(self):
        return '' if self._value is None else str(self._value)

    def __eq__(self, other):
        _this_value = self._value
        _other_value = other._value if isinstance(other, ResultValue) else other
        if _other_value is None and _this_value is None:
            return True
        if _other_value == _this_value:
            return True
        return False

    def __add__(self, other):
        return other if self._value is None else self._value + other

    def __radd__(self, other):
        return other if self._value is None else other + self._value

    def __sub__(self, other):
        return other if self._value is None else self._value - other

    def __rsub__(self, other):
        return other if self._value is None else other - self._value

    def __mul__(self, other):
        return other if self._value is None else self.as_float() * other

    def __rmul__(self, other):
        return other if self._value is None else other * self.as_float()

    def __truediv__(self, other):
        return other if self._value is None else self.as_float() / other

    def __rtruediv__(self, other):
        return other if self._value is None else other / self.as_float()

    def __floordiv__(self, other):
        return other if self._value is None else self.as_float() // other

    def __rfloordiv__(self, other):
        return other if self._value is None else other // self.as_float()

    def __mod__(self, other):
        return other if self._value is None else self.as_float() % other

    def __rmod__(self, other):
        return other if self._value is None else other % self.as_float()

    def __pow__(self, other, modulo=None):
        return other if self._value is None else pow(self.as_float(), other, mod=modulo)

    def __rpow__(self, other, modulo=None):
        return other if self._value is None else pow(other, self.as_float(), mod=modulo)

    def __instancecheck__(self, instance):
        return isinstance(instance, type(self)) or isinstance(instance, type(self._value))

    def __int__(self):
        return self.as_int()

    def __float__(self):
        return self.as_float()

    def __bool__(self):
        return self.as_bool();

    def as_str(self):
        if self._value is None:
            return None
        if type(self._value) == bool:
            return str(self._value).lower()
        return str(self._value)        

    def as_int(self):
        if self._value is None:
            return None
        return int(float(self._value))

    def as_float(self):
        if self._value is None:
            return None
        return float(self._value)

    def as_bool(self):
        if self._value is None:
            return None
        return str(self._value).lower() in ['true', '1', 't', 'y', 'yes']


class Context:

    def __init__(self):
        self._resolver = ChainedResolver()

    def set_resolver(self, name, resolver):
        self._resolver.set_resolver(name, resolver)

    def evaluate(self, expr):
        if expr is None:
            return None
        _env = SandboxedEnvironment()
        _env.globals.update(self._resolvers)
        _env.keep_trailing_newline = True
        _env.filters['split'] = lambda v, sep=None, maxsplit=-1: v.split(sep, maxsplit)
        _env.filters['keys'] = lambda v: v.keys() if type(v) == dict else []
        return _env.from_string(expr).render()

    def evaluate_model(self, model):
        _result = Result()
        for field in model.get_fields():
            try:
                _value = getattr(model, field.name)
                _evaluated = self.evaluate(str(_value)) if _value is not None else None
                setattr(_result, field.name, ResultValue(_evaluated))
            except Exception as e:
                raise Exception('Evaluation of \"{}\" in {}.{} failed: {}'.format(_value, type(model).__name__, field.name, e)) from e
        return _result


class ContextResolver:

    def __call__(self, *args, **kwargs):
        return None

    def __getitem__(self, key):
        return self._resolve(key)

    def __getattr__(self, key):
        return self._resolve(key)

    def _resolve(self, name):
        raise NotImplemented("Missing implementation for {}".format(type(self)))


class ChainedResolver(ContextResolver):

    def __init__(self):
        self._resolvers = {}

    def set_resolver(self, name, resolver):
        self._resolvers[name] = resolver

    def get_resolvers(self):
        return self._resolvers

    def _resolve(self, name):
        for _name, _resolver in self._resolvers.items():
            _value = _resolver.resolve(name)
            if _value is not None:
                return _value
        return ''


class MapResolver(ContextResolver):

    def __init__(self, variables):
        self._map = variables

    def _resolve(self, name):
        return self._map[name] if name in self._map else None


class EnvironmentResolver(ContextResolver):

    def __init__(self):
        import os
        self._env = os.environ

    def _resolve(self, name):
        return self._env[name] if name in self._env else None


class ObjectResolver(ContextResolver):

    def __init__(self, instance):
        self._instance = instance

    def _resolve(self, name):
        if hasattr(self._instance, name):
            return getattr(self._instance, name)
        return None

