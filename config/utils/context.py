
from django.db.models.fields.related import RelatedField


class Result:
    pass


class ResultValue:

    def __init__(self, value):
        self._value = value

    def as_str(self):
        if self._value is None:
            return None
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


class NoneContextValue:

    def __str__(self):
        return ''

    def __repr__(self):
        return ''

    def __eq__(self, other):
        if other is None:
            return True
        if other == '':
            return True
        return False

    def __add__(self, other):
        return other

    def __radd__(self, other):
        return other


class Context:
    NONE_VALUE = NoneContextValue()

    def __init__(self):
        self._resolver = ChainedResolver()

    def set_resolver(self, name, resolver):
        self._resolver.set_resolver(name, resolver)

    def evaluate(self, expr):
        if expr is None:
            return None
        _globals = {}
        _globals.update(self._resolver.get_resolvers())
        _expr = 'f"' + str(expr) + '"'
        return eval(_expr, _globals, {})

    def evaluate_model(self, model):
        _result = Result()
        for field in model.get_fields():
            _value = getattr(model, field.name)
            _evaluated = ResultValue(self.evaluate(_value))
            setattr(_result, field.name, _evaluated)
        return _result


class ContextResolver:

    def __getitem__(self, key):
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
        return self._map[name] if name in self._map else Context.NONE_VALUE


class EnvironmentResolver(ContextResolver):

    def __init__(self):
        import os
        self._env = os.environ

    def _resolve(self, name):
        return self._env[name] if name in self._env else Context.NONE_VALUE


class ObjectResolver(ContextResolver):

    def __init__(self, instance):
        self._instance = instance

    def _resolve(self, name):
        if hasattr(self._instance, name):
            return getattr(self._instance, name)
        return Context.NONE_VALUE

