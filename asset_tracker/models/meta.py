# -*- coding: utf-8 -*-
from datetime import datetime

import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.ext.hybrid
from inflection import underscore
from sqlalchemy.ext.declarative import declarative_base, DeclarativeMeta
from sqlalchemy.schema import MetaData


and_ = sqlalchemy.and_
asc = sqlalchemy.asc
backref = sqlalchemy.orm.backref
Boolean = sqlalchemy.Boolean
Date = sqlalchemy.Date
DateTime = sqlalchemy.DateTime
declared_attr = sqlalchemy.ext.declarative.declared_attr
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


class _DeclarativeMeta(DeclarativeMeta):
    def __new__(mcs, name, bases, d):
        tablename = d.get('__tablename__')
        if not tablename and d.get('__table__') is None:
            d['__tablename__'] = underscore(name)

        return DeclarativeMeta.__new__(mcs, name, bases, d)


# Recommended naming convention used by Alembic, as various different database
# providers will autogenerate vastly different names making migrations more
# difficult. See: http://alembic.readthedocs.org/en/latest/naming.html
NAMING_CONVENTION = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)

Model = declarative_base(cls=_ModelBase, name='ObjectModel', metaclass=_DeclarativeMeta, metadata=metadata)


class CreationDateTimeMixin(object):
    created_at = Field(DateTime, default=datetime.utcnow, nullable=False)


class UpdateDateTimeMixin(object):
    updated_at = Field(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
