from sqlalchemy import create_engine, sql
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String


_Base = declarative_base()

# FIXME: NOT THREAD SAFE!!
session = None


class Guild(_Base):

    __tablename__ = "guilds"

    snowflake = Column(Integer, primary_key=True)
    log_channel_snowflake = Column(Integer)

    entry_banner_enabled = Column(Boolean, nullable=False, default=False)
    entry_regexes = relationship("EntryRegex", back_populates="guild")

    def __repr__(self):
       return "<Guild(snowflake={0}, log_channel_snowflake={1}, entry_banner_enabled={2})>".format(
           self.snowflake, self.log_channel_snowflake, self.entry_banner_enabled
       )


class EntryRegex(_Base):

    __tablename__ = "entryRegexes"

    id = Column(Integer, primary_key=True)
    regex = Column(String, nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    lowercase = Column(Boolean, nullable=False)

    guild_snowflake = Column(Integer, ForeignKey('guilds.snowflake'), nullable=False)
    guild = relationship("Guild",  cascade="all, delete", back_populates="entry_regexes")

    # 'metadata' attribute is used by sqlalchemy.
    meta = relationship("EntryRegexMeta", uselist=False, back_populates="regex")
    bans = relationship("EntryBan")

    def __repr__(self):
       return "<EntryRegex(regex='{0}', enabled={1}, lowercase={2}, guild_snowflake={4})>".format(
           self.regex, self.enabled, self.lowercase, self.guild_snowflake,
       )


class EntryRegexMeta(_Base):

    __tablename__ = "entryRegexMeta"

    id = Column(Integer, primary_key=True)

    regex_id = Column(Integer, ForeignKey('entryRegexes.id'), nullable=False)
    regex = relationship("EntryRegex", back_populates="meta")

    created_date = Column(DateTime(timezone=True), server_default=sql.func.now(), nullable=False)
    created_name = Column(String, nullable=False)
    created_snowflake = Column(Integer, nullable=False)

    def __repr__(self):
       return "<EntryRegexMeta(regex_id={0}, created_date={1}, created_name='{2}', created_snowflake={3})>".format(
           self.regex_id, self.created_date, self.created_name, self.created_snowflake
       )


class EntryBan(_Base):

    __tablename__ = "entryBans"

    id = Column(Integer, primary_key=True)

    regex_id = Column(Integer, ForeignKey('entryRegexes.id'), nullable=False)
    regex = relationship("EntryRegex", back_populates="bans")

    date = Column(DateTime(timezone=True), server_default=sql.func.now(), nullable=False)
    user_name = Column(String, nullable=False)
    user_snowflake = Column(Integer, nullable=False)

    def __repr__(self):
       return "<EntryBan(regex_id={0}, date={1}, user_name='{2}', user_snowflake={3})>".format(
           self.regex_id, self.date, self.user_name, self.user_snowflake
       )


def init_database(dbpath):
    """Setup database engine and connection.

    Args:
        dbpath (string): path to the database file.
    """
    engine = create_engine("sqlite:///{0}".format(dbpath), echo=True)
    _Base.metadata.create_all(engine)

    global session
    session = sessionmaker(bind=engine)()
