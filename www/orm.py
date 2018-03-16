#!/user/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'kevin Sun'

import asyncio,logging
import aiomysql

def log(sql,arg=()):
	logging.info('SQL: %s' % sql)

async def create_pool(loop,**kw):
	logging.info('create database connection pool...')
	global __pool
	__pool = await aiomysql.create_pool(
		host=kw.get('host','localhost'),
		port=kw.get('port',3306),
		user=kw['user'],
		password=kw['password'],
		db=kw['db'],
		charset=kw.get('charset','utf8'),
		autocommit=kw.get('autocommit',True),
		maxsize=kw.get('maxsize',10),
		minsize=kw.get('minsize',1),
		loop=loop
		)

@asyncio.coroutine
def destory_pool():
    global __pool
    if __pool is not None :
        __pool.close()  #关闭进程池,The method is not a coroutine,就是说close()不是一个协程，所有不用yield from
        yield from __pool.wait_closed()

async def select(sql,args,size=None):
	log(sql)
#	global __pool
	async with __pool.get() as conn:
		async with conn.cursor(aiomysql.DictCursor) as cur:
			await cur.execute(sql.replace('?','%s'),args or ())
			if size:
				rs = await cur.fetchmany(size)
			else:
				rs = await cur.fetchall()
		logging.info('rows returned: %s' % len(rs))
		return rs  #返回查询结果，元素是tuple的list

async def execute(sql,args,autocommit=True):
	log(sql)
	async with __pool.acquire() as conn:
		if not autocommit:
			await conn.begin()
		try:
			async with conn.cursor(aiomysql.DictCursor) as cur:
				print(sql.replace('?','%s'))
				await cur.execute(sql.replace('?','%s'),args)
				affected = cur.rowcount
				if not autocommit:
					await conn.commit()
		except BaseException as e:
			if not autocommit:
				await conn.rollback()
			raise
		return affected

class Field(object):
	def __init__(self,name,column_type,primary_key,default):
		self.name = name
		self.column_type = column_type
		self.primary_key = primary_key
		self.default = default
	def __str__(self):
		return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self.name)

class StringField(Field):
	def __init__(self,name=None,primary_key=False,default=None,ddl='varchar(100)'):
		super().__init__(name,ddl,primary_key,default)

class BooleanField(Field):
	def __init__(self,name=None,default=False):
		super().__init__(name,'boolean',False,default)

class IntegerField(Field):
	def __init__(self, name=None,primary_key=False,default=0):
		super().__init__(name, 'bigint', primary_key, default)

class FloatField(Field):
    def __init__(self, name=None, primary_key=False, default=0.0):
        super().__init__(name, 'real', primary_key, default)

class TextField(Field):
    def __init__(self, name=None, default=None):
        super().__init__(name, 'text', False, default)

#创建拥有几个占位符的字符串,把查询字段计数 替换成sql识别的?
# 比如说：insert into  `User` (`password`, `email`, `name`, `id`) values (?,?,?,?)
def create_args_string(num):
    L = []
    for n in range(num):
        L.append('?')
    return ', '.join(L)

# 所有的元类都继承自type
# ModelMetaclass元类定义了所有Model基类(继承ModelMetaclass)的子类实现的操作
# -*-ModelMetaclass的工作主要是为一个数据库表映射成一个封装的类做准备：
# ***读取具体子类(user)的映射信息
# 创造类的时候，排除对Model类的修改
# 在当前类中查找所有的类属性(attrs)，如果找到Field属性，就将其保存到__mappings__的dict中，同时从类属性中删除Field(防止实例属性遮住类的同名属性)
# 将数据库表名保存到__table__中

# 完成这些工作就可以在Model中定义各种数据库的操作方法
# metaclass是类的模板，所以必须从`type`类型派生：
class ModelMetaClass(type):
	# __new__方法接受的参数依次是：
	# 1.当前准备创建的类的对象（cls）
	# 2.类的名字（name）
	# 3.类继承的父类集合(bases)
	# 4.类的方法集合(attrs)
	def __new__(cls,name,bases,attrs):
		#排除Model类本身
		if name == 'Model':
			return type.__new__(cls,name,bases,attrs)
		#获取table名称
		tableName = attrs.get('__table__',None) or name
		mappings = dict()
		fields = []
		primaryKey = None
		#id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
		for k,v in attrs.items(): # k->id v->StringField(primary_key=True, default=next_id, ddl='varchar(50)')
			if isinstance(v,Field):
				logging.info('  found mapping: %s ==> %s' % (k, v))
				mappings[k] = v
				if v.primary_key:#有主键  主键为True
					if primaryKey: #不为None，则主键重复，报错
						raise RuntimeError('Duplicate primary key for field: %s' % k)
					primaryKey = k
				else:
					# 保存非主键的列名
					fields.append(k)
		if not primaryKey:
			raise RuntimeError('Primary key not found.')
		#从类属性中删除Field属性
		for k in mappings.keys():
			attrs.pop(k)
		# 保存除主键外的属性为''列表形式
		# 将除主键外的其他属性变成`id`, `name`这种形式，关于
		escaped_fields = list(map(lambda f: '`%s`' % f, fields))
		attrs['__mappings__'] = mappings  # 保存属性和列的映射关系
		attrs['__table__'] = tableName
		attrs['__primary_key__'] = primaryKey  # 主键属性名
		attrs['__fields__'] = fields  # 除主键外的属性名
		attrs['__select__'] = 'select `%s` , %s from `%s` ' % (primaryKey,','.join(escaped_fields),tableName)
		attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (tableName, ', '.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields) + 1))
		attrs['__update__'] = 'update `%s` set %s where `%s`=?' % (tableName, ', '.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)
		attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (tableName, primaryKey)
		return type.__new__(cls, name, bases, attrs)


