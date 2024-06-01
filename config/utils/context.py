
from django.db.models.fields.related import RelatedField

from framarama.base import utils

class ResultValue:

    def __init__(self, value):
        self._value = value
        if type(value) == dict:
            self._resolver = MapResolver(self._value)
        elif type(value) == object:
            self._resolver = ObjectResolver(self._value)
        else:
            self._resolver = None

    def keys(self):
        if type(self._value) == dict:
            return self._value.keys()
        return []

    def __len__(self):
        return len(self._value) if self._value != None else 0

    def __iter__(self):
        def value_iterator_list(value, l):
            i = 0
            while i < l:
                yield ResultValue(value[i])
                i = i + 1
        def value_iterator_dict(value, l):
            for k, v in value.items():
                yield k, ResultValue(v)
        if type(self._value) == list:
            return value_iterator_list(self._value, len(self._value))
        if type(self._value) == dict:
            return value_iterator_dict(self._value)
        return None

    def __getitem__(self, key):
        if self._value == None:
            return ResultValue(None)
        if self._resolver:
            return ResultValue(self._resolver[key])
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
            return False
        return str(self._value).lower() in ['true', '1', 't', 'y', 'yes']


class Context:

    def __init__(self):
        self._resolvers = {}

    def set_resolver(self, name, resolver):
        self._resolvers[name] = resolver

    def evaluate(self, expr):
        if type(expr) is dict:
            return ResultValue({_k: self.evaluate(_v) for _k, _v in expr.items()})
        elif type(expr) is list:
            return ResultValue([self.evaluate(_v) for _v in expr])
        elif expr is not None:
            return ResultValue(utils.Template.render(str(expr), self._resolvers))
        else:
            return None

    def evaluate_model(self, model):
        _result = ResultValue(None)
        for field in model.get_fields():
            try:
                _value = getattr(model, field.name)
                _evaluated = self.evaluate(_value) if _value is not None else None
                setattr(_result, field.name, _evaluated)
            except Exception as e:
                raise Exception('Evaluation of \"{}\" in {}.{} failed: {}'.format(_value, type(model).__name__, field.name, e)) from e
        return _result


class ContextResolver:

    def __call__(self, *args, **kwargs):
        return ResultValue(None)

    def __getitem__(self, key):
        return ResultValue(self._resolve(key))

    def __getattr__(self, key):
        return ResultValue(self._resolve(key))

    def __len__(self):
        return 0

    def _resolve(self, name):
        raise NotImplemented("Missing implementation for {}".format(type(self)))


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


class EvaluatedResolver(ContextResolver):

    def __init__(self, ctx, resolver):
        self._ctx = ctx
        self._resolver = resolver

    def _resolve(self, name):
        _value = self._resolver._resolve(name)
        return self._ctx.evaluate(_value)
