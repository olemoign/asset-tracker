import datetime

import inflection
import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.ext.declarative


AsciiString = sqlalchemy.String
backref = sqlalchemy.orm.backref
Boolean = sqlalchemy.Boolean
Bytes = sqlalchemy.String
DateTime = sqlalchemy.DateTime
Enum = sqlalchemy.Enum
Field = sqlalchemy.Column
ForeignKey = sqlalchemy.ForeignKey
func = sqlalchemy.func
Integer = sqlalchemy.Integer
or_ = sqlalchemy.or_
relationship = sqlalchemy.orm.relationship
String = sqlalchemy.Unicode
Table = sqlalchemy.Table

__author__ = 'Jean-Christophe Bohin <jc.bohin@phiropsi.com>'


class _ModelBase(object):
    id = Field(Integer, primary_key=True)


class _DeclarativeMeta(sqlalchemy.ext.declarative.DeclarativeMeta):
    def __new__(mcs, name, bases, d):
        tablename = d.get('__tablename__')
        if not tablename and d.get('__table__') is None:
            d['__tablename__'] = inflection.underscore(name)

        return sqlalchemy.ext.declarative.DeclarativeMeta.__new__(mcs, name, bases, d)


Model = sqlalchemy.ext.declarative.declarative_base(cls=_ModelBase, name='ObjectModel', metaclass=_DeclarativeMeta)


class CreationDateTimeMixin(object):
    created_at = Field(DateTime(timezone=True), default=datetime.datetime.utcnow(), nullable=False)


class UpdateDateTimeMixin(object):
    updated_at = Field(DateTime(timezone=True), default=datetime.datetime.utcnow(), onupdate=datetime.datetime.utcnow(), nullable=False)