# Model类的任意子类可以映射一个数据库表
# Model类可以看作是对所有数据库表操作的基本定义的映射

# 基于字典查询形式
# Model从dict继承，拥有字典的所有功能，同时实现特殊方法__getattr__和__setattr__，能够实现属性操作
# 实现数据库操作的所有方法，定义为class方法，所有继承自Model都具有数据库操作方法
class Model(dict,metaclass=ModelMetaClass):
	def __init__(self,**kw):
		super(Model, self).__init__(**kw)

	def __getattr__(self, key):
		try:
			return self[key]
		except KeyError:
			raise AttributeError(r"'Model' object has no attribute '%s'" % key)

	def __setattr__(self, key, value):
		self[key] = value

	def getValue(self, key):
		return getattr(self, key, None)

	# 使用默认值
	def getValueOrDefault(self, key):
		value = getattr(self, key, None)
		if value is None:
			field = self.__mappings__[key]
			if field.default is not None:
				value = field.default() if callable(field.default) else field.default
				logging.debug('using default value for %s: %s' % (key, str(value)))
				setattr(self, key, value)
		return value


	# 类方法有类变量cls传入，从而可以用cls做一些相关的处理。并且有子类继承时，调用该类方法时，传入的类变量cls是子类，而非父类。
	@classmethod
	async def findAll(cls, where=None, args=None, **kw):
		' find objects by where clause. '
		sql = [cls.__select__]
		if where:
			sql.append('where')
			sql.append(where)
		if args is None:
			args = []
		orderBy = kw.get('orderBy', None)
		if orderBy:
			sql.append('order by')
			sql.append(orderBy)
		limit = kw.get('limit', None)
		if limit is not None:
			sql.append('limit')
			if isinstance(limit, int): #limit 20
				sql.append('?')
				args.append(limit)
			elif isinstance(limit, tuple) and len(limit) == 2:  #limit(10,20)
				sql.append('?, ?')
				args.extend(limit)
			else:
				raise ValueError('Invalid limit value: %s' % str(limit))
		rs = await select(' '.join(sql), args)
		return [cls(**r) for r in rs]# **r 是关键字参数，构成了一个cls类的列表，其实就是每一条记录对应的类实例

	#获取数据库中某一列的数目
	@classmethod
	async def findNumber(cls, selectField, where=None, args=None):
		' find number by select and where. '
		sql = ['select count(%s) _num_ from `%s`' % (selectField, cls.__table__)] #_num_ 是列的别名
		if where:
			sql.append('where')
			sql.append(where)
		rs = await select(' '.join(sql), args, 1)
		if len(rs) == 0:
			return None
		return rs[0]['_num_']  #rs-> list[tuple(),(),(),()]


	@classmethod
	async def find(cls, pk):
		' find object by primary key. '
		rs = await select('%s where `%s`=?' % (cls.__select__, cls.__primary_key__), [pk], 1)
		if len(rs) == 0:
			return None
		return cls(**rs[0])


	async def save(self):
		args = list(map(self.getValueOrDefault, self.__fields__))
		args.append(self.getValueOrDefault(self.__primary_key__))
		rows = await execute(self.__insert__, args)
		if rows != 1:
			logging.warn('failed to insert record: affected rows: %s' % rows)


	async def update(self):
		args = list(map(self.getValue, self.__fields__))
		args.append(self.getValue(self.__primary_key__)) #获得的value是User实例的属性值，也就是传入的name，email，password值
		rows = await execute(self.__update__, args)
		if rows != 1:
			logging.warn('failed to update by primary key: affected rows: %s' % rows)


	async def remove(self):
		args = [self.getValue(self.__primary_key__)]
		rows = await execute(self.__delete__, args)
		if rows != 1:
			logging.warn('failed to remove by primary key: affected rows: %s' % rows)
