import typing

from marshmallow import fields


class BigNumber(fields.Field):
    def _serialize(self, value: typing.Any, attr: str, obj: typing.Any, **kwargs):
        if value is None:
            return None

        return '{:d}'.format(int(value))
