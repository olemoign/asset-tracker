# -*- coding: utf-8 -*-
from datetime import datetime

from inflection import underscore
import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.ext.declarative
import sqlalchemy.ext.hybrid


and_ = sqlalchemy.and_
asc = sqlalchemy.asc
backref = sqlalchemy.orm.backref
Boolean = sqlalchemy.Boolean
Bytes = sqlalchemy.String
Date = sqlalchemy.Date
DateTime = sqlalchemy.DateTime
desc = sqlalchemy.desc
Enum = sqlalchemy.Enum
Field = sqlalchemy.Column
Float = sqlalchemy.Float
ForeignKey = sqlalchemy.ForeignKey
ForeignKeyConstraint = sqlalchemy.ForeignKeyConstraint
func = sqlalchemy.func
hybrid_property = sqlalchemy.ext.hybrid.hybrid_property
Integer = sqlalchemy.Integer
join = sqlalchemy.join
or_ = sqlalchemy.or_
relationship = sqlalchemy.orm.relationship
select = sqlalchemy.select
String = sqlalchemy.Unicode
Table = sqlalchemy.Table
Text = sqlalchemy.Text
Time = sqlalchemy.Time

__author__ = 'Jean-Christophe Bohin <jc.bohin@phiropsi.com>'


class _ModelBase(object):
    id = Field(Integer, primary_key=True)


class _DeclarativeMeta(sqlalchemy.ext.declarative.DeclarativeMeta):
    def __new__(mcs, name, bases, d):
        tablename = d.get('__tablename__')
        if not tablename and d.get('__table__') is None:
            d['__tablename__'] = underscore(name)

        return sqlalchemy.ext.declarative.DeclarativeMeta.__new__(mcs, name, bases, d)


Model = sqlalchemy.ext.declarative.declarative_base(cls=_ModelBase, name='ObjectModel', metaclass=_DeclarativeMeta)


class CreationDateTimeMixin(object):
    created_at = Field(DateTime, default=datetime.utcnow, nullable=False)


class UpdateDateTimeMixin(object):
    updated_at = Field(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)





