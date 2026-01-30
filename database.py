from peewee import *
import datetime
import json
import os

db = SqliteDatabase(os.path.join(os.path.dirname(__file__), 'bot.db'))

class BaseModel(Model):
    class Meta:
        database = db

class Owner(BaseModel):
    username = CharField(unique=True)
    added_at = DateTimeField(default=datetime.datetime.now)

class Channel(BaseModel):
    channel_id = CharField(unique=True) # The chat_id (e.g. -100123...)
    title = CharField()
    username = CharField(null=True) # @channelname, optional/changeable
    invite_link = CharField(null=True)  # Stored invite link
    added_at = DateTimeField(default=datetime.datetime.now)

class ScheduledPost(BaseModel):
    schedule_time = CharField() # HH:MM string
    message_data = TextField() # JSON string: {type, content, caption, ...}
    created_at = DateTimeField(default=datetime.datetime.now)

class User(BaseModel):
    user_id = IntegerField(unique=True)
    username = CharField(null=True)
    points = IntegerField(default=0)
    referrer_id = IntegerField(null=True)
    joined_all = BooleanField(default=False)
    created_at = DateTimeField(default=datetime.datetime.now)

class BotSetting(BaseModel):
    key = CharField(unique=True)
    value = TextField()
    updated_at = DateTimeField(default=datetime.datetime.now)

def init_db():
    db.connect()
    db.create_tables([Owner, Channel, ScheduledPost, User, BotSetting])
    # Migration hack for invite_link
    try:
        db.execute_sql('ALTER TABLE channel ADD COLUMN invite_link VARCHAR')
    except:
        pass

def add_owner_safe(username):
    username = username.replace('@', '').lower()
    try:
        Owner.create(username=username)
        return True
    except IntegrityError:
        return False

def is_owner(username):
    if not username: return False
    return Owner.select().where(Owner.username == username.replace('@', '').lower()).exists()

def get_owners():
    return [o.username for o in Owner.select()]

def remove_owner(username):
    username = username.replace('@', '').lower()
    return Owner.delete().where(Owner.username == username).execute()

def add_channel_safe(channel_id, title, username, invite_link=None):
    try:
        Channel.create(channel_id=str(channel_id), title=title, username=username, invite_link=invite_link)
        return True
    except IntegrityError:
        return False

def get_channels():
    return Channel.select()

def remove_channel(channel_id):
    return Channel.delete().where(Channel.channel_id == str(channel_id)).execute()

def remove_channel(channel_id):
    return Channel.delete().where(Channel.channel_id == str(channel_id)).execute()

def update_channel_id(old_id, new_id, new_title=None):
    try:
        q = Channel.update(channel_id=str(new_id), title=new_title if new_title else Channel.title).where(Channel.channel_id == str(old_id))
        return q.execute()
    except:
        return False

def add_schedule(time_str, msg_data):
    # time_str: "HH:MM"
    # msg_data: dict
    return ScheduledPost.create(
        schedule_time=time_str,
        message_data=json.dumps(msg_data)
    )

def get_all_schedules():
    return ScheduledPost.select()

def delete_schedule(schedule_id):
    return ScheduledPost.delete().where(ScheduledPost.id == schedule_id).execute()

# User helpers
def get_user(user_id):
    return User.get_or_none(User.user_id == user_id)

def add_user(user_id, username, referrer_id=None):
    try:
        return User.create(user_id=user_id, username=username, referrer_id=referrer_id)
    except IntegrityError:
        return get_user(user_id)

def add_points(user_id, amount):
    user = get_user(user_id)
    if user:
        user.points += amount
        user.save()
        return True
    return False

def get_referral_count(user_id):
    return User.select().where(User.referrer_id == user_id).count()

def get_setting(key, default=None):
    try:
        s = BotSetting.get(BotSetting.key == key)
        return s.value
    except DoesNotExist:
        return default

def set_setting(key, value):
    try:
        obj, created = BotSetting.get_or_create(key=key, defaults={'value': value})
        if not created:
            obj.value = value
            obj.save()
        return True
    except:
        return False

if __name__ == '__main__':
    init_db()
    print("Database initialized.")
